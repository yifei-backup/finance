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

Using adjusted close data from 2019-01-02 through 2026-07-09:

| Run | Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strategy 2, idle cash | 3.7439 | 19.20% | 18.58% | 1.04 | -37.74% |
| QQQ buy-and-hold | 4.8818 | 23.49% | 24.03% | 1.00 | -35.12% |
| Strategy 2, idle QQQ | 8.5188 | 32.98% | 28.97% | 1.13 | -48.66% |

From 2019 onward, both strategy-2 variants have higher Sharpe than QQQ
buy-and-hold. The cash version still lags QQQ in total return, while the
QQQ-parking version beats QQQ on both return and Sharpe but with a much deeper
drawdown.

## Strategy 2 parameter sweep from 2019

The first parameter sweep varies the most important assumptions:

- Idle capital: cash vs QQQ
- First buy trigger: 10%, 15%, 20%, 25%, or 30% below the prior all-time high
- Buy ladder: four levels spaced 10 percentage points apart
- Per-level tranche size: 2.5%, 5%, 7.5%, 10%, or 15% of current portfolio value

Top results from 2019-01-02 through 2026-07-09:

| Rank idea | Idle capital | Buy levels | Tranche | Final value | CAGR | Sharpe | Max drawdown |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Highest Sharpe | QQQ | 30%/40%/50%/60% | 15.0% | 18.4874 | 47.42% | 1.28 | -52.62% |
| High Sharpe, lower drawdown | cash | 30%/40%/50%/60% | 7.5% | 5.1173 | 24.26% | 1.21 | -35.33% |
| Conservative drawdown | cash | 30%/40%/50%/60% | 5.0% | 3.2279 | 16.87% | 1.18 | -27.61% |
| Original 2019 cash baseline | cash | 20%/30%/40%/50% | 5.0% | 3.7437 | 19.20% | 1.04 | -37.74% |

The first sweep suggests that the most important parameter is the idle-capital
choice. Parking idle capital in QQQ drives much higher returns and Sharpe, but
creates substantially deeper drawdowns. Among drawdown triggers, this sample
favored waiting for deeper declines before buying; the best-ranked combinations
cluster around a first buy at 30% below the prior high.
