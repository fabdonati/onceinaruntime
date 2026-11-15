# One account, five bars

The tiny [input CSV](account.csv) contains invented prices. A bar is just a time
step here; these are not observed market prices. Use spans 2 and 3 and start
with 1,000 cash. The first three bars warm up both averages, so the first possible
trade is at bar 3's open.

| Bar | Open | Close | What the account does |
| --- | ---: | ---: | --- |
| 0 | 100 | 100 | Initialize both averages to 100; no trading. |
| 1 | 100 | 120 | Warm up. |
| 2 | 100 | 110 | Fast EMA is approximately 111.1111; slow EMA is 110. Prepare a buy for the next open. |
| 3 | 100 | 102 | Buy at 100. At the close, fast EMA is approximately 105.0370; slow EMA is 106. Prepare a sale. |
| 4 | 99 | 100 | Sell at 99. The final close cannot produce another executable trade. |

Ignoring fees for a moment, this buys 10 shares, marks them at 1,020, then sells
them for 990. The signal at bar 3's close cannot sell at that close or go back
and sell at bar 3's open. The next opening price is 99, and that overnight gap
belongs to the account's history.

The checked engine charges one basis point of traded notional on each side:

```text
shares bought = 1000 / (100 * 1.0001)       = 9.99900009999...
entry fee     = shares * 100 * 0.0001      = 0.099990001...
bar 3 equity  = shares * 102               = 1019.898010199...
exit fee      = shares * 99 * 0.0001       = 0.098990101...
final cash    = shares * 99 * 0.9999       = 989.802019798...
```

| Required result | Value, rounded for reading |
| --- | ---: |
| Final cash | 989.802019798 |
| Net return | −1.019798% |
| Buy/sell events | 2 |
| Turnover / initial capital | 1.989801020 |
| Total fees | 0.198980102 |
| Maximum close-to-close drawdown | 2.950882% |

The drawdown is measured from the marked peak of 1,019.8980 to the final
989.8020, rather than only from the initial 1,000. A separate test checks a
position still open on the final bar: it sells at the final close, pays the exit
fee, and replaces that last mark with the remaining cash.

Both loop orders must reproduce this entire sequence. With more configurations,
they may visit other accounts between these two updates, but each account must
still see bar 3 before bar 4. The [Python reference](../analysis/reference.py)
uses a transaction ledger and equity history; the [C++ implementation](../src/replay.cpp)
uses running state. The tests compare those two accounts and check all four
C++ variants for exact output agreement.
