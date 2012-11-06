from pooldlib.postgresql import db, common


class Balance(common.Model, common.EnabledMixin):

    currency_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('currency.id'),
                            nullable=False)
    currency = db.relationship('Currency', backref='balances')
    amount = db.Column(db.DECIMAL(precision=24, scale=4),
                       nullable=False,
                       default=0)
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=True)
    user = db.relationship('User', backref='balances', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=True)
    campaign = db.relationship('Campaign', backref='balances', lazy='select')
    type = db.Column(db.Enum('user', 'campaign', name='balance_type_enum'))

    @classmethod
    def filter_by(cls, currency=None, query=None):
        from pooldlib.postgresql import Currency
        if hasattr(currency, 'id'):
            currency = currency.id

        if not query:
            query = cls.query

        if currency and isinstance(currency, basestring):
            query = query.join(Currency)
            return query.filter(Currency.code == currency)

        if currency:
            return query.filter(cls.currency_id == currency)

        return query

    @classmethod
    def first(cls, *args, **kw):
        return cls.filter_by(*args, **kw).first()

    @classmethod
    def filter_by_user(cls, user=None, currency=None):
        if hasattr(user, 'id'):
            user = user.id

        if not user:
            return

        query = cls.query.filter(cls.user_id == user)
        return super(Balance, cls).filter_by(currency=currency,
                                             query=query)

    @classmethod
    def filter_by_campaign(cls, campaign=None, currency=None):
        if hasattr(campaign, 'id'):
            campaign = campaign.id

        if not campaign:
            return

        query = cls.query.filter(cls.campaign_id == campaign)
        return super(Balance, cls).filter_by(currency=currency,
                                             query=query)
