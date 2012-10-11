from .. import db, common
from ..types import DateTimeTZ


class Community(common.ConfigurationModel, common.ActiveMixin):
    pass


class CommunityAssociation(common.Model, common.EnabledMixin):
    __tablename__ = 'community_association'

    user = db.relationship('User', backref='communities', lazy='dynamic')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False)
    community = db.relationship('Community', backref='participants', lazy='dynamic')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    role = db.Column(db.Enum('organizer', 'participant', name='community_role_enum'))


class Invitee(common.UUIDMixin, common.EnabledMixin, common.Model):
    email = db.Column(db.String(255),
                      nullable=False,
                      index=True)
    accepted = db.Column(DateTimeTZ, nullable=True)
    community = db.relationship('Community', backref='invitees', lazy='dynamic')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    user = db.relationship('User', backref='invitations', lazy='dynamic')
    user_id = db.Column(db.BigInteger(unsigned=True),
                        db.ForeignKey('user.id'),
                        nullable=False)

    db.UniqueConstraint('community_goal_id', 'email')


class CommunityGoal(common.ConfigurationModel, common.ActiveMixin):
    __tablename__ = 'community_goal'

    community = db.relationship('Community', backref='goals', lazy='dynamic')
    community_id = db.Column(db.BigInteger(unsigned=True),
                             db.ForeignKey('community.id'),
                             nullable=False)
    type = db.Column(db.Enum('amazon.com-purchase', 'amazon.com-giftcard', name='community_goal_type_enum'))
    purchase = db.relationship('Purchase',
                               backref='community_goal',
                               uselist=False,
                               lazy='dynamic')
    purchase_id = db.Column(db.BigInteger(unsigned=True),
                            db.ForeignKey('purchase.id'),
                            nullable=True)


class CommunityGoalMeta(common.Model, common.EnabledMixin, common.KeyValueMixin):
    __tablename__ = 'community_goal_meta'

    community_goal = db.relationship('CommunityGoal', backref='metadata', lazy='dynamic')
    community_goal_id = db.Column(db.BigInteger(unsigned=True),
                                  db.ForeignKey('community_goal.id'),
                                  nullable=False)
    key = db.Column(db.String(255),
                    db.ForeignKey('community_goal_meta_key.key'),
                    nullable=False)


class CommunityGoalMetaKey(common.Model, common.EnabledMixin):
    __tablename__ = 'community_goal_meta_key'

    key = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
