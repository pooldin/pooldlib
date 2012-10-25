from pooldlib.postgresql import db, common
from pooldlib.postgresql.types import DateTimeTZ


class Community(common.ConfigurationModel, common.ActiveMixin, common.BalanceMixin):
    pass


class CommunityAssociation(db.Model, common.TrackIPMixin, common.TrackTimeMixin, common.EnabledMixin, common.FieldUpdateMixin):
    __tablename__ = 'community_association'

    user = db.relationship('User', backref='communities', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False,
                        primary_key=True)
    community = db.relationship('Community', backref='participants', lazy='select')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False,
                             primary_key=True)
    role = db.Column(db.Enum('organizer', 'participant', name='community_role_enum'))

    __table_args__ = (db.UniqueConstraint(user_id, community_id), {})


class CommunityGoalAssociation(db.Model, common.TrackIPMixin, common.TrackTimeMixin, common.EnabledMixin, common.FieldUpdateMixin):
    __tablename__ = 'community_goal_association'

    user = db.relationship('User', backref='goals', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False,
                        primary_key=True)
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False,
                             primary_key=True)
    community_goal = db.relationship('CommunityGoal', backref='participants', lazy='select')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=False,
                                  primary_key=True)
    role = db.Column(db.Enum('opted-in',
                             'opted-out',
                             'participating',
                             'nonparticipating',
                             name='participation_enum'))

    __table_args__ = (db.UniqueConstraint(user_id, community_id, community_goal_id), {})


class Invitee(common.UUIDMixin, common.EnabledMixin, common.Model):
    email = db.Column(db.String(255),
                      nullable=False,
                      index=True)
    accepted = db.Column(DateTimeTZ, nullable=True)
    community = db.relationship('Community', backref='invitees', lazy='select')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    user = db.relationship('User', backref='invitations', lazy='select')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False)

    __table_args__ = (db.UniqueConstraint(community_id, email), {})


class CommunityGoal(common.ConfigurationModel, common.ActiveMixin, common.MetadataMixin):
    __tablename__ = 'community_goal'

    community = db.relationship('Community', backref='goals', lazy='select')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    type = db.Column(db.Enum('petition', 'project', 'purchase', name='community_goal_type_enum'))
    purchase = db.relationship('Purchase',
                               backref='community_goal',
                               uselist=False,
                               lazy='select')
    purchase_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('purchase.id'),
                            nullable=True)


class CommunityGoalMeta(common.Model, common.EnabledMixin, common.KeyValueMixin):
    __tablename__ = 'community_goal_meta'

    community_goal = db.relationship('CommunityGoal', backref='metadata', lazy='select')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=False)


class CommunityGoalMetaKey(common.Model, common.EnabledMixin):
    __tablename__ = 'community_goal_meta_key'

    key = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
