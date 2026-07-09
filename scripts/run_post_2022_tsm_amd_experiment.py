#!/usr/bin/env python3
"""Run the post-2022 Strategy 2 experiment with TSM and AMD added."""

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
from sweep_strategy2_params import build_levels, format_levels, format_pct


DEFAULT_TICKERS = (*MAG7, "TSM", "AMD")
DEFAULT_BENCHMARKS = ("QQQ", "DIA")


def equal_weight_buy_and_hold(prices: pd.DataFrame, tickers: tuple[str, ...], initial_capital: float) -> pd.Series:
    normalized = prices[list(tickers)].divide(prices[list(tickers)].iloc[0])
    return normalized.mean(axis=1) * initial_capital


def metrics_row(name: str, equity: pd.Series, risk_free_rate: float) -> dict[str, object]:
    metrics = compute_metrics(equity, risk_free_rate)
    return {
        "name": name,
        "final_value": metrics.final_value,
        "total_return": metrics.total_return,
        "cagr": metrics.cagr,
        "annualized_volatility": metrics.annualized_volatility,
        "sharpe": metrics.sharpe,
        "max_drawdown": metrics.max_drawdown,
    }


def display_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["final_value"] = output["final_value"].map(lambda value: f"{value:.4f}")
    for column in ["total_return", "cagr", "annualized_volatility", "max_drawdown"]:
        output[column] = output[column].map(format_pct)
    output["sharpe"] = output["sharpe"].map(lambda value: f"{value:.2f}")
    return output


def display_strategies(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame[
        [
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


def write_summary(
    path: Path,
    prices: pd.DataFrame,
    args: argparse.Namespace,
    sweep_results: pd.DataFrame,
    benchmark_metrics: pd.DataFrame,
) -> None:
    top_by_sharpe = sweep_results.sort_values("sharpe", ascending=False).head(args.top_n)
    top_by_cagr = sweep_results.sort_values("cagr", ascending=False).head(args.top_n)
    top_with_40dd = sweep_results[sweep_results["max_drawdown"] >= -0.40].sort_values("sharpe", ascending=False).head(args.top_n)

    best = top_by_sharpe.iloc[0]
    qqq = benchmark_metrics[benchmark_metrics["name"] == "QQQ_buy_hold"].iloc[0]
    equal_weight = benchmark_metrics[benchmark_metrics["name"] == "equal_weight_stocks"].iloc[0]

    lines = [
        "# Post-2022 Strategy 2 experiment with TSM and AMD",
        "",
        "This is not investment advice. It is a simple historical simulation using adjusted close data.",
        "",
        "## Setup",
        "",
        f"- Universe: {', '.join(args.tickers)}",
        f"- Start/end: {prices.index[0].date()} to {prices.index[-1].date()}",
        "- 2022 drawdown is skipped by starting the test on 2023-01-01.",
        "- Idle capital: QQQ only",
        f"- First buy drawdowns tested: {', '.join(format_pct(item) for item in args.first_levels)}",
        f"- Buy ladder: {args.level_count} levels, {format_pct(args.level_step)} apart",
        f"- Per-level tranche weights tested: {', '.join(format_pct(item) for item in args.tranche_weights)}",
        "- Comparisons: QQQ buy-and-hold, DIA buy-and-hold, and equal-weight buy-and-hold across the stock universe",
        "",
        "## Comparisons",
        "",
        display_metrics(benchmark_metrics).to_markdown(index=False),
        "",
        "## Top Strategy 2 combinations by Sharpe",
        "",
        display_strategies(top_by_sharpe).to_markdown(index=False),
        "",
        "## Top Strategy 2 combinations by CAGR",
        "",
        display_strategies(top_by_cagr).to_markdown(index=False),
        "",
        "## Top Strategy 2 combinations with max drawdown no worse than -40%",
        "",
        display_strategies(top_with_40dd).to_markdown(index=False) if not top_with_40dd.empty else "No combinations matched.",
        "",
        "## Quick read",
        "",
        (
            f"- Best Sharpe strategy: {best['levels']} with {format_pct(best['tranche_weight'])} tranches; "
            f"Sharpe {best['sharpe']:.2f}, CAGR {format_pct(best['cagr'])}, max drawdown {format_pct(best['max_drawdown'])}."
        ),
        (
            f"- QQQ buy-and-hold: Sharpe {qqq['sharpe']:.2f}, CAGR {format_pct(qqq['cagr'])}, "
            f"max drawdown {format_pct(qqq['max_drawdown'])}."
        ),
        (
            f"- Equal-weight stocks: Sharpe {equal_weight['sharpe']:.2f}, CAGR {format_pct(equal_weight['cagr'])}, "
            f"max drawdown {format_pct(equal_weight['max_drawdown'])}."
        ),
        "- In this post-2022 window, adding TSM and AMD makes the stock basket benchmark very strong; compare Strategy 2 against that benchmark, not just QQQ.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--benchmarks", default=",".join(DEFAULT_BENCHMARKS))
    parser.add_argument("--base-asset", default="QQQ")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-04-01", help="Exclusive end date; default includes March 2026.")
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--first-levels", default="0.10,0.15,0.20,0.25,0.30")
    parser.add_argument("--level-step", type=float, default=0.10)
    parser.add_argument("--level-count", type=int, default=4)
    parser.add_argument("--tranche-weights", default="0.025,0.05,0.075,0.10,0.15")
    parser.add_argument("--cache-dir", default="data")
    parser.add_argument("--output-dir", default="results/strategy2_post_2022_tsm_amd")
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    args.tickers = parse_csv_list(args.tickers)
    args.benchmarks = parse_csv_list(args.benchmarks)
    args.base_asset = args.base_asset.upper()
    args.first_levels = parse_float_list(args.first_levels)
    args.tranche_weights = parse_float_list(args.tranche_weights)

    all_tickers = tuple(dict.fromkeys((*args.tickers, *args.benchmarks, args.base_asset)))
    cache_name = "_".join(all_tickers) + f"_{args.start}_{args.end or 'latest'}.csv"
    prices = download_prices(
        all_tickers,
        start=args.start,
        end=args.end,
        cache_path=Path(args.cache_dir) / cache_name,
        refresh=args.refresh_data,
    )

    benchmark_rows = [
        metrics_row(
            f"{benchmark}_buy_hold",
            buy_and_hold(prices[benchmark], args.initial_capital),
            args.risk_free_rate,
        )
        for benchmark in args.benchmarks
    ]
    benchmark_rows.append(
        metrics_row(
            "equal_weight_stocks",
            equal_weight_buy_and_hold(prices, args.tickers, args.initial_capital),
            args.risk_free_rate,
        )
    )
    benchmark_metrics = pd.DataFrame(benchmark_rows)

    strategy_rows: list[dict[str, object]] = []
    best_equity: pd.Series | None = None
    best_trades: pd.DataFrame | None = None
    best_sharpe = float("-inf")

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
                base_asset=args.base_asset,
            )
            metrics = compute_metrics(equity, args.risk_free_rate)
            strategy_rows.append(
                {
                    "base_asset": args.base_asset,
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
            if metrics.sharpe > best_sharpe:
                best_sharpe = metrics.sharpe
                best_equity = equity
                best_trades = trades

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sweep_results = pd.DataFrame(strategy_rows).sort_values("sharpe", ascending=False)
    sweep_results.to_csv(output_dir / "strategy2_parameter_sweep.csv", index=False)
    benchmark_metrics.to_csv(output_dir / "benchmark_metrics.csv", index=False)
    if best_equity is not None:
        best_equity.to_csv(output_dir / "best_strategy2_equity_curve.csv")
    if best_trades is not None:
        best_trades.to_csv(output_dir / "best_strategy2_trades.csv", index=False)
    write_summary(
        output_dir / "strategy2_post_2022_tsm_amd_summary.md",
        prices,
        args,
        sweep_results,
        benchmark_metrics,
    )

    print("Benchmarks:")
    print(benchmark_metrics.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("\nTop Strategy 2 combinations:")
    print(sweep_results.head(args.top_n).to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print(f"\nWrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
