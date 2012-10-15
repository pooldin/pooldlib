from sqlalchemy.orm.attributes import manager_of_class

from pooldlib.postgresql import Balance as BalanceModel


BALANCE_TABLE = manager_of_class(BalanceModel).mapper.mapped_table


def get(for_update=False, **kwargs):
    """Retrieve :class:`pooldlib.postgresql.models.Balance` objects from the
    database. If `for_update` is `True` it is assumed that the caller wants a
    single balance object retrieved.

    TODO :: It would be much more efficient to retrieve all
            `pooldlib.postgresql.models.Balance` objects to be updated at once.

    :param for_update: If `True` the `FOR UPDATE` directive will be used, locking the row for an `UPDATE` query.
    :type for_update: boolean, default `False`
    :param kwargs: Database fields to use in conjunction with `query.filter_by`. IMPORTANT: These are `field`
                   names, so relational attributes must use their associated field, e.g. `model.currency_id`,
                   NOT `model.currency`
    """
    q = BalanceModel.query
    fields = [(f, v) for (f, v) in kwargs.items() if f in BALANCE_TABLE.columns]
    filters = dict()
    for (f, v) in fields:
        filters[f] = v
    q = q.filter_by(**filters)
    if for_update:
        q = q.with_lockmode('update')
        balance = q.first()
    else:
        balance = q.all()
    return balance
