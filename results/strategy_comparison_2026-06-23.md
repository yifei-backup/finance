# QQQ/TQQQ vs QQQ+Mag7 drawdown strategy backtest

Data source: Yahoo Finance daily chart API, adjusted close for returns, close for drawdown/new-high triggers. Data fetched through 2026-06-22.
Common comparison window: 2012-05-18 to 2026-06-22 (3541 daily returns).

## Strategy definitions

- Benchmark: 100% QQQ buy-and-hold.
- Strategy 1: start from 100% QQQ. If QQQ is below its prior closing high by 10%, raise TQQQ weight to 30%; if it is below by 20%, raise TQQQ weight to 60%. Keep the highest reached TQQQ tier until QQQ closes at a new high, then reset to 100% QQQ.
- Strategy 2: start from 100% QQQ. For Mag7 stocks (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA), open/raise a stock sleeve when a name is below its own prior closing high by 20%/30%/40%. The total stock sleeve is 30%/45%/60% according to the deepest active tier and is split proportional to active tiers. Each name is held until it closes at a new high; the rest stays in QQQ.

Assumptions: zero transaction costs, zero taxes, daily close-to-close rebalancing to target weights, no cash yield, and no survivorship adjustment beyond choosing today's Mag7 list.

## Results

| Portfolio | Sharpe | CAGR | Ann. vol | Max drawdown | Total return | $1 grows to | Avg TQQQ wt | Avg Mag7 sleeve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark: QQQ buy and hold | 1.01 | 20.42% | 20.66% | -35.12% | 1,271.60% | 13.72 | 0.00% | 0.00% |
| Strategy 1: QQQ drawdown -> TQQQ | 0.99 | 34.97% | 37.23% | -59.78% | 6,747.05% | 68.47 | 32.06% | 0.00% |
| Strategy 2: QQQ + Mag7 drawdown sleeve | 1.20 | 33.30% | 26.99% | -46.21% | 5,647.98% | 57.48 | 0.00% | 50.91% |

## Takeaway

On these parameters, the higher Sharpe ratio is **Strategy 2: QQQ + Mag7 drawdown sleeve** at **1.20**.
