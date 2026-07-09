# Strategy 2 backtest summary

This is not investment advice. It is a simple historical simulation using adjusted close data.

## Parameters

- Universe: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA
- Start/end: 2019-01-02 to 2026-07-09
- Drawdown levels: 20%, 30%, 40%, 50%
- Tranche weights: 5%, 5%, 5%, 5% of current portfolio value
- Idle capital: QQQ
- Initial capital: 1

## Metrics

|              |   final_value | total_return   | cagr   | annualized_volatility   |   sharpe | max_drawdown   |
|:-------------|--------------:|:---------------|:-------|:------------------------|---------:|:---------------|
| strategy2    |        8.5188 | 751.88%        | 32.98% | 28.97%                  |     1.13 | -48.66%        |
| QQQ_buy_hold |        4.8818 | 388.18%        | 23.49% | 24.03%                  |     1    | -35.12%        |

## Trade count

- Total trades: 103
- Buys: 71
- Sells: 32
