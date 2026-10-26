"""Verification metrics only. Observations must be independently quality controlled."""
from __future__ import annotations

def brier_score(probabilities, observations):
    """Mean squared probability error for event y∈{0,1}."""
    pairs = list(zip(probabilities, observations))
    if not pairs:
        raise ValueError('No matched forecast–observation pairs')
    if any(not (0 <= float(p) <= 1) or y not in (0, 1) for p,y in pairs):
        raise ValueError('Invalid probability or binary observation')
    return sum((float(p)-int(y))**2 for p,y in pairs)/len(pairs)

def bias(forecasts, observations):
    pairs = list(zip(forecasts, observations))
    if not pairs:
        raise ValueError('No pairs')
    return sum(float(f)-float(o) for f,o in pairs)/len(pairs)

def mae(forecasts, observations):
    pairs = list(zip(forecasts, observations))
    if not pairs:
        raise ValueError('No pairs')
    return sum(abs(float(f)-float(o)) for f,o in pairs)/len(pairs)
