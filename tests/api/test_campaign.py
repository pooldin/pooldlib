from datetime import datetime, timedelta
from decimal import Decimal
import pytz
from uuid import uuid4 as uuid
from nose.tools import raises, assert_equal, assert_true, assert_false

from pooldlib.exceptions import (InvalidUserRoleError,
                                 InvalidGoalParticipationNameError,
                                 DuplicateCampaignUserAssociationError,
                                 DuplicateCampaignGoalUserAssociationError,
                                 PreviousUserContributionError)
from pooldlib.postgresql import db
from pooldlib.postgresql import (Campaign as CampaignModel,
                                 Invitee as InviteeModel,
                                 CampaignMeta as CampaignMetaModel,
                                 CampaignGoal as CampaignGoalModel,
                                 CampaignGoalAssociation as CampaignGoalAssociationModel,
                                 CampaignAssociation as CampaignAssociationModel)

from pooldlib.api import campaign

from tests import tag
from tests.base import PooldLibPostgresBaseTest


class TestGetCampaign(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCampaign, self).setUp()
        self.com_name = 'TestGetCampaign'
        self.com_description = 'To Test Get Campaign'
        self.campaign = self.create_campaign(self.com_name, self.com_description)
        self.com_id = self.campaign.id

    @tag('campaign')
    def test_simple_get(self):
        com = campaign.get(self.com_id, filter_inactive=True)
        assert_equal(self.com_name, com.name)
        assert_equal(self.com_description, com.description)

    @tag('campaign')
    def test_get_inactive_not_returned(self):
        now = datetime.utcnow()
        com = self.create_campaign('Test Incactive Campaign Not Returned.',
                                   'Test Incactive Campaign Not Returned.',
                                   start=now + timedelta(days=1),
                                   end=now + timedelta(days=2))
        ret = campaign.get(com.id, filter_inactive=True)
        assert_true(ret is None)

    @tag('campaign')
    def test_get_inactive_returned(self):
        now = datetime.utcnow()
        com = self.create_campaign('Test Incactive Campaign Returned.',
                                   'Test Incactive Campaign Returned.',
                                   start=now + timedelta(days=1),
                                   end=now + timedelta(days=2))
        ret = campaign.get(com.id, filter_inactive=False)
        assert_equal(com.name, ret.name)
        assert_equal(com.description, ret.description)

    @tag('campaign')
    def test_get_disabled_not_returned(self):
        self.campaign.enabled = False
        db.session.commit()
        ret = campaign.get(self.com_id)
        assert_true(ret is None)


class TestGetCampaigns(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCampaigns, self).setUp()

        self.com_one_name = 'Test Get Campaigns One'
        self.com_one_description = 'To Test Get Campaigns: One'
        self.com_one_start = datetime.utcnow() - timedelta(days=3)
        self.com_one_end = self.com_one_start + timedelta(days=2)
        self.campaign_one = self.create_campaign(self.com_one_name,
                                                 self.com_one_description,
                                                 self.com_one_start,
                                                 self.com_one_end)
        self.com_one_id = self.campaign_one.id

        self.com_two_name = 'Test Get Campaigns Two'
        self.com_two_description = 'To Test Get Campaigns: Two'
        self.com_two_start = datetime.utcnow() - timedelta(days=1)
        self.com_two_end = self.com_two_start + timedelta(days=2)
        self.campaign_two = self.create_campaign(self.com_two_name,
                                                 self.com_two_description,
                                                 self.com_two_start,
                                                 self.com_two_end)
        self.com_two_id = self.campaign_two.id

        self.com_three_name = 'Test Get Campaigns Three'
        self.com_three_description = 'To Test Get Campaigns: Three'
        self.com_three_start = datetime.utcnow() + timedelta(days=2)
        self.com_three_end = self.com_three_start + timedelta(days=2)
        self.campaign_three = self.create_campaign(self.com_three_name,
                                                   self.com_three_description,
                                                   self.com_three_start,
                                                   self.com_three_end)
        self.com_three_id = self.campaign_three.id

    @tag('campaign')
    def test_get_all_campaigns(self):
        comms = campaign.campaigns(None, filter_inactive=False)
        # At this point we don't know the current state of the db, so there
        # should be a minimum of 3 campaigns existing.
        assert_true(3 <= len(comms))

    @tag('campaign')
    def test_get_all_campaigns_exclude_inactive(self):
        comms = campaign.campaigns(None, filter_inactive=True)
        # At this point we don't know the current state of the db, so there
        # should be a minimum of 1 active campaign existing.
        assert_true(1 <= len(comms))

    @tag('campaign')
    def test_get_all_campaigns_in_list(self):
        comms = campaign.campaigns([self.com_one_id, self.com_two_id, self.com_three_id],
                                   filter_inactive=False)
        assert_equal(3, len(comms))

    @tag('campaign')
    def test_get_campaigns_exclude_inactive(self):
        comms = campaign.campaigns([self.com_one_id, self.com_two_id, self.com_three_id],
                                   filter_inactive=True)
        assert_equal(1, len(comms))

    @tag('campaign')
    def test_get_campaigns_exclude_all_inactive(self):
        comms = campaign.campaigns([self.com_one_id, self.com_three_id])
        assert_equal(0, len(comms))


class TestCreateCampaign(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCreateCampaign, self).setUp()
        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    @tag('campaign')
    def test_simple_create(self):
        com_name = uuid().hex
        com = campaign.create(self.user,
                              com_name,
                              'It Tests Simple Campaign Creates.')
        assert_true(isinstance(com, CampaignModel))
        q_com = CampaignModel.query.filter_by(name=com_name).all()
        assert_equal(1, len(q_com))
        q_com = q_com[0]
        assert_equal('It Tests Simple Campaign Creates.', q_com.description)

    @tag('campaign')
    def test_create_with_metadata(self):
        key_one = 'property_one'
        value_one = 'property_value_one'
        key_two = 'property_two'
        value_two = 'property_value_two'

        kwargs = {key_one: value_one,
                  key_two: value_two}
        com_name = uuid().hex
        com = campaign.create(self.user,
                              com_name,
                              'It Tests Simple Campaign Creates.',
                              **kwargs)
        assert_true(isinstance(com, CampaignModel))
        q_com = CampaignModel.query.filter_by(name=com_name).all()
        assert_equal(1, len(q_com))
        q_com = q_com[0]
        assert_equal('It Tests Simple Campaign Creates.', q_com.description)

        q_commeta = CampaignMetaModel.query.filter_by(campaign_id=com.id).all()
        assert_equal(2, len(q_commeta))
        q_key_one = CampaignMetaModel.query.filter_by(campaign_id=com.id)\
                                           .filter_by(key=key_one)\
                                           .first()
        assert_equal(value_one, q_key_one.value)
        # Check the property on the CampaignModel
        assert_equal(value_one, getattr(com, key_one))
        q_key_two = CampaignMetaModel.query.filter_by(campaign_id=com.id)\
                                           .filter_by(key=key_two)\
                                           .first()
        assert_equal(value_two, q_key_two.value)
        # Check the property on the CampaignModel
        assert_equal(value_two, getattr(com, key_two))

    @tag('campaign')
    def test_organizer_association(self):
        com_name = uuid().hex
        com = campaign.create(self.user,
                              com_name,
                              'It Tests Organizer Association Creates.')
        assert_true(isinstance(com, CampaignModel))
        ass = CampaignAssociationModel.query.filter(CampaignAssociationModel.user_id == self.user.id)\
                                            .filter(CampaignAssociationModel.campaign_id == com.id)\
                                            .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)


class TestCampaignInvite(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignInvite, self).setUp()
        self.com_name = 'Test Campaign Invite'
        self.com_description = 'To Test Campaign Invite'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    @tag('campaign')
    def test_invite_non_user(self):
        email = 'johnny-left-out@example.com'
        campaign.add_invite(self.campaign, email)
        invite = InviteeModel.query.filter_by(campaign_id=self.campaign.id)\
                                   .filter_by(email=email).all()

        assert_equal(1, len(invite))
        invite = invite[0]
        assert_equal(email, invite.email)
        assert_equal(self.campaign.id, invite.campaign_id)
        assert_true(invite.user_id is None)

    @tag('campaign')
    def test_invite_non_user_duplicate(self):
        email = 'johnny-left-out@example.com'
        campaign.add_invite(self.campaign, email)
        campaign.add_invite(self.campaign, email)
        invite = InviteeModel.query.filter_by(campaign_id=self.campaign.id)\
                                   .filter_by(email=email).all()

        assert_equal(1, len(invite))
        invite = invite[0]
        assert_equal(email, invite.email)
        assert_equal(self.campaign.id, invite.campaign_id)
        assert_true(invite.user_id is None)

    @tag('campaign')
    def test_invite_non_users(self):
        emails = ['johnny-left-out-again@example.com',
                  'johnny-left-out-and-again@example.com',
                  'johnny-left-out-and-and-again@example.com']
        campaign.add_invites(self.campaign, emails)
        for email in emails:
            invite = InviteeModel.query.filter_by(campaign_id=self.campaign.id)\
                                       .filter_by(email=email).all()
            assert_equal(1, len(invite))
            invite = invite[0]
            assert_true(invite is not None)
            assert_equal(email, invite.email)
            assert_equal(self.campaign.id, invite.campaign_id)
            assert_true(invite.user_id is None)


class TestCampaignAssociateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignAssociateUser, self).setUp()
        self.com_name = 'Test Association User With Campaigns'
        self.com_description = 'To Test Association User With Campaigns'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    @tag('campaign')
    def test_associate_organizer(self):
        campaign.associate_user(self.campaign, self.user, 'organizer', 'participating')

        ass = CampaignAssociationModel.query.filter(CampaignAssociationModel.user_id == self.user.id)\
                                            .filter(CampaignAssociationModel.campaign_id == self.campaign.id)\
                                            .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    @tag('campaign')
    def test_associate_participant(self):
        campaign.associate_user(self.campaign, self.user, 'participant', 'participating')

        ass = CampaignAssociationModel.query.filter(CampaignAssociationModel.user_id == self.user.id)\
                                            .filter(CampaignAssociationModel.campaign_id == self.campaign.id)\
                                            .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('participant', ass.role)

    @tag('campaign')
    @raises(InvalidUserRoleError)
    def test_associate_unknown_role(self):
        campaign.associate_user(self.campaign, self.user, 'MinisterOfSillyWalks', 'walker')

    @tag('campaign')
    @raises(DuplicateCampaignUserAssociationError)
    def test_create_duplicate_association(self):
        campaign.associate_user(self.campaign, self.user, 'organizer', 'participating')
        campaign.associate_user(self.campaign, self.user, 'organizer', 'participating')


class TestDisableCampaign(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDisableCampaign, self).setUp()
        self.com_name = 'Test Association User With Campaigns'
        self.com_description = 'To Test Association User With Campaigns'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

    @tag('campaign')
    def test_simple_disable(self):
        campaign.disable(self.campaign)
        ret = CampaignModel.query.get(self.com_id)
        assert_false(ret.enabled)

    @tag('campaign')
    def test_simple_disable_with_id(self):
        campaign.disable(self.campaign)
        ret = CampaignModel.query.get(self.com_id)
        assert_false(ret.enabled)


class TestGetAssociations(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetAssociations, self).setUp()
        self.com_name = 'Test Association User With Campaigns'
        self.com_description = 'To Test Association User With Campaigns'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username_one = uuid().hex
        self.name_one = '%s %s' % (self.username_one[:16], self.username_one[16:])
        self.email_one = '%s@example.com' % self.username_one
        self.user_one = self.create_user(self.username_one, self.name_one, self.email_one)
        self.create_campaign_association(self.campaign, self.user_one, 'participant')

        self.username_two = uuid().hex
        self.name_two = '%s %s' % (self.username_two[:16], self.username_two[16:])
        self.email_two = '%s@example.com' % self.username_two
        self.user_two = self.create_user(self.username_two, self.name_two, self.email_two)
        self.create_campaign_association(self.campaign, self.user_two, 'participant')

        self.username_three = uuid().hex
        self.name_three = '%s %s' % (self.username_three[:16], self.username_three[16:])
        self.email_three = '%s@example.com' % self.username_three
        self.user_three = self.create_user(self.username_three, self.name_three, self.email_three)
        self.create_campaign_association(self.campaign, self.user_three, 'participant')

        self.user_ids = (self.user_one.id, self.user_two.id, self.user_three.id)

    @tag('campaign')
    def test_simple_get(self):
        asses = campaign.get_associations(self.campaign)
        assert_equal(3, len(asses))
        for ass in asses:
            assert_true(ass.user_id in self.user_ids)

    @tag('campaign')
    def test_get_single_association(self):
        ass = campaign.get_associations(self.campaign, user=self.user_one)
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal(ass.user_id, self.user_one.id)
        assert_equal(ass.campaign_id, self.campaign.id)


class TestCampaignUpdateUserRole(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignUpdateUserRole, self).setUp()
        self.com_name = 'Test Campaign Association User Role'
        self.com_description = 'To Test Campaign Association User Role'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.create_campaign_association(self.campaign, self.user, 'organizer')

    @tag('campaign')
    def test_update_new_role(self):
        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_equal('organizer', ass.role)
        campaign.update_user_association(self.campaign, self.user, role='participant')

        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_equal('participant', ass.role)


class TestCampaignUpdateUserPledge(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignUpdateUserPledge, self).setUp()
        self.com_name = 'Test Update Campaign Association Pledge'
        self.com_description = 'To Test Update Campaign Association Pledge'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.create_campaign_association(self.campaign, self.user, 'organizer')

    @tag('campaign')
    def test_update_new_pledge(self):
        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_true(ass.pledge is None)
        pledge = Decimal('100.00')
        campaign.update_user_association(self.campaign, self.user, pledge=pledge)

        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_equal(pledge, ass.pledge)


class TestCampaignUpdateUserPledgeWithGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignUpdateUserPledgeWithGoals, self).setUp()
        self.com_name = 'Test Update Campaign Association Pledge With Goals'
        self.com_description = 'To Test Update Campaign Association Pledge With Goals'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.goal_one = self.create_campaign_goal(self.com_id,
                                                  'Goal One',
                                                  'Its Goal One',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))
        self.goal_two = self.create_campaign_goal(self.com_id,
                                                  'Goal Two',
                                                  'Its Goal Two',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.create_campaign_association(self.campaign, self.user, 'organizer')
        self.create_campaign_goal_association(self.campaign, self.goal_one, self.user, 'participating')
        self.create_campaign_goal_association(self.campaign, self.goal_two, self.user, 'participating')

    @tag('campaign')
    def test_update_new_pledge(self):
        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        goal_asses = CampaignGoalAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                                  user_id=self.user.id).all()

        assert_true(ass is not None)
        assert_true(ass.pledge is None)
        for goal_ass in goal_asses:
            assert_true(goal_ass.pledge is None)
        pledge = Decimal('100.00')
        campaign.update_user_association(self.campaign, self.user, pledge=pledge)

        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        goal_asses = CampaignGoalAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                                  user_id=self.user.id).all()

        assert_true(ass is not None)
        assert_equal(pledge, ass.pledge)
        for goal_ass in goal_asses:
            assert_equal(Decimal('50.00'), goal_ass.pledge)


class TestCampaignUpdateUserPledgeWithGoalsWithPreviousPledge(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignUpdateUserPledgeWithGoalsWithPreviousPledge, self).setUp()
        self.com_name = 'Test Update Campaign Association Pledge With Goals'
        self.com_description = 'To Test Update Campaign Association Pledge With Goals'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.goal_one = self.create_campaign_goal(self.com_id,
                                                  'Goal One',
                                                  'Its Goal One',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))
        self.goal_two = self.create_campaign_goal(self.com_id,
                                                  'Goal Two',
                                                  'Its Goal Two',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.create_campaign_association(self.campaign, self.user, 'organizer', pledge=Decimal('100.00'))
        self.create_campaign_goal_association(self.campaign, self.goal_one, self.user, 'participating', pledge=Decimal('50.00'))
        self.create_campaign_goal_association(self.campaign, self.goal_two, self.user, 'participating', pledge=Decimal('50.00'))

    @tag('campaign')
    @raises(PreviousUserContributionError)
    def test_update_pledge(self):
        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        goal_asses = CampaignGoalAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                                  user_id=self.user.id).all()

        assert_true(ass is not None)
        assert_equal(Decimal('100.00'), ass.pledge)
        for goal_ass in goal_asses:
            assert_equal(Decimal('50.00'), goal_ass.pledge)
        pledge = Decimal('100.00')
        campaign.update_user_association(self.campaign, self.user, pledge=pledge)


class TestCampaignDisassociateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignDisassociateUser, self).setUp()
        self.com_name = 'Test Disassociation User From Campaigns'
        self.com_description = 'To Test Disassociation User From Campaigns'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)
        self.create_campaign_association(self.campaign, self.user, 'organizer')

    @tag('campaign')
    def test_remove_user_association(self):
        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is not None)

        campaign.disassociate_user(self.campaign, self.user)

        ass = CampaignAssociationModel.query.filter_by(campaign_id=self.com_id,
                                                       user_id=self.user.id).first()
        assert_true(ass is None)


class TestUpdateCampaign(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateCampaign, self).setUp()
        self.com_name = 'Test Update Community'
        self.com_description = 'To Test Update Community'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.meta_key_one = 'property_one'
        self.meta_key_value_one = 'property one value'
        self.meta_key_two = 'property_two'
        self.meta_key_value_two = 'property two value'
        kwargs = {self.meta_key_one: self.meta_key_value_one,
                  self.meta_key_two: self.meta_key_value_two}
        self.create_campaign_meta(self.campaign, **kwargs)
        self.com_id = self.campaign.id

    @tag('campaign')
    def test_update_meta(self):
        q_key_one = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_one)\
                                           .first()
        assert_equal(self.meta_key_value_one, q_key_one.value)
        q_key_two = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_two)\
                                           .first()
        assert_equal(self.meta_key_value_two, q_key_two.value)

        update_value_one = self.meta_key_value_one + ' updated'
        update_value_two = self.meta_key_value_two + ' updated'
        kwargs = {self.meta_key_one: update_value_one,
                  self.meta_key_two: update_value_two}

        campaign.update(self.campaign, **kwargs)

        q_key_one = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_one)\
                                           .first()
        assert_equal(update_value_one, q_key_one.value)
        # Check the property on the CampaignModel
        assert_equal(update_value_one, getattr(self.campaign, self.meta_key_one))
        q_key_two = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_two)\
                                           .first()
        assert_equal(update_value_two, q_key_two.value)
        # Check the property on the CampaignModel
        assert_equal(update_value_two, getattr(self.campaign, self.meta_key_two))

    @tag('campaign')
    def test_remove_meta(self):
        q_key_one = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_one)\
                                           .first()
        assert_equal(self.meta_key_value_one, q_key_one.value)
        q_key_two = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                           .filter_by(key=self.meta_key_two)\
                                           .first()
        assert_equal(self.meta_key_value_two, q_key_two.value)

        kwargs = {self.meta_key_one: None,
                  self.meta_key_two: None}

        campaign.update(self.campaign, **kwargs)

        q_key_one_del = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                               .filter_by(key=self.meta_key_one)\
                                               .first()
        assert_true(q_key_one_del is None)
        q_key_two_del = CampaignMetaModel.query.filter_by(campaign_id=self.campaign.id)\
                                               .filter_by(key=self.meta_key_two)\
                                               .first()
        assert_true(q_key_two_del is None)


class TestGetCampaignTransfers(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCampaignTransfers, self).setUp()


class TestGetCampaignGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCampaignGoal, self).setUp()
        self.com_name = 'Test Get Campaign Goal'
        self.com_description = 'To Test Get Campaign Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.goal_one = self.create_campaign_goal(self.campaign.id,
                                                  'Goal One',
                                                  'Its Goal One',
                                                  'project',
                                                  start=now - timedelta(days=3),
                                                  end=now - timedelta(days=2))
        self.goal_two = self.create_campaign_goal(self.campaign.id,
                                                  'Goal Two',
                                                  'Its Goal Two',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))
        self.goal_three = self.create_campaign_goal(self.campaign.id,
                                                    'Goal Three',
                                                    'Its Goal Three',
                                                    'project',
                                                    start=now + timedelta(days=1),
                                                    end=now + timedelta(days=2))

    @tag('campaign')
    def test_simple_get(self):
        goal = campaign.goal(self.goal_one.id, filter_inactive=False)
        assert_equal(self.goal_one.id, goal.id)

        goal = campaign.goal(self.goal_two.id, filter_inactive=False)
        assert_equal(self.goal_two.id, goal.id)

        goal = campaign.goal(self.goal_three.id, filter_inactive=False)
        assert_equal(self.goal_three.id, goal.id)

    @tag('campaign')
    def test_get_filter_inactive(self):
        goal = campaign.goal(self.goal_one.id, filter_inactive=True)
        assert_true(goal is None)

        goal = campaign.goal(self.goal_two.id, filter_inactive=True)
        assert_equal(self.goal_two.id, goal.id)

        goal = campaign.goal(self.goal_three.id, filter_inactive=True)
        assert_true(goal is None)


class TestGetCampaignGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCampaignGoals, self).setUp()
        self.com_name = 'Test Get Campaign Goals'
        self.com_description = 'To Test Get Campaign Goals'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.goal_one = self.create_campaign_goal(self.campaign.id,
                                                  'Goal One',
                                                  'Its Goal One',
                                                  'project',
                                                  start=now - timedelta(days=3),
                                                  end=now - timedelta(days=2))
        self.goal_two = self.create_campaign_goal(self.campaign.id,
                                                  'Goal Two',
                                                  'Its Goal Two',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))
        self.goal_three = self.create_campaign_goal(self.campaign.id,
                                                    'Goal Three',
                                                    'Its Goal Three',
                                                    'project',
                                                    start=now + timedelta(days=1),
                                                    end=now + timedelta(days=2))
        self.goal_ids = (self.goal_one.id, self.goal_two.id, self.goal_three.id)

    @tag('campaign')
    def test_simple_get_goals(self):
        goals = campaign.goals(self.campaign, filter_inactive=False)
        assert_equal(3, len(goals))
        for goal in goals:
            assert_true(goal.id in self.goal_ids)

    @tag('campaign')
    def test_get_filter_inactive(self):
        goal = campaign.goals(self.campaign, filter_inactive=True)
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(self.goal_two.id, goal.id)

    @tag('campaign')
    def test_simple_get_specific_goals(self):
        goal_ids = (self.goal_one.id, self.goal_two.id)
        goals = campaign.goals(self.campaign, goal_ids=goal_ids, filter_inactive=False)
        assert_equal(2, len(goals))
        for goal in goals:
            assert_true(goal.id in goal_ids)

    @tag('campaign')
    def test_get_filter_inactive_specific_goals(self):
        goal_ids = (self.goal_one.id, self.goal_two.id)
        goal = campaign.goals(self.campaign, goal_ids=goal_ids, filter_inactive=True)
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(self.goal_two.id, goal.id)


class TestAddCampaignGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAddCampaignGoal, self).setUp()
        self.com_name = 'Test Add Campaign Goal'
        self.com_description = 'To Test Add Campaign Goal.'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

    @tag('campaign')
    def test_simple_add(self):
        campaign.add_goal(self.campaign,
                          'Test Simple Add',
                          'To Test Simple Add',
                          'project')
        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Simple Add', goal.name)
        assert_equal('To Test Simple Add', goal.description)
        assert_equal('project', goal.type)
        assert_true(isinstance(goal.start, datetime))
        assert_true(goal.end is None)

    @tag('campaign')
    def test_add_start_end_specified(self):
        start = datetime.utcnow()
        end = start + timedelta(days=30)
        campaign.add_goal(self.campaign,
                          'Test Add Start End Specified',
                          'To Test Add Start End Specified',
                          'project',
                          start=start,
                          end=end)
        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Add Start End Specified', goal.name)
        assert_equal('To Test Add Start End Specified', goal.description)
        assert_equal('project', goal.type)
        assert_equal(pytz.UTC.localize(start), goal.start)
        assert_equal(pytz.UTC.localize(end), goal.end)

    @tag('campaign')
    def test_add_with_metadata(self):
        campaign.add_goal(self.campaign,
                          'Test Add With Metadata',
                          'To Test Add With Metadata',
                          'project',
                          mdata_key_one='mdata value one',
                          mdata_key_two='mdata value two')
        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Add With Metadata', goal.name)
        assert_equal('To Test Add With Metadata', goal.description)
        assert_equal('project', goal.type)
        assert_true(isinstance(goal.start, datetime))
        assert_true(goal.end is None)
        assert_equal(goal.mdata_key_one, u'mdata value one')
        assert_equal(goal.mdata_key_two, u'mdata value two')

    @tag('campaign')
    def test_add_goals_as_milestones(self):
        names = ('Milestone One', 'Milestone Two', 'Milestone Three')
        last_goal = None
        for name in names:
            last_goal = campaign.add_goal(self.campaign,
                                          name,
                                          name,
                                          'project',
                                          predecessor=last_goal)
        goals = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).order_by('campaign_goal.id').all()
        assert_equal(3, len(goals))

        check_last_goal = None
        for (i, goal) in enumerate(goals):
            assert_equal(names[i], goal.name)
            assert_equal(names[i], goal.description)
            if not check_last_goal:
                assert_true(goal.predecessor is None)
                assert_equal(goals[i + 1], goal.descendant)
            else:
                assert_equal(check_last_goal, goal.predecessor)
                if i == 1:
                    assert_equal(goals[i + 1], goal.descendant)
                else:
                    assert_true(goal.descendant is None)
            check_last_goal = goal


class TestCampaignGoalUserAssociation(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCampaignGoalUserAssociation, self).setUp()
        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

        self.com_name = 'Test Campaign Goal Association'
        self.com_description = 'To Test Campaign Goal Association'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.goal_one = self.create_campaign_goal(self.campaign.id,
                                                  'Goal One',
                                                  'Its Goal One',
                                                  'project',
                                                  start=now - timedelta(days=3),
                                                  end=now - timedelta(days=2))
        self.goal_two = self.create_campaign_goal(self.campaign.id,
                                                  'Goal Two',
                                                  'Its Goal Two',
                                                  'project',
                                                  start=now - timedelta(days=1),
                                                  end=now + timedelta(days=1))
        self.goal_three = self.create_campaign_goal(self.campaign.id,
                                                    'Goal Three',
                                                    'Its Goal Three',
                                                    'project',
                                                    start=now + timedelta(days=1),
                                                    end=now + timedelta(days=2))

    @tag('campaign')
    def test_simple_association(self):
        campaign.associate_user_with_goal(self.goal_one, self.user, 'participating')
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_one)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_one.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

    @tag('campaign')
    def test_multiple_associations(self):
        campaign.associate_user_with_goal(self.goal_one, self.user, 'participating')
        campaign.associate_user_with_goal(self.goal_two, self.user, 'participating')
        campaign.associate_user_with_goal(self.goal_three, self.user, 'participating')

        # Goal One
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_one)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_one.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Two
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_two)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_two.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Three
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_three)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_three.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

    @tag('campaign')
    def test_associations_by_goal_assosiation(self):
        campaign.associate_user(self.campaign, self.user, 'participant', 'opted-in')

        # Goal One: Inactive
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_one)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_one.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Two: Active
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_two)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_two.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Three: Inactive
        cga = CampaignGoalAssociationModel.query.filter_by(user=self.user)\
                                                .filter_by(campaign_id=self.campaign.id)\
                                                .filter_by(campaign_goal=self.goal_three)\
                                                .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_three.id, cga.campaign_goal.id)
        assert_equal(self.campaign.id, cga.campaign_id)
        assert_equal(self.user.id, cga.user.id)

    @tag('campaign')
    @raises(InvalidGoalParticipationNameError)
    def test_invalid_association(self):
        campaign.associate_user_with_goal(self.goal_one, self.user, 'wedontneednostinkingoals')

    @tag('campaign')
    @raises(DuplicateCampaignGoalUserAssociationError)
    def test_duplicate_association(self):
        campaign.associate_user_with_goal(self.goal_one, self.user, 'opted-in')
        campaign.associate_user_with_goal(self.goal_one, self.user, 'opted-in')


class TestUpdateCampaignGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateCampaignGoal, self).setUp()
        self.com_name = 'Test Update Campaign Goal'
        self.com_description = 'To Test Update Campaign Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.start = now - timedelta(days=3)
        self.goal = self.create_campaign_goal(self.campaign.id,
                                              'Update Goal',
                                              'Its Update Goal',
                                              'project',
                                              start=self.start)
        self.goal_meta = self.create_campaign_goal_meta(self.goal.id,
                                                        meta_key_one='meta_value_one')

    @tag('campaign')
    def test_update_name_description(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)

        campaign.update_goal(self.goal, name='Updated Goal', description='Its Updated Goal')
        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Updated Goal', goal.name)
        assert_equal('Its Updated Goal', goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)

    @tag('campaign')
    def test_update_meta(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        old_meta_value_one = self.goal.meta_key_one

        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(hasattr(goal, 'meta_key_one'))
        assert_equal(old_meta_value_one, goal.meta_key_one)
        assert_true(not hasattr(goal, 'meta_key_two'))

        campaign.update_goal(self.goal,
                             meta_key_one='meta value one updated',
                             meta_key_two='meta value two created')

        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(hasattr(goal, 'meta_key_one'))
        assert_equal('meta value one updated', goal.meta_key_one)
        assert_true(hasattr(goal, 'meta_key_two'))
        assert_equal('meta value two created', goal.meta_key_two)

    @tag('campaign')
    def test_delete_meta(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        old_meta_value_one = self.goal.meta_key_one

        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(hasattr(goal, 'meta_key_one'))
        assert_equal(old_meta_value_one, goal.meta_key_one)

        campaign.update_goal(self.goal,
                             meta_key_one=None)

        goal = CampaignGoalModel.query.filter_by(campaign_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(not hasattr(goal, 'meta_key_one'))


class TestDisableCampaignGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDisableCampaignGoal, self).setUp()
        self.com_name = 'Test Disable Campaign Goal'
        self.com_description = 'To Test Disable Campaign Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.campaign = self.create_campaign(self.com_name,
                                             self.com_description,
                                             self.com_start,
                                             self.com_end)
        self.com_id = self.campaign.id

        now = datetime.utcnow()
        self.start = now - timedelta(days=3)
        self.goal = self.create_campaign_goal(self.campaign.id,
                                              'Update Goal',
                                              'Its Update Goal',
                                              'project',
                                              start=self.start)

    @tag('campaign')
    def test_simple_disable(self):
        campaign.disable_goal(self.goal)
        campaign_goal = CampaignGoalModel.query.get(self.goal.id)
        assert_false(campaign_goal.enabled)

    @tag('campaign')
    def test_simple_disable_then_get(self):
        campaign.disable_goal(self.goal)
        campaign_goal = campaign.goal(self.goal.id)
        assert_true(campaign_goal is None)
