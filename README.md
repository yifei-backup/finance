# finance

Small, reproducible finance backtests.

## Strategy 2: buy Magnificent Seven drawdowns

The first implemented simulation models the idea of buying whichever
Magnificent Seven stock has fallen meaningfully from its own all-time high.

Default interpretation:

- Universe: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA
- Data: Yahoo Finance adjusted close prices
- Start date: 2014-01-01, so all seven stocks have enough public data
- Buy tranches: buy 5% of current portfolio value when a stock is down 20%,
  another 5% at 30%, another 5% at 40%, and another 5% at 50%
- Exit: sell the full stock position when it reaches a new adjusted-close
  all-time high
- Idle capital: cash by default
- Benchmark: QQQ buy-and-hold over the same dates

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/backtest_strategy2.py --refresh-data
```

Useful variations:

```bash
# Park idle capital in QQQ instead of cash.
python scripts/backtest_strategy2.py --base-asset QQQ --refresh-data

# Use larger tranches.
python scripts/backtest_strategy2.py --tranche-weights 0.1,0.1,0.1,0.1 --refresh-data
```

Outputs are written to `results/`:

- `strategy2_metrics.csv`
- `strategy2_equity_curve.csv`
- `strategy2_trades.csv`
- `strategy2_summary.md`

## Current run summary

Using adjusted close data from 2014-01-02 through 2026-07-09:

| Run | Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strategy 2, idle cash | 5.9301 | 15.28% | 15.69% | 0.99 | -37.74% |
| QQQ buy-and-hold | 9.1442 | 19.34% | 21.41% | 0.94 | -35.12% |
| Strategy 2, idle QQQ | 18.0112 | 25.99% | 25.34% | 1.04 | -48.66% |

Under these assumptions, the cash version has a slightly higher Sharpe than
QQQ buy-and-hold but lower absolute return. The QQQ-parking version has the
highest Sharpe and return in this run, while taking a meaningfully deeper max
drawdown.
