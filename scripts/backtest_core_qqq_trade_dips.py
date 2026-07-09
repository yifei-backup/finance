#!/usr/bin/env python3
"""Backtest a core QQQ plus prioritized dip-trading strategy."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtest_strategy2 import (
    MAG7,
    buy_and_hold,
    compute_metrics,
    download_prices,
    parse_csv_list,
    parse_float_list,
)
from run_post_2022_tsm_amd_experiment import equal_weight_buy_and_hold
from sweep_strategy2_params import format_pct


DEFAULT_TICKERS = (*MAG7, "TSM", "AMD")
DEFAULT_PRIORITY = ("GOOGL", "NVDA", "AAPL", "TSM")
DEFAULT_BENCHMARKS = ("QQQ", "DIA")


def ordered_universe(tickers: tuple[str, ...], priority: tuple[str, ...]) -> tuple[str, ...]:
    priority_set = set(priority)
    return tuple(ticker for ticker in priority if ticker in tickers) + tuple(
        ticker for ticker in tickers if ticker not in priority_set
    )


def portfolio_value(cash: float, base_shares: float, shares: dict[str, float], row: pd.Series, base_asset: str) -> float:
    return cash + base_shares * row[base_asset] + sum(shares[ticker] * row[ticker] for ticker in shares)


def stock_value(shares: dict[str, float], row: pd.Series) -> float:
    return sum(shares[ticker] * row[ticker] for ticker in shares)


def backtest_core_trade_strategy(
    prices: pd.DataFrame,
    tickers: tuple[str, ...],
    priority: tuple[str, ...],
    base_asset: str,
    buy_levels: tuple[float, ...],
    buy_weights: tuple[float, ...],
    sell_gains: tuple[float, ...],
    core_fraction: float,
    trading_fraction: float,
    min_trade_fraction: float,
    initial_capital: float,
    prior_high_warmup: pd.DataFrame | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    if len(buy_levels) != len(buy_weights):
        raise ValueError("Buy levels and buy weights must have the same length.")
    if sorted(buy_levels) != list(buy_levels):
        raise ValueError("Buy levels must be sorted from shallow to deep.")
    if core_fraction + trading_fraction > 1.000001:
        raise ValueError("Core fraction plus trading fraction cannot exceed 100%.")

    execution_order = ordered_universe(tickers, priority)
    cash = 0.0
    base_shares = initial_capital / prices[base_asset].iloc[0]
    shares = {ticker: 0.0 for ticker in tickers}
    triggered_levels = {ticker: set() for ticker in tickers}
    realized_sell_stages = {ticker: set() for ticker in tickers}
    invested_cash = {ticker: 0.0 for ticker in tickers}
    trades: list[dict[str, object]] = []

    if prior_high_warmup is not None and not prior_high_warmup.empty:
        running_highs = prior_high_warmup[list(tickers)].cummax().iloc[-1].to_dict()
    else:
        running_highs = prices[list(tickers)].iloc[0].to_dict()

    equity_points: list[tuple[pd.Timestamp, float]] = []
    for date, row in prices.iterrows():
        value_before = portfolio_value(cash, base_shares, shares, row, base_asset)

        # Sell first so rebounds refill QQQ before new dip signals are evaluated.
        for ticker in execution_order:
            if shares[ticker] <= 0:
                continue

            position_value = shares[ticker] * row[ticker]
            unrealized_gain = position_value / invested_cash[ticker] - 1.0 if invested_cash[ticker] > 0 else 0.0
            prior_high = running_highs[ticker]
            near_prior_high = prior_high > 0 and row[ticker] >= 0.90 * prior_high

            sell_fraction = 0.0
            action = ""
            for gain in sell_gains:
                if unrealized_gain >= gain and gain not in realized_sell_stages[ticker]:
                    sell_fraction += 1.0 / len(sell_gains)
                    realized_sell_stages[ticker].add(gain)
                    action = f"sell_gain_{int(gain * 100)}pct"

            if near_prior_high:
                sell_fraction = 1.0
                action = "sell_near_prior_high"

            sell_fraction = min(sell_fraction, 1.0)
            if sell_fraction <= 0:
                continue

            sold_shares = shares[ticker] * sell_fraction
            proceeds = sold_shares * row[ticker]
            shares[ticker] -= sold_shares
            base_shares += proceeds / row[base_asset]
            invested_cash[ticker] *= 1.0 - sell_fraction
            trades.append(
                {
                    "date": date.date().isoformat(),
                    "ticker": ticker,
                    "action": action,
                    "price": row[ticker],
                    "shares": sold_shares,
                    "cash_flow": proceeds,
                    "unrealized_gain_before_trade": unrealized_gain,
                    "portfolio_value_before_trade": value_before,
                }
            )
            if shares[ticker] <= 1e-10:
                shares[ticker] = 0.0
                triggered_levels[ticker].clear()
                realized_sell_stages[ticker].clear()
                invested_cash[ticker] = 0.0

        value_before = portfolio_value(cash, base_shares, shares, row, base_asset)
        current_stock_value = stock_value(shares, row)
        max_stock_value = trading_fraction * value_before
        min_base_value = core_fraction * value_before
        available_trade_budget = max_stock_value - current_stock_value
        available_base_value = base_shares * row[base_asset] - min_base_value

        for ticker in execution_order:
            prior_high = running_highs[ticker]
            if prior_high <= 0:
                continue
            drawdown = row[ticker] / prior_high - 1.0
            for level, buy_weight in zip(buy_levels, buy_weights):
                if drawdown > -level or level in triggered_levels[ticker]:
                    continue
                trade_value = min(
                    buy_weight * value_before,
                    available_trade_budget,
                    available_base_value,
                )
                if trade_value < min_trade_fraction * value_before:
                    continue

                base_shares -= trade_value / row[base_asset]
                bought_shares = trade_value / row[ticker]
                shares[ticker] += bought_shares
                invested_cash[ticker] += trade_value
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
                        "portfolio_value_before_trade": value_before,
                    }
                )
                available_trade_budget -= trade_value
                available_base_value -= trade_value
                if available_trade_budget <= 1e-10 or available_base_value <= 1e-10:
                    break

        equity_points.append((date, portfolio_value(cash, base_shares, shares, row, base_asset)))
        for ticker in tickers:
            running_highs[ticker] = max(running_highs[ticker], row[ticker])

    equity = pd.Series(
        [value for _, value in equity_points],
        index=pd.DatetimeIndex([date for date, _ in equity_points]),
        name="core_qqq_trade_dips",
    )
    return equity, pd.DataFrame(trades)


def metrics_frame(rows: list[tuple[str, pd.Series]], risk_free_rate: float) -> pd.DataFrame:
    output = []
    for name, equity in rows:
        metrics = compute_metrics(equity, risk_free_rate)
        output.append(
            {
                "name": name,
                "final_value": metrics.final_value,
                "total_return": metrics.total_return,
                "cagr": metrics.cagr,
                "annualized_volatility": metrics.annualized_volatility,
                "sharpe": metrics.sharpe,
                "max_drawdown": metrics.max_drawdown,
            }
        )
    return pd.DataFrame(output)


def display_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["final_value"] = output["final_value"].map(lambda value: f"{value:.4f}")
    for column in ["total_return", "cagr", "annualized_volatility", "max_drawdown"]:
        output[column] = output[column].map(format_pct)
    output["sharpe"] = output["sharpe"].map(lambda value: f"{value:.2f}")
    return output


def write_summary(
    path: Path,
    prices: pd.DataFrame,
    args: argparse.Namespace,
    metrics: pd.DataFrame,
    trades: pd.DataFrame,
) -> None:
    lines = [
        "# Core QQQ plus prioritized dip-trading backtest",
        "",
        "This is not investment advice. It is a simple historical simulation using adjusted close data.",
        "",
        "## Setup",
        "",
        f"- Universe: {', '.join(args.tickers)}",
        f"- Priority order: {', '.join(args.priority)}",
        f"- Start/end: {prices.index[0].date()} to {prices.index[-1].date()}",
        f"- Core asset: {args.base_asset}",
        f"- Core QQQ floor: {format_pct(args.core_fraction)}",
        f"- Trading sleeve cap: {format_pct(args.trading_fraction)}",
        f"- Minimum trade size: {format_pct(args.min_trade_fraction)} of current portfolio value",
        f"- Buy drawdowns: {', '.join(format_pct(item) for item in args.buy_levels)} from prior all-time high",
        f"- Buy weights: {', '.join(format_pct(item) for item in args.buy_weights)} of current portfolio value",
        f"- Sell gains: {', '.join(format_pct(item) for item in args.sell_gains)} of remaining cost basis, or sell all near 90% of prior high",
        "",
        "## Metrics",
        "",
        display_metrics(metrics).to_markdown(index=False),
        "",
        "## Trade count",
        "",
        f"- Total trades: {len(trades)}",
        f"- Buys: {(trades['action'].str.startswith('buy')).sum() if not trades.empty else 0}",
        f"- Sells: {(trades['action'].str.startswith('sell')).sum() if not trades.empty else 0}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--priority", default=",".join(DEFAULT_PRIORITY))
    parser.add_argument("--benchmarks", default=",".join(DEFAULT_BENCHMARKS))
    parser.add_argument("--base-asset", default="QQQ")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-04-01")
    parser.add_argument("--warmup-start", default="2014-01-01", help="Used only to know prior all-time highs.")
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--core-fraction", type=float, default=0.70)
    parser.add_argument("--trading-fraction", type=float, default=0.30)
    parser.add_argument("--min-trade-fraction", type=float, default=0.01)
    parser.add_argument("--buy-levels", default="0.25,0.35,0.45")
    parser.add_argument("--buy-weights", default="0.10,0.10,0.10")
    parser.add_argument("--sell-gains", default="0.20,0.30")
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--cache-dir", default="data")
    parser.add_argument("--output-dir", default="results/core_qqq_trade_dips_post_2022")
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    args.tickers = parse_csv_list(args.tickers)
    args.priority = parse_csv_list(args.priority)
    args.benchmarks = parse_csv_list(args.benchmarks)
    args.base_asset = args.base_asset.upper()
    args.buy_levels = parse_float_list(args.buy_levels)
    args.buy_weights = parse_float_list(args.buy_weights)
    args.sell_gains = parse_float_list(args.sell_gains)

    all_tickers = tuple(dict.fromkeys((*args.tickers, *args.benchmarks, args.base_asset)))
    cache_name = "_".join(all_tickers) + f"_{args.warmup_start}_{args.end or 'latest'}.csv"
    full_prices = download_prices(
        all_tickers,
        start=args.warmup_start,
        end=args.end,
        cache_path=Path(args.cache_dir) / cache_name,
        refresh=args.refresh_data,
    )
    prices = full_prices.loc[full_prices.index >= pd.Timestamp(args.start)].copy()
    warmup = full_prices.loc[full_prices.index < pd.Timestamp(args.start)].copy()
    if prices.empty:
        raise RuntimeError("No prices are available in the requested backtest period.")

    strategy_equity, trades = backtest_core_trade_strategy(
        prices=prices,
        tickers=args.tickers,
        priority=args.priority,
        base_asset=args.base_asset,
        buy_levels=args.buy_levels,
        buy_weights=args.buy_weights,
        sell_gains=args.sell_gains,
        core_fraction=args.core_fraction,
        trading_fraction=args.trading_fraction,
        min_trade_fraction=args.min_trade_fraction,
        initial_capital=args.initial_capital,
        prior_high_warmup=warmup,
    )

    benchmark_curves = [
        (f"{benchmark}_buy_hold", buy_and_hold(prices[benchmark], args.initial_capital))
        for benchmark in args.benchmarks
    ]
    equal_weight_curve = equal_weight_buy_and_hold(prices, args.tickers, args.initial_capital)
    metric_rows = [
        ("core_qqq_trade_dips", strategy_equity),
        *benchmark_curves,
        ("equal_weight_stocks", equal_weight_curve),
    ]
    metrics = metrics_frame(metric_rows, args.risk_free_rate)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    trades.to_csv(output_dir / "trades.csv", index=False)
    pd.DataFrame(
        {
            "core_qqq_trade_dips": strategy_equity,
            **{name: curve for name, curve in benchmark_curves},
            "equal_weight_stocks": equal_weight_curve,
        }
    ).to_csv(output_dir / "equity_curves.csv")
    write_summary(output_dir / "summary.md", prices, args, metrics, trades)

    print(metrics.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print(f"\nWrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
