from decimal import Decimal


class BalanceMixin(object):
    """Mixin for balance holding :mod:`pooldlib.postgresql.models` models.
    Provides :func:`model.balance_for_currency`
    """

    def balance_for_currency(self, currency, get_or_create=True, for_update=False):
        """Return a user's :class:`pooldlib.postgresql.models.Balance` for a given
        :class:`pooldlib.postgresql.models.Currency` or currency code (:class:`str`).

        :param currency: Currency of balance to return.
        :type currency: :class:`pooldlib.postgresql.models.Balance` or string.
        :param get_or_create: Should a balance be created for the user in the target currency if none is found?
        :type get_or_create: boolean, default `True`
        :param for_update: If `True` the `FOR UPDATE` directive will be used, locking the row for an `UPDATE` query.
        :type for_update: boolean, default `False`
        """
        from pooldlib.api import balance
        from pooldlib.postgresql import (db,
                                         Currency as CurrencyModel,
                                         Balance as BalanceModel)

        if isinstance(currency, basestring):
            currency = CurrencyModel.get(currency)
        balance = balance.get(for_update=for_update, user_id=self.id, currency_id=currency.id)

        # If we don't find a balance for the user, create if requested to
        if not balance and get_or_create:
            balance = BalanceModel()
            balance.enabled = True
            balance.amount = Decimal('0.0000')
            balance.currency = currency
            db.session.add(balance)
            self.balances.append(balance)
            db.session.flush()

        # Balance.get returns a list if for_update=False. A user should only
        # have a single balance for a given currency, so return the
        # CurrencyModel object instead of a list.
        if isinstance(balance, list):
            balance = balance[0]
        return balance
