from pooldlib.postgresql import db, common
from pooldlib.postgresql.types import DateTimeTZ


class Campaign(common.ConfigurationModel,
               common.ActiveMixin,
               common.BalanceMixin,
               common.MetadataMixin):
    pass


class CampaignMeta(common.Model, common.EnabledMixin, common.KeyValueMixin):
    __tablename__ = 'campaign_meta'

    campaign = db.relationship('Campaign', backref='metadata', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False)


class CampaignAssociation(db.Model, common.TrackIPMixin, common.TrackTimeMixin, common.EnabledMixin, common.FieldUpdateMixin):
    __tablename__ = 'campaign_association'

    user = db.relationship('User', backref='campaigns', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False,
                        primary_key=True)
    campaign = db.relationship('Campaign', backref='participants', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False,
                            primary_key=True)
    role = db.Column(db.Enum('organizer', 'participant', name='campaign_role_enum'))
    pledge = db.Column(db.DECIMAL(precision=24, scale=4),
                       nullable=True)

    __table_args__ = (db.UniqueConstraint(user_id, campaign_id), {})


class CampaignGoalAssociation(db.Model, common.TrackIPMixin, common.TrackTimeMixin, common.EnabledMixin, common.FieldUpdateMixin):
    __tablename__ = 'campaign_goal_association'

    user = db.relationship('User', backref='goals', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False,
                        primary_key=True)
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False,
                            primary_key=True)
    campaign_goal = db.relationship('CampaignGoal', backref='participants', lazy='select')
    campaign_goal_id = db.Column(db.BigInteger(unsigned=True),
                                 db.ForeignKey('campaign_goal.id'),
                                 nullable=False,
                                 primary_key=True)
    participation = db.Column(db.Enum('opted-in',
                                      'opted-out',
                                      'participating',
                                      'nonparticipating',
                                      name='participation_enum'))
    pledge = db.Column(db.DECIMAL(precision=24, scale=4),
                       nullable=True)

    __table_args__ = (db.UniqueConstraint(user_id, campaign_id, campaign_goal_id), {})


class Invitee(common.UUIDMixin, common.EnabledMixin, common.Model):
    email = db.Column(db.String(255),
                      nullable=False,
                      index=True)
    accepted = db.Column(DateTimeTZ, nullable=True)
    campaign = db.relationship('Campaign', backref='invitees', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False)
    user = db.relationship('User', backref='invitations', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=True)

    __table_args__ = (db.UniqueConstraint(campaign_id, email), {})


class CampaignGoal(common.ConfigurationModel, common.ActiveMixin, common.MetadataMixin):
    __tablename__ = 'campaign_goal'

    predecessor_id = db.Column(db.BigInteger(unsigned=True),
                               db.ForeignKey('campaign_goal.id'),
                               nullable=True)
    predecessor = db.relationship('CampaignGoal',
                                  uselist=False,
                                  backref=db.backref('descendant', remote_side="CampaignGoal.id"))

    campaign = db.relationship('Campaign', backref='goals', lazy='select')
    campaign_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('campaign.id'),
                            nullable=False)

    type = db.Column(db.Enum('petition', 'project', 'purchase', name='campaign_goal_type_enum'))

    purchase = db.relationship('Purchase',
                               backref='campaign_goal',
                               uselist=False,
                               lazy='select')
    purchase_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('purchase.id'),
                            nullable=True)


class CampaignGoalMeta(common.Model, common.EnabledMixin, common.KeyValueMixin):
    __tablename__ = 'campaign_goal_meta'

    campaign_goal = db.relationship('CampaignGoal', backref='metadata', lazy='select')
    campaign_goal_id = db.Column(db.BigInteger(unsigned=True),
                                 db.ForeignKey('campaign_goal.id'),
                                 nullable=False)
