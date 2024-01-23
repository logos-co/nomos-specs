import numpy


def poisson_interval_sec(rate_per_min: int) -> float:
    # If events occur in a Poisson distribution with rate_per_min,
    # the interval between events follows the exponential distribution
    # with the rate_per_min (i.e. with the scale 1/rate_per_min).
    interval_min = numpy.random.exponential(scale=1 / rate_per_min, size=1)[0]
    return interval_min * 60


def poisson_mean_interval_sec(rate_per_min: int) -> float:
    return 1 / rate_per_min * 60
