# Core QQQ plus prioritized dip-trading backtest

This is not investment advice. It is a simple historical simulation using adjusted close data.

## Setup

- Universe: AAPL, MSFT, AMZN, GOOGL, META, TSLA, TSM, AMD
- Priority order: GOOGL, AAPL, TSM
- Start/end: 2023-01-03 to 2026-03-31
- Core asset: QQQ
- Core QQQ floor: 70.00%
- Trading sleeve cap: 30.00%
- Minimum trade size: 1.00% of current portfolio value
- Buy drawdowns: 25.00%, 35.00%, 45.00% from prior all-time high
- Buy weights: 10.00%, 10.00%, 10.00% of current portfolio value
- Sell gains: 20.00%, 30.00% of remaining cost basis, or sell all near 90% of prior high

## Metrics

| name                |   final_value | total_return   | cagr   | annualized_volatility   |   sharpe | max_drawdown   |
|:--------------------|--------------:|:---------------|:-------|:------------------------|---------:|:---------------|
| core_qqq_trade_dips |        2.5692 | 156.92%        | 33.82% | 23.38%                  |     1.37 | -26.68%        |
| QQQ_buy_hold        |        2.2245 | 122.45%        | 28.00% | 19.87%                  |     1.35 | -22.77%        |
| DIA_buy_hold        |        1.4789 | 47.89%         | 12.84% | 13.47%                  |     0.97 | -15.95%        |
| equal_weight_stocks |        3.1704 | 217.04%        | 42.80% | 27.73%                  |     1.43 | -31.06%        |

## Trade count

- Total trades: 54
- Buys: 25
- Sells: 29
