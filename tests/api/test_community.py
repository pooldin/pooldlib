from datetime import datetime, timedelta
from uuid import uuid4 as uuid
from nose.tools import raises, assert_equal, assert_true, assert_false

from pooldlib.exceptions import InvalidUserRoleError
from pooldlib.postgresql import db
from pooldlib.postgresql import (Community as CommunityModel,
                                 CommunityGoal as CommunityGoalModel,
                                 CommunityGoalMeta as CommunityGoalMetaModel,
                                 CommunityAssociation as CommunityAssociationModel)
from pooldlib.api import community

from tests.base import PooldLibPostgresBaseTest


class TestGetCommunity(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunity, self).setUp()
        self.com_name = 'TestGetCommunity'
        self.com_description = 'To Test Get Community'
        self.community = self.create_community(self.com_name, self.com_description)
        self.com_id = self.community.id

    def test_simple_get(self):
        com = community.get(self.com_id)
        assert_equal(self.com_name, com.name)
        assert_equal(self.com_description, com.description)

    def test_get_inactive_not_returned(self):
        now = datetime.utcnow()
        com = self.create_community('Test Incactive Community Not Returned.',
                                    'Test Incactive Community Not Returned.',
                                    start=now + timedelta(days=1),
                                    end=now + timedelta(days=2))
        ret = community.get(com.id, filter_inactive=True)
        assert_true(ret is None)

    def test_get_inactiv_returned(self):
        now = datetime.utcnow()
        com = self.create_community('Test Incactive Community Returned.',
                                    'Test Incactive Community Returned.',
                                    start=now + timedelta(days=1),
                                    end=now + timedelta(days=2))
        ret = community.get(com.id)
        assert_equal(com.name, ret.name)
        assert_equal(com.description, ret.description)


class TestGetCommunities(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunities, self).setUp()

        self.com_one_name = 'Test Get Communities One'
        self.com_one_description = 'To Test Get Communities: One'
        self.com_one_start = datetime.utcnow() - timedelta(days=3)
        self.com_one_end = self.com_one_start + timedelta(days=2)
        self.community_one = self.create_community(self.com_one_name,
                                                   self.com_one_description,
                                                   self.com_one_start,
                                                   self.com_one_end)
        self.com_one_id = self.community_one.id

        self.com_two_name = 'Test Get Communities Two'
        self.com_two_description = 'To Test Get Communities: Two'
        self.com_two_start = datetime.utcnow() - timedelta(days=1)
        self.com_two_end = self.com_two_start + timedelta(days=2)
        self.community_two = self.create_community(self.com_two_name,
                                                   self.com_two_description,
                                                   self.com_two_start,
                                                   self.com_two_end)
        self.com_two_id = self.community_two.id

        self.com_three_name = 'Test Get Communities Three'
        self.com_three_description = 'To Test Get Communities: Three'
        self.com_three_start = datetime.utcnow() + timedelta(days=2)
        self.com_three_end = self.com_three_start + timedelta(days=2)
        self.community_three = self.create_community(self.com_three_name,
                                                     self.com_three_description,
                                                     self.com_three_start,
                                                     self.com_three_end)
        self.com_three_id = self.community_three.id

    def test_get_all_communities(self):
        comms = community.communities(None, filter_inactive=False)
        # At this point we don't know the current state of the db, so there
        # should be a minimum of 3 communities existing.
        assert_true(3 <= len(comms))

    def test_get_all_communities_exclude_inactive(self):
        comms = community.communities(None, filter_inactive=True)
        # At this point we don't know the current state of the db, so there
        # should be a minimum of 1 active community existing.
        assert_true(1 <= len(comms))

    def test_get_all_communities_in_list(self):
        comms = community.communities([self.com_one_id, self.com_two_id, self.com_three_id],
                                      filter_inactive=False)
        assert_equal(3, len(comms))

    def test_get_communities_exclude_inactive(self):
        comms = community.communities([self.com_one_id, self.com_two_id, self.com_three_id],
                                      filter_inactive=True)
        assert_equal(1, len(comms))

    def test_get_communities_exclude_all_inactive(self):
        comms = community.communities([self.com_one_id, self.com_three_id])
        assert_equal(0, len(comms))


class TestCreateCommunity(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCreateCommunity, self).setUp()
        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    def test_simple_create(self):
        com_name = uuid().hex
        com = community.create(self.user,
                               com_name,
                               'It Tests Simple Community Creates.')
        assert_true(isinstance(com, CommunityModel))
        q_com = CommunityModel.query.filter_by(name=com_name).all()
        assert_equal(1, len(q_com))
        q_com = q_com[0]
        assert_equal('It Tests Simple Community Creates.', q_com.description)

    def test_organizer_association(self):
        com_name = uuid().hex
        com = community.create(self.user,
                               com_name,
                               'It Tests Organizer Association Creates.')
        assert_true(isinstance(com, CommunityModel))
        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == com.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    def test_organizer_association_with_username(self):
        com_name = uuid().hex
        com = community.create(self.user.username,
                               com_name,
                               'It Tests Organizer Association With Username Creates.')
        assert_true(isinstance(com, CommunityModel))
        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == com.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    def test_organizer_association_with_user_id(self):
        com_name = uuid().hex
        com = community.create(self.user.id,
                               com_name,
                               'It Tests Organizer Association With User ID Creates.')
        assert_true(isinstance(com, CommunityModel))
        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == com.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    def test_organizer_association_with_user_email(self):
        com_name = uuid().hex
        com = community.create(self.user.email,
                               com_name,
                               'It Tests Organizer Association With User Email Creates.')
        assert_true(isinstance(com, CommunityModel))
        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == com.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)


class TestCommunityAssociateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityAssociateUser, self).setUp()
        self.com_name = 'Test Association User With Communities'
        self.com_description = 'To Test Association User With Communities'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

    def test_associate_organizer(self):
        community.associate_user(self.community.id, self.user, 'organizer')

        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == self.community.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    def test_associate_participant(self):
        community.associate_user(self.community.id, self.user, 'participant')

        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == self.community.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('participant', ass.role)

    @raises(InvalidUserRoleError)
    def test_associate_unknown_role(self):
        community.associate_user(self.community.id, self.user, 'MinistryOfSillyWalks')


class TestCommunityUpdateUserRole(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityAssociateUser, self).setUp()


class TestCommunityDisassociateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityAssociateUser, self).setUp()


class TestUpdateCommunity(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateCommunity, self).setUp()


class TestGetCommunityTransfers(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityTransfers, self).setUp()


class TestGetCommunityGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityGoals, self).setUp()


class TestAddCommunityGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAddCommunityGoals, self).setUp()


class TestUpdateCommunityGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityGoals, self).setUp()
