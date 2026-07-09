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

## Post-2022 sweep with TSM and AMD

This run skips the 2022 deep drawdown by starting on 2023-01-01, ends at
2026-03-31, adds TSM and AMD to the stock universe, and always parks idle
capital in QQQ.

Universe: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, TSM, AMD.

Comparison buy-and-hold results from 2023-01-03 through 2026-03-31:

| Benchmark | Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| QQQ buy-and-hold | 2.2245 | 28.00% | 19.87% | 1.35 | -22.77% |
| DIA buy-and-hold | 1.4789 | 12.84% | 13.47% | 0.97 | -15.95% |
| Equal-weight stocks | 4.1732 | 55.44% | 30.63% | 1.60 | -31.61% |

Top Strategy 2 parameter results:

| Rank idea | Buy levels | Tranche | Final value | CAGR | Sharpe | Max drawdown |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Highest Sharpe | 30%/40%/50%/60% | 7.5% | 3.1054 | 41.89% | 1.47 | -25.27% |
| Higher return, similar Sharpe | 30%/40%/50%/60% | 10.0% | 3.4044 | 45.97% | 1.47 | -26.18% |
| Highest CAGR | 20%/30%/40%/50% | 15.0% | 3.6619 | 49.29% | 1.30 | -33.43% |

In this post-2022 window, Strategy 2 beats QQQ and DIA on CAGR and Sharpe, but
does not beat simply holding the nine-stock equal-weight basket. The
equal-weight stock basket benefits heavily from the strong post-2022 rebound in
mega-cap AI and semiconductor names, especially with TSM and AMD included.

## Core QQQ plus prioritized dip-trading strategy

This simulation models a more conservative "long-term conviction plus short-term
arbitrage" structure:

- Keep at least 70% of the portfolio in QQQ.
- Use at most 30% as a trading sleeve.
- Buy from QQQ into stocks when they fall 25%, 35%, and 45% from their prior
  all-time high.
- Each buy level targets 10% of portfolio value, subject to the 30% total
  trading-sleeve cap.
- Sell one-half of a position after a 20% gain on remaining cost basis, another
  one-half after a 30% gain, or sell all once the stock returns to 90% of its
  prior all-time high.
- Priority order: GOOGL, NVDA, AAPL, TSM.

Results from 2023-01-03 through 2026-03-31:

| Run | Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nine-stock universe, priority order applied | 2.7008 | 35.90% | 23.68% | 1.42 | -26.83% |
| Four priority stocks only | 2.4202 | 31.37% | 20.60% | 1.43 | -22.44% |
| QQQ buy-and-hold | 2.2245 | 28.00% | 19.87% | 1.35 | -22.77% |
| DIA buy-and-hold | 1.4789 | 12.84% | 13.47% | 0.97 | -15.95% |
| Nine-stock equal-weight buy-and-hold | 4.1732 | 55.44% | 30.63% | 1.60 | -31.61% |
| Four-stock equal-weight buy-and-hold | 5.5769 | 70.00% | 34.46% | 1.72 | -33.73% |

The priority dip-trading strategy improves on QQQ buy-and-hold in this window,
with only a modest increase in drawdown for the nine-stock version. However, it
still trails equal-weight buy-and-hold because this sample strongly rewards
simply owning the AI and semiconductor winners through the whole period.

### NVDA excluded

Because NVDA dominates the direct buy-and-hold results, the same core QQQ
dip-trading strategy was rerun with NVDA excluded.

Results from 2023-01-03 through 2026-03-31:

| Run | Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| Eight-stock universe, NVDA excluded | 2.5692 | 33.82% | 23.38% | 1.37 | -26.68% |
| Three priority stocks only: GOOGL/AAPL/TSM | 2.2302 | 28.10% | 20.23% | 1.33 | -23.14% |
| QQQ buy-and-hold | 2.2245 | 28.00% | 19.87% | 1.35 | -22.77% |
| Eight-stock equal-weight buy-and-hold | 3.1704 | 42.80% | 27.73% | 1.43 | -31.06% |
| Three-stock equal-weight buy-and-hold | 3.3706 | 45.52% | 25.14% | 1.63 | -31.11% |

Excluding NVDA weakens the dip-trading edge materially. The eight-stock version
still beats QQQ on return and narrowly on Sharpe, but with a deeper drawdown.
The three-priority-stock version is essentially a QQQ-like result with slightly
lower Sharpe. This suggests that much of the recent benefit came from having
access to very strong rebound names rather than from the trading rule alone.
