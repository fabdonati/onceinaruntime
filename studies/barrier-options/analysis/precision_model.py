"""Independent date-wise FP32 oracle and cross-precision descriptive errors."""
import math
import numpy as np
from model import DISCOUNT


def oracle32(factors, barrier, discount=DISCOUNT, spot=100., strike=100.):
    factors = np.asarray(factors, dtype=np.float32)
    if factors.ndim != 2:
        raise ValueError('reference expects paths by dates')
    n, steps = factors.shape
    stock = np.full(n, np.float32(spot), dtype=np.float32)
    limit = np.float32(barrier)
    hit = stock >= limit
    lifetime = np.zeros(n, dtype='<u8')
    for date in range(steps):
        live = ~hit
        # NumPy ufuncs round each operation in binary32; this is not a C++ lane loop.
        stock[live] = np.multiply(stock[live], factors[live, date], dtype=np.float32)
        lifetime[live] += 1
        hit |= stock >= limit
    intrinsic = np.maximum(np.subtract(stock, np.float32(strike), dtype=np.float32), np.float32(0))
    payoff = np.multiply(intrinsic, np.float32(discount), dtype=np.float32)
    payoff[hit] = np.float32(0)
    return payoff, lifetime, hit.astype(np.uint8)


def ordered_mean(values):
    total = 0.
    for value in values:
        total += float(value)
    return total / len(values) if len(values) else 0.


def errors(candidate, reference):
    payoff, dates, knocked = candidate
    expected, ref_dates, ref_knocked = reference
    if not (payoff.shape == expected.shape == dates.shape == ref_dates.shape == knocked.shape == ref_knocked.shape):
        raise ValueError('accuracy arrays differ in shape')
    diff = payoff.astype(np.float64) - expected.astype(np.float64)
    n = len(diff)
    return dict(paths=n,
                knockout_disagreements=int(np.count_nonzero(knocked != ref_knocked)),
                candidate_only_knockouts=int(np.count_nonzero((knocked != 0) & (ref_knocked == 0))),
                reference_only_knockouts=int(np.count_nonzero((knocked == 0) & (ref_knocked != 0))),
                stopping_date_disagreements=int(np.count_nonzero(dates != ref_dates)),
                zero_payoff_disagreements=int(np.count_nonzero((payoff == 0) != (expected == 0))),
                maximum_absolute_payoff_error=float(np.max(np.abs(diff))) if n else 0.,
                rms_payoff_error=float(np.sqrt(np.mean(diff * diff))) if n else 0.,
                mean_signed_payoff_error=float(np.mean(diff)) if n else 0.,
                candidate_price=ordered_mean(payoff), reference_price=ordered_mean(expected),
                price_difference=ordered_mean(payoff)-ordered_mean(expected),
                paired_difference_standard_error=float(np.std(diff, ddof=1)/math.sqrt(n)) if n > 1 else None)
