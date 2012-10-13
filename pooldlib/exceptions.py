class TransactError(Exception):
    """Base class for errors encountered during operation of
    pooldlib.api.Transact calls."""


class InsufficentFundsTransferError(Exception):
    """An attempt was made to transfer too much currency from
    one balance to another."""
