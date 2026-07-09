#!/usr/bin/env python3
"""Run a parameter sweep for the Mag7 drawdown-buying strategy."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtest_strategy2 import (
    MAG7,
    backtest_dip_strategy,
    buy_and_hold,
    compute_metrics,
    download_prices,
    parse_csv_list,
    parse_float_list,
)


def build_levels(first_level: float, step: float, count: int) -> tuple[float, ...]:
    return tuple(round(first_level + step * index, 4) for index in range(count))


def format_pct(value: float) -> str:
    return f"{value:.2%}"


def format_levels(levels: tuple[float, ...]) -> str:
    return "/".join(f"{level:.0%}" for level in levels)


def write_summary(
    path: Path,
    results: pd.DataFrame,
    benchmark: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    args: argparse.Namespace,
) -> None:
    top_by_sharpe = results.sort_values("sharpe", ascending=False).head(args.top_n)
    top_by_cagr = results.sort_values("cagr", ascending=False).head(args.top_n)
    top_with_40dd = results[results["max_drawdown"] >= -0.40].sort_values("sharpe", ascending=False).head(args.top_n)

    def display(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        output = frame[
            [
                "idle_capital",
                "levels",
                "tranche_weight",
                "final_value",
                "cagr",
                "annualized_volatility",
                "sharpe",
                "max_drawdown",
                "trade_count",
            ]
        ].copy()
        output["tranche_weight"] = output["tranche_weight"].map(format_pct)
        output["final_value"] = output["final_value"].map(lambda value: f"{value:.4f}")
        for column in ["cagr", "annualized_volatility", "max_drawdown"]:
            output[column] = output[column].map(format_pct)
        output["sharpe"] = output["sharpe"].map(lambda value: f"{value:.2f}")
        return output

    lines = [
        "# Strategy 2 parameter sweep",
        "",
        "This is not investment advice. It is a simple historical simulation using adjusted close data.",
        "",
        "## Sweep design",
        "",
        f"- Universe: {', '.join(args.tickers)}",
        f"- Start/end: {start_date.date()} to {end_date.date()}",
        f"- Benchmark: {args.benchmark} buy-and-hold",
        f"- Idle capital choices: {', '.join('cash' if item == 'cash' else item for item in args.idle_choices)}",
        f"- First buy drawdowns tested: {', '.join(format_pct(item) for item in args.first_levels)}",
        f"- Level gap: {format_pct(args.level_step)}",
        f"- Number of buy levels: {args.level_count}",
        f"- Per-level tranche weights tested: {', '.join(format_pct(item) for item in args.tranche_weights)}",
        "",
        "## Benchmark",
        "",
        "| Final value | CAGR | Annual volatility | Sharpe | Max drawdown |",
        "| ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {benchmark['final_value']:.4f} | {format_pct(benchmark['cagr'])} | "
            f"{format_pct(benchmark['annualized_volatility'])} | {benchmark['sharpe']:.2f} | "
            f"{format_pct(benchmark['max_drawdown'])} |"
        ),
        "",
        "## Top by Sharpe",
        "",
        display(top_by_sharpe).to_markdown(index=False),
        "",
        "## Top by CAGR",
        "",
        display(top_by_cagr).to_markdown(index=False),
        "",
        "## Top by Sharpe with max drawdown no worse than -40%",
        "",
        display(top_with_40dd).to_markdown(index=False) if not top_with_40dd.empty else "No combinations matched.",
        "",
        "## Quick read",
        "",
        "- Idle capital policy is the biggest driver: using QQQ as the parking asset materially raises return and Sharpe, but also increases drawdown.",
        "- Earlier first buys and larger tranches tend to improve upside in this Mag7 bull-market-heavy sample, but they also concentrate risk during large selloffs.",
        "- The drawdown-filtered table is useful if the goal is to avoid turning a higher Sharpe into an uncomfortable realized loss path.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(MAG7), help="Comma-separated stock universe.")
    parser.add_argument("--benchmark", default="QQQ", help="Benchmark ETF ticker.")
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--first-levels", default="0.10,0.15,0.20,0.25,0.30")
    parser.add_argument("--level-step", type=float, default=0.10)
    parser.add_argument("--level-count", type=int, default=4)
    parser.add_argument("--tranche-weights", default="0.025,0.05,0.075,0.10,0.15")
    parser.add_argument("--idle-choices", default="cash,QQQ")
    parser.add_argument("--cache-dir", default="data")
    parser.add_argument("--output-dir", default="results/strategy2_param_sweep_2019")
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    args.tickers = parse_csv_list(args.tickers)
    args.benchmark = args.benchmark.upper()
    args.first_levels = parse_float_list(args.first_levels)
    args.tranche_weights = parse_float_list(args.tranche_weights)
    args.idle_choices = tuple(item.strip().upper() if item.strip().lower() != "cash" else "cash" for item in args.idle_choices.split(",") if item.strip())

    base_assets = tuple(item for item in args.idle_choices if item != "cash")
    all_tickers = tuple(dict.fromkeys((*args.tickers, args.benchmark, *base_assets)))
    cache_name = "_".join(all_tickers) + f"_{args.start}_{args.end or 'latest'}.csv"
    prices = download_prices(
        all_tickers,
        start=args.start,
        end=args.end,
        cache_path=Path(args.cache_dir) / cache_name,
        refresh=args.refresh_data,
    )

    benchmark_equity = buy_and_hold(prices[args.benchmark], args.initial_capital)
    benchmark_metrics = compute_metrics(benchmark_equity, args.risk_free_rate)
    benchmark = pd.Series(
        {
            "final_value": benchmark_metrics.final_value,
            "total_return": benchmark_metrics.total_return,
            "cagr": benchmark_metrics.cagr,
            "annualized_volatility": benchmark_metrics.annualized_volatility,
            "sharpe": benchmark_metrics.sharpe,
            "max_drawdown": benchmark_metrics.max_drawdown,
        }
    )

    rows: list[dict[str, object]] = []
    for idle_choice in args.idle_choices:
        base_asset = None if idle_choice == "cash" else idle_choice
        for first_level in args.first_levels:
            levels = build_levels(first_level, args.level_step, args.level_count)
            for tranche_weight in args.tranche_weights:
                tranche_weights = tuple([tranche_weight] * args.level_count)
                equity, trades = backtest_dip_strategy(
                    prices=prices,
                    universe=args.tickers,
                    levels=levels,
                    tranche_weights=tranche_weights,
                    initial_capital=args.initial_capital,
                    base_asset=base_asset,
                )
                metrics = compute_metrics(equity, args.risk_free_rate)
                rows.append(
                    {
                        "idle_capital": idle_choice,
                        "first_level": first_level,
                        "levels": format_levels(levels),
                        "tranche_weight": tranche_weight,
                        "total_target_weight_per_stock": tranche_weight * args.level_count,
                        "final_value": metrics.final_value,
                        "total_return": metrics.total_return,
                        "cagr": metrics.cagr,
                        "annualized_volatility": metrics.annualized_volatility,
                        "sharpe": metrics.sharpe,
                        "max_drawdown": metrics.max_drawdown,
                        "trade_count": len(trades),
                        "buy_count": int(trades["action"].str.startswith("buy").sum()) if not trades.empty else 0,
                        "sell_count": int(trades["action"].str.startswith("sell").sum()) if not trades.empty else 0,
                    }
                )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    results.to_csv(output_dir / "strategy2_parameter_sweep.csv", index=False)
    benchmark.to_csv(output_dir / "benchmark_metrics.csv")
    write_summary(
        output_dir / "strategy2_parameter_sweep_summary.md",
        results,
        benchmark,
        prices.index[0],
        prices.index[-1],
        args,
    )

    print(results.head(args.top_n).to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print(f"\nWrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
