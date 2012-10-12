import unittest

from pooldlib.postgresql import db


class PooldLibDBBaseTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        # Close the session so we don't lock tables while trunc***** them.
        db.shutdown_session()

        # trunc*** is a four letter word
        tables = db.get_tables_for_bind()
        tables = ', '.join(['public.%s' % t.name for t in tables])
        sql = "TRUNCATE %s RESTART IDENTITY CASCADE" % tables
        db.session.execute(sql)
        db.session.commit()

        # Once again, close the session
        db.shutdown_session()

    def add_model(self, model):
        db.session.add(model)

    def commit_model(self, model):
        self.add_model(model)
        db.session.commit()
