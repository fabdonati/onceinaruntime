"""Small independent ledger reference. Not used by any timed C++ path."""
import math
from itertools import accumulate, combinations


def features(bars, spans):
    columns = []
    for span in spans:
        alpha = 2.0 / (span + 1.0)
        values = [bars[0][2]]
        for _, _, close in bars[1:]:
            values.append(alpha * close + (1.0 - alpha) * values[-1])
        columns.append(values)
    return list(zip(*columns))


def account(bars, targets, first, capital=1000.0, fee=0.0001, diagnose=True):
    """Record transactions and equity; derive totals from the ledger each time.

    Targets are independently computed from completed closes. Keeping an explicit
    transaction list and equity history avoids sharing C++'s running accumulators.
    """
    balance, quantity = capital, 0.0
    ledger, marks, traces = [], [capital], []
    for t in range(first, len(bars)):
        _, opening, closing = bars[t]
        target = targets[t - 1]
        event, opening_fee, liquidation_fee = 0, 0.0, 0.0
        if target != (quantity > 0):
            if target:
                quantity = balance / (opening * (1 + fee))
                gross = quantity * opening
                opening_fee = gross * fee
                balance = 0.0
                event = 1
            else:
                gross = quantity * opening
                opening_fee = gross * fee
                balance = gross - opening_fee
                quantity = 0.0
                event = -1
            ledger.append((gross, opening_fee))
        cash_after_open, shares_after_open = balance, quantity
        if t == len(bars) - 1 and quantity > 0:
            gross = quantity * closing
            liquidation_fee = gross * fee
            balance = gross - liquidation_fee
            quantity = 0.0
            ledger.append((gross, liquidation_fee))
        marks.append(balance + quantity * closing)
        if diagnose:
            drawdowns = [1 - value / peak for value, peak in zip(marks, accumulate(marks, max))]
            traces.append(dict(bar=t, target_long=int(target), opening_event=event,
                               cash_after_open=cash_after_open, shares_after_open=shares_after_open,
                               opening_fee=opening_fee, liquidation_fee=liquidation_fee,
                               equity=marks[-1], cash=balance, shares=quantity, peak=max(marks),
                               max_drawdown=max(drawdowns), notional=math.fsum(x[0] for x in ledger),
                               fees=math.fsum(x[1] for x in ledger), trades=len(ledger)))
    peak = capital
    drawdown = 0.0
    for mark in marks:
        peak = max(peak, mark)
        drawdown = max(drawdown, 1 - mark / peak)
    summary = dict(final_cash=balance, net_return=balance/capital - 1,
                   trades=len(ledger), turnover=math.fsum(x[0] for x in ledger)/capital,
                   max_drawdown=drawdown, fees=math.fsum(x[1] for x in ledger))
    return summary, traces


def replay(bars, spans, count=None, capital=1000.0, fee=0.0001, diagnose=True):
    matrix = features(bars, spans)
    configs = list(combinations(range(len(spans)), 2))
    if count is not None:
        configs = configs[:count]
    summaries, traces = [], []
    for index, (fast, slow) in enumerate(configs):
        targets = [row[fast] > row[slow] for row in matrix]
        summary, trace = account(bars, targets, max(spans), capital, fee, diagnose)
        summaries.append(dict(config=index, fast=spans[fast], slow=spans[slow], **summary))
        traces.extend(dict(config=index, **item) for item in trace)
    return matrix, summaries, traces
