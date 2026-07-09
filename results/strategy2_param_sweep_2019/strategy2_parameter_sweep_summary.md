# Strategy 2 parameter sweep

This is not investment advice. It is a simple historical simulation using adjusted close data.

## Sweep design

- Universe: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA
- Start/end: 2019-01-02 to 2026-07-09
- Benchmark: QQQ buy-and-hold
- Idle capital choices: cash, QQQ
- First buy drawdowns tested: 10.00%, 15.00%, 20.00%, 25.00%, 30.00%
- Level gap: 10.00%
- Number of buy levels: 4
- Per-level tranche weights tested: 2.50%, 5.00%, 7.50%, 10.00%, 15.00%

## Benchmark

| Final value | CAGR | Annual volatility | Sharpe | Max drawdown |
| ---: | ---: | ---: | ---: | ---: |
| 4.8798 | 23.48% | 24.03% | 1.00 | -35.12% |

## Top by Sharpe

| idle_capital   | levels          | tranche_weight   |   final_value | cagr   | annualized_volatility   |   sharpe | max_drawdown   |   trade_count |
|:---------------|:----------------|:-----------------|--------------:|:-------|:------------------------|---------:|:---------------|--------------:|
| QQQ            | 30%/40%/50%/60% | 15.00%           |       18.4874 | 47.42% | 35.31%                  |     1.28 | -52.62%        |            48 |
| QQQ            | 30%/40%/50%/60% | 7.50%            |       11.7003 | 38.72% | 29.99%                  |     1.25 | -47.28%        |            58 |
| QQQ            | 30%/40%/50%/60% | 10.00%           |       12.9762 | 40.64% | 31.77%                  |     1.24 | -51.41%        |            53 |
| cash           | 30%/40%/50%/60% | 2.50%            |        1.9279 | 9.13%  | 7.36%                   |     1.23 | -14.38%        |            62 |
| cash           | 30%/40%/50%/60% | 15.00%           |       10.9499 | 37.50% | 29.58%                  |     1.23 | -49.59%        |            48 |
| cash           | 30%/40%/50%/60% | 7.50%            |        5.1173 | 24.26% | 19.59%                  |     1.21 | -35.33%        |            59 |
| QQQ            | 25%/35%/45%/55% | 10.00%           |       12.2515 | 39.57% | 32.63%                  |     1.19 | -53.48%        |            63 |
| cash           | 30%/40%/50%/60% | 10.00%           |        6.5676 | 28.46% | 23.54%                  |     1.18 | -42.62%        |            53 |
| cash           | 30%/40%/50%/60% | 5.00%            |        3.2279 | 16.87% | 14.08%                  |     1.18 | -27.61%        |            62 |
| QQQ            | 30%/40%/50%/60% | 5.00%            |        8.5946 | 33.14% | 27.81%                  |     1.17 | -45.24%        |            62 |

## Top by CAGR

| idle_capital   | levels          | tranche_weight   |   final_value | cagr   | annualized_volatility   |   sharpe | max_drawdown   |   trade_count |
|:---------------|:----------------|:-----------------|--------------:|:-------|:------------------------|---------:|:---------------|--------------:|
| QQQ            | 30%/40%/50%/60% | 15.00%           |       18.4874 | 47.42% | 35.31%                  |     1.28 | -52.62%        |            48 |
| QQQ            | 15%/25%/35%/45% | 15.00%           |       13.1964 | 40.96% | 35.83%                  |     1.14 | -57.84%        |           117 |
| QQQ            | 20%/30%/40%/50% | 15.00%           |       13.1852 | 40.94% | 36.64%                  |     1.12 | -58.59%        |            74 |
| QQQ            | 30%/40%/50%/60% | 10.00%           |       12.9762 | 40.64% | 31.77%                  |     1.24 | -51.41%        |            53 |
| QQQ            | 25%/35%/45%/55% | 15.00%           |       12.8119 | 40.40% | 34.13%                  |     1.17 | -57.13%        |            56 |
| QQQ            | 25%/35%/45%/55% | 10.00%           |       12.2515 | 39.57% | 32.63%                  |     1.19 | -53.48%        |            63 |
| QQQ            | 20%/30%/40%/50% | 10.00%           |       12.0574 | 39.27% | 33.46%                  |     1.16 | -55.58%        |            87 |
| QQQ            | 30%/40%/50%/60% | 7.50%            |       11.7003 | 38.72% | 29.99%                  |     1.25 | -47.28%        |            58 |
| QQQ            | 15%/25%/35%/45% | 10.00%           |       11.1122 | 37.77% | 32.94%                  |     1.14 | -54.66%        |           133 |
| cash           | 30%/40%/50%/60% | 15.00%           |       10.9499 | 37.50% | 29.58%                  |     1.23 | -49.59%        |            48 |

## Top by Sharpe with max drawdown no worse than -40%

| idle_capital   | levels          | tranche_weight   |   final_value | cagr   | annualized_volatility   |   sharpe | max_drawdown   |   trade_count |
|:---------------|:----------------|:-----------------|--------------:|:-------|:------------------------|---------:|:---------------|--------------:|
| cash           | 30%/40%/50%/60% | 2.50%            |        1.9279 | 9.13%  | 7.36%                   |     1.23 | -14.38%        |            62 |
| cash           | 30%/40%/50%/60% | 7.50%            |        5.1173 | 24.26% | 19.59%                  |     1.21 | -35.33%        |            59 |
| cash           | 30%/40%/50%/60% | 5.00%            |        3.2279 | 16.87% | 14.08%                  |     1.18 | -27.61%        |            62 |
| cash           | 25%/35%/45%/55% | 2.50%            |        1.9811 | 9.52%  | 8.42%                   |     1.13 | -17.89%        |            75 |
| cash           | 20%/30%/40%/50% | 2.50%            |        2.0915 | 10.32% | 9.34%                   |     1.1  | -19.88%        |           104 |
| cash           | 25%/35%/45%/55% | 5.00%            |        3.3948 | 17.66% | 16.42%                  |     1.08 | -33.86%        |            75 |
| cash           | 15%/25%/35%/45% | 2.50%            |        2.2047 | 11.09% | 10.61%                  |     1.05 | -23.60%        |           154 |
| cash           | 20%/30%/40%/50% | 5.00%            |        3.7437 | 19.20% | 18.58%                  |     1.04 | -37.74%        |           103 |
| cash           | 10%/20%/30%/40% | 2.50%            |        2.2706 | 11.53% | 11.58%                  |     1    | -24.27%        |           205 |

## Quick read

- Idle capital policy is the biggest driver: using QQQ as the parking asset materially raises return and Sharpe, but also increases drawdown.
- In this sample, deeper first buys generally rank better than earlier entries; the result is sensitive to the large 2022 drawdown and rebound.
- Larger tranches improve upside when the rebound is strong, but they also concentrate risk during large selloffs.
- The drawdown-filtered table is useful if the goal is to avoid turning a higher Sharpe into an uncomfortable realized loss path.
