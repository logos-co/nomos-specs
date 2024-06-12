POWERS_OF_2 = {2**i for i in range(1, 32)}


def is_power_of_two(n) -> bool:
    return n in POWERS_OF_2
