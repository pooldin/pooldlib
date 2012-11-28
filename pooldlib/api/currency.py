"""
pooldlib.api.currency
===============================

.. currentmodule:: pooldlib.api.currency

"""

from pooldlib.postgresql import Currency as CurrencyModel


def get(code):
    c = CurrencyModel.query.filter_by(code=code).first()
    return c
