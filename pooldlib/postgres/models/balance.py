from .. import db, common


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
                        nullable=False)
    user = db.relationship('User', backref='balances', lazy='dynamic')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    community = db.relationship('Community', backref='balances', lazy='dynamic')
    type = db.Column(db.Enum('user', 'community', name='balance_type_enum'))

    @classmethod
    def filter_by(cls, currency=None, query=None):
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
    def filter_by_community(cls, community=None, currency=None):
        if hasattr(community, 'id'):
            community = community.id

        if not community:
            return

        query = cls.query.filter(cls.community_id == community)
        return super(Balance, cls).filter_by(currency=currency,
                                             query=query)
