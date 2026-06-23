#!/usr/bin/env python3
"""Backtest QQQ and AI drawdown-buying strategies.

The script intentionally avoids third-party market-data packages so it can run
with /usr/bin/python3 in a minimal environment. It downloads daily Yahoo
Finance chart data and writes a Markdown summary to results/.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


QQQ = "QQQ"
TQQQ = "TQQQ"
QLD = "QLD"
SGOV = "SGOV"
MAG7 = ("AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA")
AI_CORE = ("NVDA", "TSM", "GOOGL", "MSFT", "AMZN", "META", "ASML", "AVGO")
ALL_TICKERS = tuple(dict.fromkeys((QQQ, TQQQ, QLD, SGOV, *MAG7, *AI_CORE)))
TRADING_DAYS = 252
EPSILON = 1e-10


@dataclass(frozen=True)
class PriceSeries:
    ticker: str
    close: Mapping[str, float]
    adj_close: Mapping[str, float]

    @property
    def dates(self) -> List[str]:
        return sorted(self.adj_close)


@dataclass(frozen=True)
class BacktestResult:
    name: str
    dates: Sequence[str]
    equity: Sequence[float]
    daily_returns: Sequence[float]
    average_tqqq_weight: float = 0.0
    max_tqqq_weight: float = 0.0
    average_stock_sleeve: float = 0.0
    max_stock_sleeve: float = 0.0
    average_qld_weight: float = 0.0
    max_qld_weight: float = 0.0
    average_ai_core_weight: float = 0.0
    max_ai_core_weight: float = 0.0
    average_cash_like_weight: float = 0.0
    max_cash_like_weight: float = 0.0


def yahoo_chart_url(ticker: str, period1: int, period2: int) -> str:
    quoted = urllib.parse.quote(ticker)
    query = urllib.parse.urlencode(
        {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{quoted}?{query}"


def fetch_price_series(ticker: str, period2: int) -> PriceSeries:
    request = urllib.request.Request(
        yahoo_chart_url(ticker, period1=0, period2=period2),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    error = payload.get("chart", {}).get("error")
    if error:
        raise RuntimeError(f"Yahoo returned an error for {ticker}: {error}")

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    adjclose = result["indicators"]["adjclose"][0]["adjclose"]
    closes = quote["close"]

    close_by_date: Dict[str, float] = {}
    adj_by_date: Dict[str, float] = {}
    for ts, close, adj in zip(timestamps, closes, adjclose):
        if close is None or adj is None:
            continue
        session_date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        close_by_date[session_date] = float(close)
        adj_by_date[session_date] = float(adj)

    if len(adj_by_date) < 2:
        raise RuntimeError(f"Not enough data for {ticker}")
    return PriceSeries(ticker=ticker, close=close_by_date, adj_close=adj_by_date)


def running_drawdown_and_ath(series: PriceSeries) -> Tuple[Dict[str, float], Dict[str, bool]]:
    drawdown: Dict[str, float] = {}
    is_ath: Dict[str, bool] = {}
    running_max = -math.inf
    for day in sorted(series.close):
        close = series.close[day]
        new_high = close >= running_max - EPSILON
        if new_high:
            running_max = close
        drawdown[day] = close / running_max - 1.0
        is_ath[day] = new_high
    return drawdown, is_ath


def common_trading_dates(series_by_ticker: Mapping[str, PriceSeries]) -> List[str]:
    date_sets = [set(series.adj_close) for series in series_by_ticker.values()]
    first_common_possible = max(min(date_set) for date_set in date_sets)
    dates = sorted(set.intersection(*date_sets))
    return [day for day in dates if day >= first_common_possible]


def lookback_start(end_day: str, years: int) -> str:
    end = date.fromisoformat(end_day)
    try:
        start = end.replace(year=end.year - years)
    except ValueError:
        # Handles Feb. 29 for leap years.
        start = end.replace(year=end.year - years, day=28)
    return start.isoformat()


def select_lookback_dates(dates: Sequence[str], years: int | None) -> List[str]:
    if years is None:
        return list(dates)
    start_day = lookback_start(dates[-1], years)
    selected = [day for day in dates if day >= start_day]
    if len(selected) < 2:
        raise RuntimeError(f"Not enough common trading dates for a {years}-year lookback")
    return selected


def returns_by_ticker(
    series_by_ticker: Mapping[str, PriceSeries], dates: Sequence[str]
) -> Dict[str, Dict[str, float]]:
    returns: Dict[str, Dict[str, float]] = {ticker: {} for ticker in series_by_ticker}
    for ticker, series in series_by_ticker.items():
        for previous_day, day in zip(dates, dates[1:]):
            previous_price = series.adj_close[previous_day]
            current_price = series.adj_close[day]
            returns[ticker][day] = current_price / previous_price - 1.0
    return returns


def update_tqqq_weight(current_weight: float, day: str, qqq_drawdown: Mapping[str, float], qqq_is_ath: Mapping[str, bool]) -> float:
    if qqq_is_ath[day]:
        return 0.0
    drawdown = qqq_drawdown[day]
    if drawdown <= -0.20:
        return max(current_weight, 0.60)
    if drawdown <= -0.10:
        return max(current_weight, 0.30)
    return current_weight


def simulate_qqq_tqqq_strategy(
    dates: Sequence[str],
    returns: Mapping[str, Mapping[str, float]],
    qqq_drawdown: Mapping[str, float],
    qqq_is_ath: Mapping[str, bool],
) -> BacktestResult:
    equity = [1.0]
    daily_returns: List[float] = []
    tqqq_weights: List[float] = []
    tqqq_weight = update_tqqq_weight(0.0, dates[0], qqq_drawdown, qqq_is_ath)

    for day in dates[1:]:
        tqqq_weights.append(tqqq_weight)
        qqq_weight = 1.0 - tqqq_weight
        daily_return = qqq_weight * returns[QQQ][day] + tqqq_weight * returns[TQQQ][day]
        daily_returns.append(daily_return)
        equity.append(equity[-1] * (1.0 + daily_return))
        tqqq_weight = update_tqqq_weight(tqqq_weight, day, qqq_drawdown, qqq_is_ath)

    return BacktestResult(
        name="Strategy 1: QQQ drawdown -> TQQQ",
        dates=dates,
        equity=equity,
        daily_returns=daily_returns,
        average_tqqq_weight=sum(tqqq_weights) / len(tqqq_weights),
        max_tqqq_weight=max(tqqq_weights),
    )


def stage_from_drawdown(drawdown: float) -> int:
    if drawdown <= -0.40:
        return 3
    if drawdown <= -0.30:
        return 2
    if drawdown <= -0.20:
        return 1
    return 0


def update_mag7_stages(
    current_stages: MutableMapping[str, int],
    day: str,
    stock_drawdowns: Mapping[str, Mapping[str, float]],
    stock_is_ath: Mapping[str, Mapping[str, bool]],
) -> None:
    for ticker in MAG7:
        if stock_is_ath[ticker][day]:
            current_stages[ticker] = 0
            continue
        current_stages[ticker] = max(current_stages[ticker], stage_from_drawdown(stock_drawdowns[ticker][day]))


def mag7_weights(stages: Mapping[str, int]) -> Tuple[float, Dict[str, float]]:
    max_stage = max(stages.values())
    sleeve_by_stage = {0: 0.0, 1: 0.30, 2: 0.45, 3: 0.60}
    sleeve = sleeve_by_stage[max_stage]
    total_score = sum(stages.values())
    if sleeve == 0.0 or total_score == 0:
        return 0.0, {ticker: 0.0 for ticker in MAG7}
    return sleeve, {ticker: sleeve * stage / total_score for ticker, stage in stages.items()}


def simulate_mag7_drawdown_strategy(
    dates: Sequence[str],
    returns: Mapping[str, Mapping[str, float]],
    drawdowns: Mapping[str, Mapping[str, float]],
    is_ath: Mapping[str, Mapping[str, bool]],
) -> BacktestResult:
    equity = [1.0]
    daily_returns: List[float] = []
    stock_sleeves: List[float] = []
    stages: Dict[str, int] = {ticker: 0 for ticker in MAG7}
    update_mag7_stages(stages, dates[0], drawdowns, is_ath)

    for day in dates[1:]:
        stock_sleeve, stock_weights = mag7_weights(stages)
        stock_sleeves.append(stock_sleeve)
        qqq_weight = 1.0 - stock_sleeve
        daily_return = qqq_weight * returns[QQQ][day]
        daily_return += sum(stock_weights[ticker] * returns[ticker][day] for ticker in MAG7)
        daily_returns.append(daily_return)
        equity.append(equity[-1] * (1.0 + daily_return))
        update_mag7_stages(stages, day, drawdowns, is_ath)

    return BacktestResult(
        name="Strategy 2: QQQ + Mag7 drawdown sleeve",
        dates=dates,
        equity=equity,
        daily_returns=daily_returns,
        average_stock_sleeve=sum(stock_sleeves) / len(stock_sleeves),
        max_stock_sleeve=max(stock_sleeves),
    )


def ai_core_multiplier(drawdown: float) -> float:
    if drawdown <= -0.50:
        return 3.0
    if drawdown <= -0.40:
        return 2.5
    if drawdown <= -0.30:
        return 2.0
    if drawdown <= -0.20:
        return 1.5
    return 1.0


def qld_weight_from_qqq_drawdown(drawdown: float) -> float:
    if drawdown <= -0.35:
        return 0.30
    if drawdown <= -0.25:
        return 0.20
    if drawdown <= -0.15:
        return 0.10
    return 0.0


def ai_core_weights(day: str, drawdowns: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    base_weight = 0.30 / len(AI_CORE)
    desired = {
        ticker: min(0.18, base_weight * ai_core_multiplier(drawdowns[ticker][day]))
        for ticker in AI_CORE
    }
    total = sum(desired.values())
    if total <= 0.60:
        return desired
    scale = 0.60 / total
    return {ticker: weight * scale for ticker, weight in desired.items()}


def ai_core_target_weights(day: str, drawdowns: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    ai_weights = ai_core_weights(day, drawdowns)
    ai_total = sum(ai_weights.values())
    qld_weight = qld_weight_from_qqq_drawdown(drawdowns[QQQ][day])
    ai_extra = max(0.0, ai_total - 0.30)

    # Cash is spent first on AI drawdown adds and the small QLD overlay.
    cash_like_weight = max(0.0, 0.20 - ai_extra - qld_weight)
    qqq_weight = 1.0 - ai_total - qld_weight - cash_like_weight
    if qqq_weight < -EPSILON:
        raise RuntimeError(f"AI strategy weights exceeded 100% on {day}")

    weights = {ticker: 0.0 for ticker in ALL_TICKERS}
    weights[QQQ] = max(0.0, qqq_weight)
    weights[QLD] = qld_weight
    weights[SGOV] = cash_like_weight
    weights.update(ai_weights)
    return weights


def simulate_ai_core_strategy(
    dates: Sequence[str],
    returns: Mapping[str, Mapping[str, float]],
    drawdowns: Mapping[str, Mapping[str, float]],
) -> BacktestResult:
    equity = [1.0]
    daily_returns: List[float] = []
    qld_weights: List[float] = []
    ai_core_totals: List[float] = []
    cash_like_weights: List[float] = []

    for previous_day, day in zip(dates, dates[1:]):
        weights = ai_core_target_weights(previous_day, drawdowns)
        qld_weights.append(weights[QLD])
        ai_core_total = sum(weights[ticker] for ticker in AI_CORE)
        ai_core_totals.append(ai_core_total)
        cash_like_weights.append(weights[SGOV])

        daily_return = sum(weight * returns[ticker][day] for ticker, weight in weights.items() if weight)
        daily_returns.append(daily_return)
        equity.append(equity[-1] * (1.0 + daily_return))

    return BacktestResult(
        name="Strategy 3: AI core + cash + QLD overlay",
        dates=dates,
        equity=equity,
        daily_returns=daily_returns,
        average_qld_weight=sum(qld_weights) / len(qld_weights),
        max_qld_weight=max(qld_weights),
        average_ai_core_weight=sum(ai_core_totals) / len(ai_core_totals),
        max_ai_core_weight=max(ai_core_totals),
        average_cash_like_weight=sum(cash_like_weights) / len(cash_like_weights),
        max_cash_like_weight=max(cash_like_weights),
    )


def simulate_qqq_buy_hold(
    dates: Sequence[str], returns: Mapping[str, Mapping[str, float]]
) -> BacktestResult:
    equity = [1.0]
    daily_returns = [returns[QQQ][day] for day in dates[1:]]
    for daily_return in daily_returns:
        equity.append(equity[-1] * (1.0 + daily_return))
    return BacktestResult(name="Benchmark: QQQ buy and hold", dates=dates, equity=equity, daily_returns=daily_returns)


def max_drawdown(equity: Sequence[float]) -> float:
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1.0)
    return max_dd


def annualized_metrics(result: BacktestResult) -> Dict[str, float]:
    daily_returns = result.daily_returns
    start = date.fromisoformat(result.dates[0])
    end = date.fromisoformat(result.dates[-1])
    years = (end - start).days / 365.25
    total_return = result.equity[-1] - 1.0
    cagr = result.equity[-1] ** (1.0 / years) - 1.0
    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((daily_return - mean) ** 2 for daily_return in daily_returns) / (len(daily_returns) - 1)
    daily_std = math.sqrt(variance)
    annual_vol = daily_std * math.sqrt(TRADING_DAYS)
    sharpe = mean / daily_std * math.sqrt(TRADING_DAYS) if daily_std > 0 else float("nan")
    return {
        "total_return": total_return,
        "cagr": cagr,
        "annual_vol": annual_vol,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown(result.equity),
        "final_value": result.equity[-1],
    }


def pct(value: float) -> str:
    return f"{value * 100:,.2f}%"


def number(value: float) -> str:
    return f"{value:,.2f}"


def markdown_table(rows: Iterable[Sequence[str]]) -> str:
    rows = list(rows)
    header = rows[0]
    separator = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(separator) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def write_summary(
    output_path: Path,
    results: Sequence[BacktestResult],
    metrics_by_name: Mapping[str, Mapping[str, float]],
    data_end: str,
    lookback_years: int | None,
) -> None:
    best = max(results, key=lambda result: metrics_by_name[result.name]["sharpe"])
    table_rows = [
        (
            "Portfolio",
            "Sharpe",
            "CAGR",
            "Ann. vol",
            "Max drawdown",
            "Total return",
            "$1 grows to",
            "Avg TQQQ wt",
            "Avg Mag7 sleeve",
            "Avg AI core",
            "Avg QLD wt",
            "Avg SGOV/cash",
        )
    ]
    for result in results:
        metrics = metrics_by_name[result.name]
        table_rows.append(
            (
                result.name,
                f"{metrics['sharpe']:.2f}",
                pct(metrics["cagr"]),
                pct(metrics["annual_vol"]),
                pct(metrics["max_drawdown"]),
                pct(metrics["total_return"]),
                number(metrics["final_value"]),
                pct(result.average_tqqq_weight),
                pct(result.average_stock_sleeve),
                pct(result.average_ai_core_weight),
                pct(result.average_qld_weight),
                pct(result.average_cash_like_weight),
            )
        )

    start_date = results[0].dates[0]
    end_date = results[0].dates[-1]
    window_label = "full common" if lookback_years is None else f"trailing {lookback_years}-year"
    lines = [
        "# QQQ/TQQQ vs QQQ+Mag7 vs AI-core drawdown strategy backtest",
        "",
        f"Data source: Yahoo Finance daily chart API, adjusted close for returns, close for drawdown/new-high triggers. Data fetched through {data_end}.",
        f"Common comparison window: {start_date} to {end_date} ({len(results[0].daily_returns)} daily returns, {window_label} window).",
        "",
        "## Strategy definitions",
        "",
        "- Benchmark: 100% QQQ buy-and-hold.",
        "- Strategy 1: start from 100% QQQ. If QQQ is below its prior closing high by 10%, raise TQQQ weight to 30%; if it is below by 20%, raise TQQQ weight to 60%. Keep the highest reached TQQQ tier until QQQ closes at a new high, then reset to 100% QQQ.",
        "- Strategy 2: start from 100% QQQ. For Mag7 stocks (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA), open/raise a stock sleeve when a name is below its own prior closing high by 20%/30%/40%. The total stock sleeve is 30%/45%/60% according to the deepest active tier and is split proportional to active tiers. Each name is held until it closes at a new high; the rest stays in QQQ.",
        "- Strategy 3: start from 50% QQQ, 30% equal-weight AI-core basket (NVDA, TSM, GOOGL, MSFT, AMZN, META, ASML, AVGO), and 20% SGOV/cash-like ballast. AI-core names are raised to 1.5x/2.0x/2.5x/3.0x their base weight at 20%/30%/40%/50% drawdowns, capped at 18% per name and 60% total AI-core weight. QQQ drawdowns of 15%/25%/35% add 10%/20%/30% QLD, funded from SGOV first and then QQQ.",
        "",
        "Assumptions: zero transaction costs, zero taxes, daily close-to-close rebalancing to target weights, SGOV as the cash-like sleeve, and no survivorship adjustment beyond choosing today's Mag7/AI-core lists.",
        "",
        "## Results",
        "",
        markdown_table(table_rows),
        "",
        "## Takeaway",
        "",
        f"On these parameters, the higher Sharpe ratio is **{best.name}** at **{metrics_by_name[best.name]['sharpe']:.2f}**.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lookback-years",
        type=int,
        default=5,
        help="Trailing-year comparison window; pass 0 for the full common window",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Markdown output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    period2 = int(time.time()) + 24 * 60 * 60
    series_by_ticker = {ticker: fetch_price_series(ticker, period2=period2) for ticker in ALL_TICKERS}
    common_dates = common_trading_dates(series_by_ticker)
    lookback_years = None if args.lookback_years == 0 else args.lookback_years
    dates = select_lookback_dates(common_dates, lookback_years)
    returns = returns_by_ticker(series_by_ticker, dates)
    drawdowns: Dict[str, Dict[str, float]] = {}
    is_ath: Dict[str, Dict[str, bool]] = {}
    for ticker, series in series_by_ticker.items():
        drawdown, ath = running_drawdown_and_ath(series)
        drawdowns[ticker] = drawdown
        is_ath[ticker] = ath

    results = [
        simulate_qqq_buy_hold(dates, returns),
        simulate_qqq_tqqq_strategy(dates, returns, drawdowns[QQQ], is_ath[QQQ]),
        simulate_mag7_drawdown_strategy(dates, returns, drawdowns, is_ath),
        simulate_ai_core_strategy(dates, returns, drawdowns),
    ]
    metrics_by_name = {result.name: annualized_metrics(result) for result in results}
    if args.output:
        output_path = Path(args.output)
    elif lookback_years is None:
        output_path = Path("results/strategy_comparison_full_common_2026-06-23.md")
    else:
        output_path = Path(f"results/strategy_comparison_{lookback_years}y_2026-06-23.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_summary(output_path, results, metrics_by_name, data_end=dates[-1], lookback_years=lookback_years)
    print(output_path)


if __name__ == "__main__":
    main()
