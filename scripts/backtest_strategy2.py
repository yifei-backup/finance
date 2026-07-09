#!/usr/bin/env python3
"""Backtest a Mag7 drawdown-buying strategy.

Strategy 2 interpretation:
- Universe defaults to the current "Magnificent Seven".
- Buy a tranche when a stock falls below configured drawdown levels from its
  own prior adjusted-close all-time high.
- Sell the full position when the stock reaches a new adjusted-close all-time
  high.
- Idle capital can stay in cash or be parked in a base ETF such as QQQ.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf


MAG7 = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")
DEFAULT_LEVELS = (0.20, 0.30, 0.40, 0.50)
DEFAULT_TRANCHE_WEIGHTS = (0.05, 0.05, 0.05, 0.05)
TRADING_DAYS = 252


@dataclass(frozen=True)
class Metrics:
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    max_drawdown: float
    final_value: float


def parse_csv_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def ensure_same_length(levels: Iterable[float], tranche_weights: Iterable[float]) -> None:
    levels_len = len(tuple(levels))
    weights_len = len(tuple(tranche_weights))
    if levels_len != weights_len:
        raise ValueError(
            f"Drawdown levels ({levels_len}) and tranche weights ({weights_len}) must match."
        )


def download_prices(
    tickers: tuple[str, ...],
    start: str,
    end: str | None,
    cache_path: Path,
    refresh: bool,
) -> pd.DataFrame:
    if cache_path.exists() and not refresh:
        prices = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return prices.sort_index()

    data = yf.download(
        list(tickers),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if data.empty:
        raise RuntimeError("No price data returned from Yahoo Finance.")

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            raise RuntimeError("Downloaded data does not include adjusted close prices.")
        prices = data["Close"].copy()
    else:
        prices = data[["Close"]].copy()
        prices.columns = tickers

    prices = prices.dropna(how="all").ffill().dropna(how="any")
    missing = sorted(set(tickers) - set(prices.columns))
    if missing:
        raise RuntimeError(f"Missing close prices for: {', '.join(missing)}")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(cache_path)
    return prices.sort_index()


def compute_metrics(equity: pd.Series, risk_free_rate: float = 0.0) -> Metrics:
    equity = equity.dropna()
    returns = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0 if years > 0 else math.nan
    ann_vol = returns.std(ddof=0) * math.sqrt(TRADING_DAYS)
    excess_daily = returns - risk_free_rate / TRADING_DAYS
    sharpe = (
        excess_daily.mean() / excess_daily.std(ddof=0) * math.sqrt(TRADING_DAYS)
        if excess_daily.std(ddof=0) > 0
        else math.nan
    )
    drawdown = equity / equity.cummax() - 1.0
    return Metrics(
        total_return=total_return,
        cagr=cagr,
        annualized_volatility=ann_vol,
        sharpe=sharpe,
        max_drawdown=drawdown.min(),
        final_value=equity.iloc[-1],
    )


def metrics_to_frame(metrics: dict[str, Metrics]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: {
                "final_value": value.final_value,
                "total_return": value.total_return,
                "cagr": value.cagr,
                "annualized_volatility": value.annualized_volatility,
                "sharpe": value.sharpe,
                "max_drawdown": value.max_drawdown,
            }
            for name, value in metrics.items()
        }
    ).T


def backtest_dip_strategy(
    prices: pd.DataFrame,
    universe: tuple[str, ...],
    levels: tuple[float, ...],
    tranche_weights: tuple[float, ...],
    initial_capital: float,
    base_asset: str | None,
) -> tuple[pd.Series, pd.DataFrame]:
    cash = initial_capital
    shares = {ticker: 0.0 for ticker in universe}
    triggered_levels = {ticker: set() for ticker in universe}
    trades: list[dict[str, object]] = []

    base_shares = 0.0
    if base_asset:
        base_shares = cash / prices[base_asset].iloc[0]
        cash = 0.0

    equity_points: list[tuple[pd.Timestamp, float]] = []
    prior_highs = prices[universe].cummax().shift(1)

    for date, row in prices.iterrows():
        portfolio_value = cash + sum(shares[ticker] * row[ticker] for ticker in universe)
        if base_asset:
            portfolio_value += base_shares * row[base_asset]

        # Exit first so a new high can reset the next drawdown cycle cleanly.
        for ticker in universe:
            prior_high = prior_highs.at[date, ticker]
            if shares[ticker] <= 0 or pd.isna(prior_high) or row[ticker] < prior_high:
                continue
            proceeds = shares[ticker] * row[ticker]
            cash += proceeds
            trades.append(
                {
                    "date": date.date().isoformat(),
                    "ticker": ticker,
                    "action": "sell_new_high",
                    "price": row[ticker],
                    "shares": shares[ticker],
                    "cash_flow": proceeds,
                    "portfolio_value_before_trade": portfolio_value,
                }
            )
            shares[ticker] = 0.0
            triggered_levels[ticker].clear()

        if base_asset and cash > 0:
            base_shares += cash / row[base_asset]
            cash = 0.0

        portfolio_value = cash + sum(shares[ticker] * row[ticker] for ticker in universe)
        if base_asset:
            portfolio_value += base_shares * row[base_asset]

        for ticker in universe:
            prior_high = prior_highs.at[date, ticker]
            if pd.isna(prior_high) or prior_high <= 0:
                continue
            drawdown = row[ticker] / prior_high - 1.0

            for level, tranche_weight in zip(levels, tranche_weights):
                if drawdown > -level or level in triggered_levels[ticker]:
                    continue

                trade_value = tranche_weight * portfolio_value
                if base_asset:
                    sale_value = min(trade_value, base_shares * row[base_asset])
                    base_shares -= sale_value / row[base_asset]
                    cash += sale_value

                trade_value = min(trade_value, cash)
                if trade_value <= 0:
                    continue

                bought_shares = trade_value / row[ticker]
                shares[ticker] += bought_shares
                cash -= trade_value
                triggered_levels[ticker].add(level)
                trades.append(
                    {
                        "date": date.date().isoformat(),
                        "ticker": ticker,
                        "action": f"buy_down_{int(level * 100)}pct",
                        "price": row[ticker],
                        "shares": bought_shares,
                        "cash_flow": -trade_value,
                        "drawdown": drawdown,
                        "portfolio_value_before_trade": portfolio_value,
                    }
                )

        equity = cash + sum(shares[ticker] * row[ticker] for ticker in universe)
        if base_asset:
            equity += base_shares * row[base_asset]
        equity_points.append((date, equity))

    equity_curve = pd.Series(
        data=[value for _, value in equity_points],
        index=pd.DatetimeIndex([date for date, _ in equity_points]),
        name="strategy2_equity",
    )
    return equity_curve, pd.DataFrame(trades)


def buy_and_hold(prices: pd.Series, initial_capital: float) -> pd.Series:
    return prices / prices.iloc[0] * initial_capital


def write_markdown_summary(
    path: Path,
    args: argparse.Namespace,
    prices: pd.DataFrame,
    metrics: pd.DataFrame,
    trades: pd.DataFrame,
) -> None:
    pct_metrics = metrics.copy()
    for column in ["total_return", "cagr", "annualized_volatility", "max_drawdown"]:
        pct_metrics[column] = pct_metrics[column].map(lambda value: f"{value:.2%}")
    pct_metrics["final_value"] = pct_metrics["final_value"].map(lambda value: f"{value:.4f}")
    pct_metrics["sharpe"] = pct_metrics["sharpe"].map(lambda value: f"{value:.2f}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Strategy 2 backtest summary",
                "",
                "This is not investment advice. It is a simple historical simulation using adjusted close data.",
                "",
                "## Parameters",
                "",
                f"- Universe: {', '.join(args.tickers)}",
                f"- Start/end: {prices.index[0].date()} to {prices.index[-1].date()}",
                f"- Drawdown levels: {', '.join(f'{level:.0%}' for level in args.levels)}",
                f"- Tranche weights: {', '.join(f'{weight:.0%}' for weight in args.tranche_weights)} of current portfolio value",
                f"- Idle capital: {args.base_asset if args.base_asset else 'cash'}",
                f"- Initial capital: {args.initial_capital:g}",
                "",
                "## Metrics",
                "",
                pct_metrics.to_markdown(),
                "",
                "## Trade count",
                "",
                f"- Total trades: {len(trades)}",
                f"- Buys: {(trades['action'].str.startswith('buy')).sum() if not trades.empty else 0}",
                f"- Sells: {(trades['action'].str.startswith('sell')).sum() if not trades.empty else 0}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(MAG7), help="Comma-separated stock universe.")
    parser.add_argument("--benchmark", default="QQQ", help="Benchmark ETF ticker.")
    parser.add_argument("--base-asset", default=None, help="Optional asset for idle capital, e.g. QQQ.")
    parser.add_argument("--start", default="2014-01-01", help="Download start date.")
    parser.add_argument("--end", default=None, help="Download end date, exclusive.")
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--levels", default=",".join(str(level) for level in DEFAULT_LEVELS))
    parser.add_argument(
        "--tranche-weights",
        default=",".join(str(weight) for weight in DEFAULT_TRANCHE_WEIGHTS),
    )
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--cache-dir", default="data")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    args.tickers = parse_csv_list(args.tickers)
    args.levels = parse_float_list(args.levels)
    args.tranche_weights = parse_float_list(args.tranche_weights)
    args.benchmark = args.benchmark.upper()
    args.base_asset = args.base_asset.upper() if args.base_asset else None
    ensure_same_length(args.levels, args.tranche_weights)

    all_tickers = tuple(dict.fromkeys((*args.tickers, args.benchmark, *(tuple([args.base_asset]) if args.base_asset else ()))))
    cache_name = "_".join(all_tickers) + f"_{args.start}_{args.end or 'latest'}.csv"
    prices = download_prices(
        all_tickers,
        start=args.start,
        end=args.end,
        cache_path=Path(args.cache_dir) / cache_name,
        refresh=args.refresh_data,
    )

    strategy_equity, trades = backtest_dip_strategy(
        prices=prices,
        universe=args.tickers,
        levels=args.levels,
        tranche_weights=args.tranche_weights,
        initial_capital=args.initial_capital,
        base_asset=args.base_asset,
    )
    benchmark_equity = buy_and_hold(prices[args.benchmark], args.initial_capital)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"strategy2": strategy_equity, args.benchmark: benchmark_equity}).to_csv(
        output_dir / "strategy2_equity_curve.csv"
    )
    trades.to_csv(output_dir / "strategy2_trades.csv", index=False)

    metric_frame = metrics_to_frame(
        {
            "strategy2": compute_metrics(strategy_equity, args.risk_free_rate),
            f"{args.benchmark}_buy_hold": compute_metrics(benchmark_equity, args.risk_free_rate),
        }
    )
    metric_frame.to_csv(output_dir / "strategy2_metrics.csv")
    write_markdown_summary(output_dir / "strategy2_summary.md", args, prices, metric_frame, trades)

    print(metric_frame.to_string(float_format=lambda value: f"{value:.6f}"))
    print(f"\nWrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
