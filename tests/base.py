import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from pooldlib.postgresql import (db,
                                 User,
                                 UserMeta,
                                 Balance,
                                 Currency,
                                 Campaign,
                                 CampaignMeta,
                                 CampaignAssociation,
                                 CampaignGoalAssociation,
                                 CampaignGoal,
                                 CampaignGoalMeta)


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

    def create_user_meta(self, user, **kwargs):
        if isinstance(user, (int, long)):
            user = User.query.get(user)
        for (k, v) in kwargs.items():
            um = UserMeta()
            um.key = k
            um.value = v
            um.user_id = user.id
            self.commit_model(um)

    def create_campaign(self, name, description, start=None, end=None):
        if start is None:
            start = datetime.utcnow()
        if end is None:
            end = start + timedelta(days=30)

        c = Campaign()
        c.name = name
        c.description = description
        c.enabled = True
        c.start = start
        c.end = end

        self.commit_model(c)
        return c

    def create_campaign_meta(self, campaign, **kwargs):
        if isinstance(campaign, (int, long)):
            campaign = Campaign.query.get(campaign)
        for (k, v) in kwargs.items():
            cm = CampaignMeta()
            cm.key = k
            cm.value = v
            cm.campaign_id = campaign.id
            self.commit_model(cm)

    def create_campaign_association(self, campaign, user, role, pledge=None):
        ca = CampaignAssociation()
        ca.user_id = user.id
        ca.campaign_id = campaign.id
        ca.role = role
        if pledge is not None:
            ca.pledge = pledge
        self.commit_model(ca)
        return ca

    def create_campaign_goal_association(self, campaign, goal, user, participation, pledge=None):
        cga = CampaignGoalAssociation()
        cga.user_id = user.id
        cga.campaign_id = campaign.id
        cga.campaign_goal_id = goal.id
        cga.participation = participation
        if pledge is not None:
            cga.pledge = pledge
        self.commit_model(cga)
        return cga

    def create_campaign_goal(self, campaign, name, description, type=None, start=None, end=None):
        if type is None:
            type = 'project'
        if start is None:
            start = datetime.utcnow()
        if end is None:
            end = start + timedelta(days=7)
        if not isinstance(campaign, Campaign):
            campaign = Campaign.query.get(campaign)
        cg = CampaignGoal()
        #campaign.goals.append(cg)
        cg.campaign_id = campaign.id
        cg.enabled = True
        cg.name = name
        cg.description = description
        cg.start = start
        cg.end = end
        cg.type = type
        self.commit_model(cg)

        return cg

    def create_campaign_goal_meta(self, campaign_goal_id, **kwargs):
        cg = CampaignGoal.query.get(campaign_goal_id)
        for (k, v) in kwargs.items():
            cgm = CampaignGoalMeta()
            cgm.key = k
            cgm.value = v
            cgm.campaign_goal_id = cg.id
            self.commit_model(cgm)
        return cg

    def create_balance(self, user=None, campaign=None, currency_code=None, amount=None):
        amount = amount if amount is not None else Decimal('50.0000')
        if not currency_code:
            currency_code = 'USD'

        currency = Currency.get(currency_code)
        b = Balance()
        b.enabled = True
        b.amount = amount
        b.currency = currency

        if user is not None:
            b.user_id = user.id
            b.type = 'user'
        elif campaign is not None:
            b.campaign_id = campaign.id
            b.type = 'campaign'

        self.commit_model(b)
        return b

    def commit_model(self, model):
        db.session.add(model)
        db.session.commit()


class PooldLibPostgresBaseTest(PooldLibBaseTest):

    def tearDown(self):
        # Close the session so we don't lock tables while trunc***** them.
        db.shutdown_session()
