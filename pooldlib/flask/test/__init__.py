from pooldlib.flask.test.suite import TestSuite, suites, iter_suites
from pooldlib.flask.test.mixin import ContextCaseMixin, RequestCaseMixin, SessionCaseMixin


def run(name):
    import unittest
    from flask import testsuite

    class BetterLoader(testsuite.BetterLoader):

        def getRootSuite(self):
            return suites(name)

    unittest.main(testLoader=BetterLoader(), defaultTest='suite')
