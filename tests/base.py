import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from pooldlib.postgresql import db, User, UserMeta, Community, CommunityGoal, CommunityGoalMeta, Currency, Balance

from tests import create_fixtures


class PooldLibBaseTest(unittest.TestCase):

    def create_user(self, username, name, email=None):
        u = User()
        u.name = name
        u.username = username
        # Passwords must contain at least one number, so we force it...
        u.password = username + '1'
        u.verified = True
        u.enabled = True
        self.commit_model(u)

        if email is not None:
            um = UserMeta()
            um.key = 'email'
            um.value = email
            um.user = u
            self.commit_model(um)

        return u

    def create_community(self, name, description, start=None, end=None):
        if start is None:
            start = datetime.utcnow()
        if end is None:
            end = start + timedelta(days=30)

        c = Community()
        c.name = name
        c.description = description
        c.enabled = True
        c.start = start
        c.end = end

        self.commit_model(c)
        return c

    def create_community_goal(self, community_id, type, start=None, end=None):
        if start is None:
            start = datetime.utcnow()
        if end is None:
            end = start + timedelta(days=7)
        c = Community.get(community_id)
        cg = CommunityGoal()
        cg.communtiy = c
        cg.enabled = True
        cg.start = start
        cg.end = end
        cg.type = type
        self.commit_model(cg)
        return cg

    def create_community_goal_meta(self, community_goal_id, **kwargs):
        cg = CommunityGoal.get(community_goal_id)
        for (k, v) in kwargs.items():
            cgm = CommunityGoalMeta()
            cgm.key = k
            cgm.value = v
            cgm.community_goal = cg
            self.commit_model(cgm)
        return cg

    def create_balance(self, user=None, community=None, currency_code=None, amount=Decimal('50.0000')):
        if not currency_code:
            currency_code = 'USD'

        currency = Currency.get(currency_code)
        b = Balance()
        b.enabled = True
        b.amount = amount
        b.currency = currency

        if user is not None:
            b.user = user
            b.type = 'user'
        elif community is not None:
            b.community = user
            b.type = 'community'

        self.commit_model(b)
        return b

    def commit_model(self, model):
        db.session.add(model)
        db.session.commit()


class PooldLibPostgresBaseTest(PooldLibBaseTest):

    def setUp(self):
        # Create us some useful fixtures
        create_fixtures()

    def tearDown(self):
        # Close the session so we don't lock tables while trunc***** them.
        db.shutdown_session()
