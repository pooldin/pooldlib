from decimal import Decimal


class BalanceMixin(object):

    def balance_for_currency(self, currency):
        from pooldlib.postgresql import db, Currency, Balance
        if isinstance(currency, basestring):
            currency = Currency.get(currency)
        balance = [b for b in self.balances if b.currency == currency]
        if not balance:
            balance = Balance()
            balance.enabled = True
            balance.amount = Decimal('0.0000')
            balance.currency = currency
            db.session.add(balance)
            self.balances.append(balance)
            db.session.flush()
        else:
            balance = balance[0]

        return balance
