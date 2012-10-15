.. _api:

pooldlib
========


Console
-------

Application
^^^^^^^^^^^

.. autoclass:: pooldlib.cli.App
   :members:


Command
^^^^^^^

.. autoclass:: pooldlib.cli.RootController
.. autoclass:: pooldlib.cli.ServerController
.. autoclass:: pooldlib.cli.ShellController


Flask
-----

.. autofunction:: pooldlib.flask.test.run
.. autofunction:: pooldlib.flask.test.suites
.. autoclass:: pooldlib.flask.test.TestSuite
.. autoclass:: pooldlib.flask.test.ContextCaseMixin
.. autoclass:: pooldlib.flask.test.RequestCaseMixin
.. autoclass:: pooldlib.flask.test.SessionCaseMixin


Postgresql
----------

.. autoclass:: pooldlib.postgresql.Database

Models
^^^^^^

.. autoclass:: pooldlib.postgresql.models.Balance
.. autoclass:: pooldlib.postgresql.models.Community
.. autoclass:: pooldlib.postgresql.models.Currency
.. autoclass:: pooldlib.postgresql.models.Fee
.. autoclass:: pooldlib.postgresql.models.InternalLedger
.. autoclass:: pooldlib.postgresql.models.ExternalLedger
.. autoclass:: pooldlib.postgresql.models.Purchase
.. autoclass:: pooldlib.postgresql.models.Transfer
.. autoclass:: pooldlib.postgresql.models.Transaction
.. autoclass:: pooldlib.postgresql.models.Exchange
.. autoclass:: pooldlib.postgresql.models.User
.. autoclass:: pooldlib.postgresql.models.AnonymousUser
.. autoclass:: pooldlib.postgresql.models.UserPurchase


Types
^^^^^

.. autoclass:: pooldlib.postgresql.types.DateTimeTZ
.. autoclass:: pooldlib.postgresql.types.UUID


Common
^^^^^^

.. autoclass:: pooldlib.postgresql.common.EnabledMixin
.. autoclass:: pooldlib.postgresql.common.DisabledMixin
.. autoclass:: pooldlib.postgresql.common.VerifiedMixin
.. autoclass:: pooldlib.postgresql.common.ActiveMixin
.. autoclass:: pooldlib.postgresql.common.BalanceMixin
.. autoclass:: pooldlib.postgresql.common.Model
.. autoclass:: pooldlib.postgresql.common.ConfigurationModel
.. autoclass:: pooldlib.postgresql.common.LedgerModel
.. autoclass:: pooldlib.postgresql.common.IDMixin
.. autoclass:: pooldlib.postgresql.common.UUIDMixin
.. autoclass:: pooldlib.postgresql.common.NameMixin
.. autoclass:: pooldlib.postgresql.common.NullNameMixin
.. autoclass:: pooldlib.postgresql.common.DescriptionMixin
.. autoclass:: pooldlib.postgresql.common.SlugMixin
.. autoclass:: pooldlib.postgresql.common.TrackTimeMixin
.. autoclass:: pooldlib.postgresql.common.TrackIPMixin
.. autoclass:: pooldlib.postgresql.common.KeyValueMixin
.. autoclass:: pooldlib.postgresql.common.FieldUpdateMixin
.. autoclass:: pooldlib.postgresql.common.SerializationMixin
.. autoclass:: pooldlib.postgresql.common.LedgerMixin


SQLAlchemy
----------

.. autoclass:: pooldlib.sqlalchemy.Database
.. automodule:: pooldlib.sqlalchemy.transaction
    :members:

API
---

.. autofunction:: pooldlib.api.balance.get
.. autoclass:: pooldlib.api.transact.Transact
   :members:


Utils
-----

.. automodule:: pooldlib.util.signals
