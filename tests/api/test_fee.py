from nose.tools import raises, assert_equal, assert_true, assert_false

from pooldlib.api import fee

from tests import tag
from tests.base import PooldLibPostgresBaseTest


class TestFeeGet(PooldLibPostgresBaseTest):

    @tag('fee')
    def test_get_name(self):
        ret = fee.get('gimmy-more')
        assert_equal(1, len(ret))
        ret = ret[0]
        assert_equal('Fee used for testing.', ret.description)

    @tag('fee')
    def test_get_names(self):
        ret = fee.get(None, ('stripe-transaction', 'poold-transaction'))
        assert_equal(2, len(ret))
