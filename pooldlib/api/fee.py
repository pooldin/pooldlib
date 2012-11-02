"""
pooldlib.api.fee
===============================

.. currentmodule:: pooldlib.api.fee

"""
from pooldlib.postgresql.models import Fee as FeeModel


def get(fee_name, fee_names=None):
    """Retrieve :class:`pooldlib.postgresql.models.Fee` objects based on ``fee.name``.
    You must supplie *either* ``fee_name`` (a single fee name) or ``fee_names`` (a list
    of fee names).

    :param fee_name: The name corresponding to the desired Fee.
    :type fee_name: string
    :param fee_name: A list of names corresponding to the desired Fees.
    :type fee_name: list of strings

    :returns: list of :class:`pooldlib.postgresql.models.Fee`
    """
    if fee_names is not None:
        names = fee_names
    elif fee_name is not None:
        names = [fee_name]
    else:
        msg = 'Either fee_name or fee_names must be not None.'
        raise TypeError(msg)

    fees = FeeModel.query.filter_by(enabled=True)\
                         .filter(FeeModel.name.in_(names))\
                         .all()
    return fees
