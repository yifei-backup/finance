# Strategy 2 backtest summary

This is not investment advice. It is a simple historical simulation using adjusted close data.

## Parameters

- Universe: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA
- Start/end: 2014-01-02 to 2026-07-09
- Drawdown levels: 20%, 30%, 40%, 50%
- Tranche weights: 5%, 5%, 5%, 5% of current portfolio value
- Idle capital: cash
- Initial capital: 1

## Metrics

|              |   final_value | total_return   | cagr   | annualized_volatility   |   sharpe | max_drawdown   |
|:-------------|--------------:|:---------------|:-------|:------------------------|---------:|:---------------|
| strategy2    |        5.9301 | 493.01%        | 15.28% | 15.69%                  |     0.99 | -37.74%        |
| QQQ_buy_hold |        9.1442 | 814.42%        | 19.34% | 21.41%                  |     0.94 | -35.12%        |

## Trade count

- Total trades: 138
- Buys: 94
- Sells: 44
