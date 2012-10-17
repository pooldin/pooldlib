"""
pooldlib.generators
===============================

.. currentmodule:: pooldlib.generators

"""
import random


ALPHA = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
NUMERIC = '1234567890'


def alphanumeric_string(alpha_count=10, number_count=3):
    """Returns a randomly generated alphanumeric string.

    :param alpha_count: The number of alpha characters to be included
                        in the returned string.
    :type alpha_count: integer
    :param number_count: The number of numeric characters to be included
                         in the returned string.
    :type number_count: integer

    :returns: string
    """
    password = list()
    password.extend(random.sample(ALPHA, alpha_count))
    password.extend(random.sample(NUMERIC, number_count))
    return ''.join(password)
