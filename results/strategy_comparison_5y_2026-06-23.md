# QQQ/TQQQ vs QQQ+Mag7 vs AI-core drawdown strategy backtest

Data source: Yahoo Finance daily chart API, adjusted close for returns, close for drawdown/new-high triggers. Data fetched through 2026-06-22.
Common comparison window: 2021-06-22 to 2026-06-22 (1254 daily returns, trailing 5-year window).

## Strategy definitions

- Benchmark: 100% QQQ buy-and-hold.
- Strategy 1: start from 100% QQQ. If QQQ is below its prior closing high by 10%, raise TQQQ weight to 30%; if it is below by 20%, raise TQQQ weight to 60%. Keep the highest reached TQQQ tier until QQQ closes at a new high, then reset to 100% QQQ.
- Strategy 2: start from 100% QQQ. For Mag7 stocks (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA), open/raise a stock sleeve when a name is below its own prior closing high by 20%/30%/40%. The total stock sleeve is 30%/45%/60% according to the deepest active tier and is split proportional to active tiers. Each name is held until it closes at a new high; the rest stays in QQQ.
- Strategy 3: start from 50% QQQ, 30% equal-weight AI-core basket (NVDA, TSM, GOOGL, MSFT, AMZN, META, ASML, AVGO), and 20% SGOV/cash-like ballast. AI-core names are raised to 1.5x/2.0x/2.5x/3.0x their base weight at 20%/30%/40%/50% drawdowns, capped at 18% per name and 60% total AI-core weight. QQQ drawdowns of 15%/25%/35% add 10%/20%/30% QLD, funded from SGOV first and then QQQ.

Assumptions: zero transaction costs, zero taxes, daily close-to-close rebalancing to target weights, SGOV as the cash-like sleeve, and no survivorship adjustment beyond choosing today's Mag7/AI-core lists.

## Results

| Portfolio | Sharpe | CAGR | Ann. vol | Max drawdown | Total return | $1 grows to | Avg TQQQ wt | Avg Mag7 sleeve | Avg AI core | Avg QLD wt | Avg SGOV/cash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark: QQQ buy and hold | 0.81 | 16.95% | 22.64% | -35.12% | 118.77% | 2.19 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Strategy 1: QQQ drawdown -> TQQQ | 0.71 | 23.10% | 41.22% | -59.78% | 182.61% | 2.83 | 26.99% | 0.00% | 0.00% | 0.00% | 0.00% |
| Strategy 2: QQQ + Mag7 drawdown sleeve | 1.03 | 31.85% | 31.89% | -46.21% | 298.46% | 3.98 | 0.00% | 51.71% | 0.00% | 0.00% | 0.00% |
| Strategy 3: AI core + cash + QLD overlay | 0.92 | 22.91% | 26.18% | -41.08% | 180.44% | 2.80 | 0.00% | 0.00% | 39.11% | 3.84% | 12.37% |

## Takeaway

On these parameters, the higher Sharpe ratio is **Strategy 2: QQQ + Mag7 drawdown sleeve** at **1.03**.
