"""A collection of Avro related utility functions. If we plan to support
other serialization frameworks in the future, we might have to do some
refactoring to extract common features to an upper layer.
"""


def float_to_long(value):
    return int(value * 1000000)


def long_to_float(value):
    return value / 1000000.0
