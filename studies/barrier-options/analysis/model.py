"""Canonical input generation and an independent date-wise NumPy oracle."""
import math
import numpy as np

SPOT, STRIKE, RATE, DIVIDEND, SIGMA, MATURITY = 100., 100., .02, 0., .2, 1.
DISCOUNT = math.exp(-RATE * MATURITY)

def generate(paths, steps, seed, sigma=SIGMA):
    """PCG64, path-major order, chunks of at most 4096 paths; binary64 output."""
    rng = np.random.Generator(np.random.PCG64(seed))
    result = np.empty((paths, steps), dtype="<f8")
    dt = MATURITY / steps
    drift = (RATE - DIVIDEND - .5 * sigma * sigma) * dt
    scale = sigma * math.sqrt(dt)
    for start in range(0, paths, 4096):
        block = rng.standard_normal((min(4096, paths-start), steps), dtype=np.float64)
        block *= scale
        block += drift
        np.exp(block, out=block)
        result[start:start+len(block)] = block
    return result

def oracle(factors, barrier, discount=DISCOUNT, spot=SPOT, strike=STRIKE):
    """Walk dates across all live paths; separate control structure from C++ path/lane loops."""
    n, steps = factors.shape
    stock = np.full(n, spot, dtype=np.float64)
    hit = stock >= barrier
    lifetime = np.zeros(n, dtype="<u8")
    for date in range(steps):
        live = ~hit
        stock[live] *= factors[live, date]
        lifetime[live] += 1
        hit |= stock >= barrier
    payoff = discount * np.maximum(stock-strike, 0.)
    payoff[hit] = 0.
    return payoff, lifetime, hit.astype(np.uint8)

def vanilla_diagnostic(factors):
    payoff, _, _ = oracle(factors, math.inf)
    n = len(payoff)
    d1 = (math.log(SPOT/STRIKE) + (RATE-DIVIDEND+.5*SIGMA**2)*MATURITY)/(SIGMA*math.sqrt(MATURITY))
    d2 = d1-SIGMA*math.sqrt(MATURITY)
    cdf = lambda x: .5*(1+math.erf(x/math.sqrt(2)))
    analytic = SPOT*math.exp(-DIVIDEND*MATURITY)*cdf(d1)-STRIKE*DISCOUNT*cdf(d2)
    mean=float(payoff.mean())
    se=float(payoff.std(ddof=1)/math.sqrt(n))
    return dict(paths=n, estimate=mean, analytic=analytic, standard_error=se,
                z_score=(mean-analytic)/se, interpretation="Statistical diagnostic, not a pass/fail pricing oracle")
