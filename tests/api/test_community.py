from datetime import datetime, timedelta
import pytz
from uuid import uuid4 as uuid
from nose.tools import raises, assert_equal, assert_true, assert_false

from pooldlib.exceptions import (InvalidUserRoleError,
                                 InvalidGoalParticipationNameError,
                                 UnknownCommunityError,
                                 DuplicateCommunityUserAssociationError,
                                 DuplicateCommunityGoalUserAssociationError)
from pooldlib.postgresql import db
from pooldlib.postgresql import (Community as CommunityModel,
                                 CommunityGoal as CommunityGoalModel,
                                 CommunityGoalAssociation as CommunityGoalAssociationModel,
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
        com = community.get(self.com_id, filter_inactive=True)
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

    def test_get_inactive_returned(self):
        now = datetime.utcnow()
        com = self.create_community('Test Incactive Community Returned.',
                                    'Test Incactive Community Returned.',
                                    start=now + timedelta(days=1),
                                    end=now + timedelta(days=2))
        ret = community.get(com.id, filter_inactive=False)
        assert_equal(com.name, ret.name)
        assert_equal(com.description, ret.description)

    def test_get_disabled_not_returned(self):
        self.community.enabled = False
        db.session.commit()
        ret = community.get(self.com_id)
        assert_true(ret is None)


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
        community.associate_user(self.community, self.user, 'organizer', 'participating')

        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == self.community.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('organizer', ass.role)

    def test_associate_participant(self):
        community.associate_user(self.community, self.user, 'participant', 'participating')

        ass = CommunityAssociationModel.query.filter(CommunityAssociationModel.user_id == self.user.id)\
                                             .filter(CommunityAssociationModel.community_id == self.community.id)\
                                             .all()
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal('participant', ass.role)

    @raises(InvalidUserRoleError)
    def test_associate_unknown_role(self):
        community.associate_user(self.community, self.user, 'MinisterOfSillyWalks', 'walker')

    @raises(DuplicateCommunityUserAssociationError)
    def test_create_duplicate_association(self):
        community.associate_user(self.community, self.user, 'organizer', 'participating')
        community.associate_user(self.community, self.user, 'organizer', 'participating')


class TestDisableCommunity(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDisableCommunity, self).setUp()
        self.com_name = 'Test Association User With Communities'
        self.com_description = 'To Test Association User With Communities'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

    def test_simple_disable(self):
        community.disable(self.community)
        ret = CommunityModel.query.get(self.com_id)
        assert_false(ret.enabled)

    def test_simple_disable_with_id(self):
        community.disable(self.community)
        ret = CommunityModel.query.get(self.com_id)
        assert_false(ret.enabled)


class TestGetAssociations(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetAssociations, self).setUp()
        self.com_name = 'Test Association User With Communities'
        self.com_description = 'To Test Association User With Communities'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        self.username_one = uuid().hex
        self.name_one = '%s %s' % (self.username_one[:16], self.username_one[16:])
        self.email_one = '%s@example.com' % self.username_one
        self.user_one = self.create_user(self.username_one, self.name_one, self.email_one)
        self.create_community_association(self.community, self.user_one, 'participant')

        self.username_two = uuid().hex
        self.name_two = '%s %s' % (self.username_two[:16], self.username_two[16:])
        self.email_two = '%s@example.com' % self.username_two
        self.user_two = self.create_user(self.username_two, self.name_two, self.email_two)
        self.create_community_association(self.community, self.user_two, 'participant')

        self.username_three = uuid().hex
        self.name_three = '%s %s' % (self.username_three[:16], self.username_three[16:])
        self.email_three = '%s@example.com' % self.username_three
        self.user_three = self.create_user(self.username_three, self.name_three, self.email_three)
        self.create_community_association(self.community, self.user_three, 'participant')

        self.user_ids = (self.user_one.id, self.user_two.id, self.user_three.id)

    def test_simple_get(self):
        asses = community.get_associations(self.community)
        assert_equal(3, len(asses))
        for ass in asses:
            assert_true(ass.user_id in self.user_ids)

    def test_get_single_association(self):
        ass = community.get_associations(self.community, user=self.user_one)
        assert_equal(1, len(ass))
        ass = ass[0]
        assert_equal(ass.user_id, self.user_one.id)
        assert_equal(ass.community_id, self.community.id)


class TestCommunityUpdateUserRole(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityUpdateUserRole, self).setUp()
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
        self.create_community_association(self.community, self.user, 'organizer')

    def test_update_new_role(self):
        ass = CommunityAssociationModel.query.filter_by(community_id=self.com_id,
                                                        user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_equal('organizer', ass.role)
        community.update_user_association(self.community, self.user, 'participant')

        ass = CommunityAssociationModel.query.filter_by(community_id=self.com_id,
                                                        user_id=self.user.id).first()
        assert_true(ass is not None)
        assert_equal('participant', ass.role)


class TestCommunityDisassociateUser(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityDisassociateUser, self).setUp()
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
        self.create_community_association(self.community, self.user, 'organizer')

    def test_remove_user_association(self):
        ass = CommunityAssociationModel.query.filter_by(community_id=self.com_id,
                                                        user_id=self.user.id).first()
        assert_true(ass is not None)

        community.disassociate_user(self.community, self.user)

        ass = CommunityAssociationModel.query.filter_by(community_id=self.com_id,
                                                        user_id=self.user.id).first()
        assert_true(ass is None)


class TestUpdateCommunity(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateCommunity, self).setUp()


class TestGetCommunityTransfers(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityTransfers, self).setUp()


class TestGetCommunityGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityGoal, self).setUp()
        self.com_name = 'Test Get Community Goal'
        self.com_description = 'To Test Get Community Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        now = datetime.utcnow()
        self.goal_one = self.create_community_goal(self.community.id,
                                                   'Goal One',
                                                   'Its Goal One',
                                                   'project',
                                                   start=now - timedelta(days=3),
                                                   end=now - timedelta(days=2))
        self.goal_two = self.create_community_goal(self.community.id,
                                                   'Goal Two',
                                                   'Its Goal Two',
                                                   'project',
                                                   start=now - timedelta(days=1),
                                                   end=now + timedelta(days=1))
        self.goal_three = self.create_community_goal(self.community.id,
                                                     'Goal Three',
                                                     'Its Goal Three',
                                                     'project',
                                                     start=now + timedelta(days=1),
                                                     end=now + timedelta(days=2))

    def test_simple_get(self):
        goal = community.goal(self.goal_one.id, filter_inactive=False)
        assert_equal(self.goal_one.id, goal.id)

        goal = community.goal(self.goal_two.id, filter_inactive=False)
        assert_equal(self.goal_two.id, goal.id)

        goal = community.goal(self.goal_three.id, filter_inactive=False)
        assert_equal(self.goal_three.id, goal.id)

    def test_get_filter_inactive(self):
        goal = community.goal(self.goal_one.id, filter_inactive=True)
        assert_true(goal is None)

        goal = community.goal(self.goal_two.id, filter_inactive=True)
        assert_equal(self.goal_two.id, goal.id)

        goal = community.goal(self.goal_three.id, filter_inactive=True)
        assert_true(goal is None)


class TestGetCommunityGoals(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestGetCommunityGoals, self).setUp()
        self.com_name = 'Test Get Community Goals'
        self.com_description = 'To Test Get Community Goals'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        now = datetime.utcnow()
        self.goal_one = self.create_community_goal(self.community.id,
                                                   'Goal One',
                                                   'Its Goal One',
                                                   'project',
                                                   start=now - timedelta(days=3),
                                                   end=now - timedelta(days=2))
        self.goal_two = self.create_community_goal(self.community.id,
                                                   'Goal Two',
                                                   'Its Goal Two',
                                                   'project',
                                                   start=now - timedelta(days=1),
                                                   end=now + timedelta(days=1))
        self.goal_three = self.create_community_goal(self.community.id,
                                                     'Goal Three',
                                                     'Its Goal Three',
                                                     'project',
                                                     start=now + timedelta(days=1),
                                                     end=now + timedelta(days=2))
        self.goal_ids = (self.goal_one.id, self.goal_two.id, self.goal_three.id)

    def test_simple_get_goals(self):
        goals = community.goals(self.community, filter_inactive=False)
        assert_equal(3, len(goals))
        for goal in goals:
            assert_true(goal.id in self.goal_ids)

    def test_get_filter_inactive(self):
        goal = community.goals(self.community, filter_inactive=True)
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(self.goal_two.id, goal.id)

    def test_simple_get_specific_goals(self):
        goal_ids = (self.goal_one.id, self.goal_two.id)
        goals = community.goals(self.community, goal_ids=goal_ids, filter_inactive=False)
        assert_equal(2, len(goals))
        for goal in goals:
            assert_true(goal.id in goal_ids)

    def test_get_filter_inactive_specific_goals(self):
        goal_ids = (self.goal_one.id, self.goal_two.id)
        goal = community.goals(self.community, goal_ids=goal_ids, filter_inactive=True)
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(self.goal_two.id, goal.id)


class TestAddCommunityGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestAddCommunityGoal, self).setUp()
        self.com_name = 'Test Add Community Goal'
        self.com_description = 'To Test Add Community Goal.'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

    def test_simple_add(self):
        community.add_goal(self.community,
                           'Test Simple Add',
                           'To Test Simple Add',
                           'project')
        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Simple Add', goal.name)
        assert_equal('To Test Simple Add', goal.description)
        assert_equal('project', goal.type)
        assert_true(isinstance(goal.start, datetime))
        assert_true(goal.end is None)

    def test_add_start_end_specified(self):
        start = datetime.utcnow()
        end = start + timedelta(days=30)
        community.add_goal(self.community,
                           'Test Add Start End Specified',
                           'To Test Add Start End Specified',
                           'project',
                           start=start,
                           end=end)
        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Add Start End Specified', goal.name)
        assert_equal('To Test Add Start End Specified', goal.description)
        assert_equal('project', goal.type)
        assert_equal(pytz.UTC.localize(start), goal.start)
        assert_equal(pytz.UTC.localize(end), goal.end)

    def test_add_with_metadata(self):
        community.add_goal(self.community,
                           'Test Add With Metadata',
                           'To Test Add With Metadata',
                           'project',
                           mdata_key_one='mdata value one',
                           mdata_key_two='mdata value two')
        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Test Add With Metadata', goal.name)
        assert_equal('To Test Add With Metadata', goal.description)
        assert_equal('project', goal.type)
        assert_true(isinstance(goal.start, datetime))
        assert_true(goal.end is None)
        assert_equal(goal.mdata_key_one, u'mdata value one')
        assert_equal(goal.mdata_key_two, u'mdata value two')


class TestCommunityGoalUserAssociation(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestCommunityGoalUserAssociation, self).setUp()
        self.username = uuid().hex
        self.name = '%s %s' % (self.username[:16], self.username[16:])
        self.email = '%s@example.com' % self.username
        self.user = self.create_user(self.username, self.name, self.email)

        self.com_name = 'Test Community Goal Association'
        self.com_description = 'To Test Community Goal Association'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        now = datetime.utcnow()
        self.goal_one = self.create_community_goal(self.community.id,
                                                   'Goal One',
                                                   'Its Goal One',
                                                   'project',
                                                   start=now - timedelta(days=3),
                                                   end=now - timedelta(days=2))
        self.goal_two = self.create_community_goal(self.community.id,
                                                   'Goal Two',
                                                   'Its Goal Two',
                                                   'project',
                                                   start=now - timedelta(days=1),
                                                   end=now + timedelta(days=1))
        self.goal_three = self.create_community_goal(self.community.id,
                                                     'Goal Three',
                                                     'Its Goal Three',
                                                     'project',
                                                     start=now + timedelta(days=1),
                                                     end=now + timedelta(days=2))

    def test_simple_association(self):
        community.associate_user_with_goal(self.goal_one, self.user, 'participating')
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_one)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_one.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

    def test_multiple_associations(self):
        community.associate_user_with_goal(self.goal_one, self.user, 'participating')
        community.associate_user_with_goal(self.goal_two, self.user, 'participating')
        community.associate_user_with_goal(self.goal_three, self.user, 'participating')

        # Goal One
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_one)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_one.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Two
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_two)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_two.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Three
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_three)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('participating', cga.participation)
        assert_equal(self.goal_three.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

    def test_associations_by_goal_assosiation(self):
        community.associate_user(self.community, self.user, 'participant', 'opted-in')

        # Goal One: Inactive
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_one)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_one.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Two: Active
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_two)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_two.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

        # Goal Three: Inactive
        cga = CommunityGoalAssociationModel.query.filter_by(user=self.user)\
                                                 .filter_by(community_id=self.community.id)\
                                                 .filter_by(community_goal=self.goal_three)\
                                                 .first()
        cga = cga or None
        assert_true(cga is not None)
        assert_equal('opted-in', cga.participation)
        assert_equal(self.goal_three.id, cga.community_goal.id)
        assert_equal(self.community.id, cga.community_id)
        assert_equal(self.user.id, cga.user.id)

    @raises(InvalidGoalParticipationNameError)
    def test_invalid_association(self):
        community.associate_user_with_goal(self.goal_one, self.user, 'wedontneednostinkingoals')

    @raises(DuplicateCommunityGoalUserAssociationError)
    def test_duplicate_association(self):
        community.associate_user_with_goal(self.goal_one, self.user, 'opted-in')
        community.associate_user_with_goal(self.goal_one, self.user, 'opted-in')


class TestUpdateCommunityGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestUpdateCommunityGoal, self).setUp()
        self.com_name = 'Test Update Community Goal'
        self.com_description = 'To Test Update Community Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        now = datetime.utcnow()
        self.start = now - timedelta(days=3)
        self.goal = self.create_community_goal(self.community.id,
                                               'Update Goal',
                                               'Its Update Goal',
                                               'project',
                                               start=self.start)
        self.goal_meta = self.create_community_goal_meta(self.goal.id,
                                                         meta_key_one='meta_value_one')

    def test_update_name_description(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)

        community.update_goal(self.goal, name='Updated Goal', description='Its Updated Goal')
        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal('Updated Goal', goal.name)
        assert_equal('Its Updated Goal', goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)

    def test_update_meta(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        old_meta_value_one = self.goal.meta_key_one

        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(hasattr(goal, 'meta_key_one'))
        assert_equal(old_meta_value_one, goal.meta_key_one)
        assert_true(not hasattr(goal, 'meta_key_two'))

        community.update_goal(self.goal,
                              meta_key_one='meta value one updated',
                              meta_key_two='meta value two created')

        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
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

    def test_delete_meta(self):
        old_name = self.goal.name
        old_description = self.goal.description
        old_start = self.goal.start
        old_end = self.goal.end
        old_meta_value_one = self.goal.meta_key_one

        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(hasattr(goal, 'meta_key_one'))
        assert_equal(old_meta_value_one, goal.meta_key_one)

        community.update_goal(self.goal,
                              meta_key_one=None)

        goal = CommunityGoalModel.query.filter_by(community_id=self.com_id).all()
        assert_equal(1, len(goal))
        goal = goal[0]
        assert_equal(old_name, goal.name)
        assert_equal(old_description, goal.description)
        assert_equal(old_start, goal.start)
        assert_equal(old_end, goal.end)
        assert_true(not hasattr(goal, 'meta_key_one'))


class TestDisableCommunityGoal(PooldLibPostgresBaseTest):

    def setUp(self):
        super(TestDisableCommunityGoal, self).setUp()
        self.com_name = 'Test Disable Community Goal'
        self.com_description = 'To Test Disable Community Goal'
        self.com_start = datetime.utcnow() - timedelta(days=2)
        self.com_end = self.com_start + timedelta(days=4)
        self.community = self.create_community(self.com_name,
                                               self.com_description,
                                               self.com_start,
                                               self.com_end)
        self.com_id = self.community.id

        now = datetime.utcnow()
        self.start = now - timedelta(days=3)
        self.goal = self.create_community_goal(self.community.id,
                                               'Update Goal',
                                               'Its Update Goal',
                                               'project',
                                               start=self.start)

    def test_simple_disable(self):
        community.disable_goal(self.goal)
        community_goal = CommunityGoalModel.query.get(self.goal.id)
        assert_false(community_goal.enabled)

    def test_simple_disable_then_get(self):
        community.disable_goal(self.goal)
        community_goal = community.goal(self.goal.id)
        assert_true(community_goal is None)
