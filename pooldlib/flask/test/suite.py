import unittest
from werkzeug.utils import import_string, find_modules


def iter_suites(name=None):
    name = name or __name__

    for module in find_modules(name):
        mod = import_string(module)
        if hasattr(mod, 'suite'):
            yield mod.suite()


def suites(name=None):
    return list(iter_suites(name=name))


class TestSuite(unittest.TestSuite):

    @classmethod
    def load(cls, name=None):
        cases = suites(name=name)
        return cls.create(cases)

    @classmethod
    def create(cls, cases=None):
        cases = cases or []
        suite = cls()
        for case in cases:
            suite.addTest(unittest.makeSuite(case))
        return suite
