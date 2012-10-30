import logging
import inspect

from pooldlib import config


class Logger(object):

    def __init__(self, name, is_instance):
        self._name = name
        self.is_instance = is_instance
        self.logger = logging.getLogger(name)
        self.json_logging = config.POOLDLIB_LOGGING_FORMAT
        self.json_logging = True if self.json_logging in ('json', 'JSON') else False

    def _log(self, level, msg, *args, **kwargs):
        # We're two functions deep at this point
        calling_func = inspect.currentframe().f_back.f_back.f_code
        calling_func_name = calling_func.co_name

        if self.json_logging:
            data = kwargs['data'] if 'data' in kwargs else None
            if 'data' in kwargs:
                del kwargs['data']
            msg = self._json_msg(calling_func_name, msg, data=data, **kwargs)
            kwargs = dict()
        else:
            calling_key = 'function' if not self.is_instance else 'method'
            kwargs[calling_key] = calling_func_name
        msg_add = ', '.join(['%s :: %s' % (k, v) for (k, v) in kwargs.items() if k != 'exc_info'])
        del_keys = [k for k in kwargs if k != 'exc_info']
        for key in del_keys:
            del kwargs[key]
        if msg_add:
            msg += ' :: %s' % msg_add

        self.logger.log(level, msg, *args, **kwargs)

    def _json_msg(self, caller_name, msg, data=None, **kwargs):
        import json
        calling_key = 'function' if not self.is_instance else 'method'
        msg = {calling_key: caller_name,
               'data': data,
               'message': msg,
               'meta': dict()}
        for (k, v) in kwargs.items():
            msg['meta'][k] = v
        return json.dumps(msg)

    def debug(self, msg, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs["exc_info"] = 1
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def transaction(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    # Shorthand functions
    warn = warning
    err = error
    exc = exception
    crit = critical


def get_logger(obj, logging_name=None):
    is_instance = False
    if obj and hasattr(obj, '__class__'):
        is_instance = True
        name = '%s.%s' % (obj.__class__.__module__,
                          obj.__class__.__name__)
    elif obj and hasattr(obj, '__name__'):
        name = obj.__name__
    else:
        if logging_name is None:
            msg = 'If ``obj`` is not given ``logger_name`` must be defined.'
            raise TypeError(msg)
        name = logging_name

    logger = Logger(name, is_instance)
    return logger
