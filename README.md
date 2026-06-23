# finance

This repository contains small, reproducible finance analysis scripts.

## QQQ/TQQQ vs QQQ+Mag7 vs AI-core drawdown backtest

Run:

```bash
/usr/bin/python3 scripts/compare_qqq_mag7_strategies.py
```

The script fetches Yahoo Finance daily data and writes the summary to
`results/strategy_comparison_5y_2026-06-23.md`.

Pass `--lookback-years 0` to use the full common data window.
