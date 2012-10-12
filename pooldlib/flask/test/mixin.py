import json
import time
from datetime import datetime, timedelta
from cookielib import Cookie

from werkzeug.urls import url_encode


class ContextCaseMixin(object):

    def create_app(self):
        raise NotImplementedError()

    def setup_context(self):
        self.app = self.create_app()
        self.client = self.app.test_client()

    def teardown_context(self):
        pass


class RequestCaseMixin(object):

    def request(self, *args, **kw):
        accept = kw.pop('accept', None)
        if accept:
            kw['headers'] = list(kw.get('headers') or [])
            kw['headers'].append(('Accept', accept))
        return self.client.open(*args, **kw)

    def get(self, *args, **kw):
        kw['method'] = 'GET'
        return self.request(*args, **kw)

    def patch(self, *args, **kw):
        kw['method'] = 'PATCH'
        return self.request(*args, **kw)

    def patch_json(self, *args, **kw):
        kw['content_type'] = 'application/json'
        if 'data' in kw:
            kw['data'] = json.dumps(kw['data'])
        return self.patch(*args, **kw)

    def patch_form(self, *args, **kw):
        kw['content_type'] = 'application/x-www-form-urlencoded'
        if 'data' in kw:
            kw['data'] = url_encode(kw['data'])
        return self.patch(*args, **kw)

    def post(self, *args, **kw):
        kw['method'] = 'POST'
        return self.request(*args, **kw)

    def post_json(self, *args, **kw):
        kw['content_type'] = 'application/json'
        if 'data' in kw:
            kw['data'] = json.dumps(kw['data'])
        return self.post(*args, **kw)

    def post_form(self, *args, **kw):
        kw['content_type'] = 'application/x-www-form-urlencoded'
        if 'data' in kw:
            kw['data'] = url_encode(kw['data'])
        return self.post(*args, **kw)

    def head(self, *args, **kw):
        kw['method'] = 'HEAD'
        return self.request(*args, **kw)

    def put(self, *args, **kw):
        kw['method'] = 'PUT'
        return self.request(*args, **kw)

    def put_json(self, *args, **kw):
        kw['content_type'] = 'application/json'
        if 'data' in kw:
            kw['data'] = json.dumps(kw['data'])
        return self.put(*args, **kw)

    def put_form(self, *args, **kw):
        kw['content_type'] = 'application/x-www-form-urlencoded'
        if 'data' in kw:
            kw['data'] = url_encode(kw['data'])
        return self.put(*args, **kw)

    def delete(self, *args, **kw):
        kw['method'] = 'DELETE'
        return self.request(*args, **kw)


class SessionCaseMixin(object):

    @property
    def session_name(self):
        return self.app.config.get('SESSION_COOKIE_NAME')

    @property
    def session_serializer(self):
        return self.app.session_interface.get_serializer(self.app)

    @property
    def session_domain(self):
        return self.app.session_interface.get_cookie_domain(self.app)

    @property
    def session_path(self):
        return self.app.session_interface.get_cookie_path(self.app)

    def cookies(self):
        if not hasattr(self, 'client') or not self.client:
            return {}

        cookies = list(self.client.cookie_jar)

        if len(cookies) < 1:
            return {}

        return dict([(cookie.name, cookie) for cookie in cookies])

    def get_session(self, cookie=None):
        if not cookie:
            cookie = self.session_name

        if isinstance(cookie, basestring):
            cookie = self.cookies().get(cookie)

        if not cookie:
            return

        serializer = self.app.session_interface.get_serializer(self.app)
        return serializer.loads(cookie.value)

    def get_session_expires(self, now=None):
        expires = None
        lifetime = self.app.config.get('PERMANENT_SESSION_LIFETIME')

        if isinstance(lifetime, int):
            lifetime = timedelta(seconds=lifetime)

        if isinstance(lifetime, timedelta):
            expires = (now or datetime.utcnow()) + lifetime
            expires = time.mktime(expires.timetuple())

        return expires

    def get_session_cookie(self, name=None):
        name = name or self.session_name
        return self.cookies().get(name)

    def get_session_cookie_args(self, data=None, **kwargs):
        kw = {}
        kw['version'] = kwargs.get('version', 0)
        kw['name'] = kwargs.get('name', self.session_name)
        kw['value'] = self.session_serializer.dumps(data or {})
        kw['port'] = kwargs.get('port', None)
        kw['port_specified'] = bool(kw['port'])

        kw['domain'] = kwargs.get('domain', self.session_domain)
        kw['domain_specified'] = bool(kw['domain'])
        if not kw['domain']:
            kw['domain'] = 'localhost'

        dot = kw['domain_specified'] and kw['domain'][0] == '.'
        kw['domain_initial_dot'] = dot

        path = kwargs.get('path', self.session_path)
        if path:
            kw['path'] = path
            kw['path_specified'] = True
        else:
            kw['path_specified'] = False

        kw['expires'] = kwargs.get('expires')
        if not kw['expires']:
            kw['expires'] = self.get_session_expires()

        kw['discard'] = kwargs.get('discard', True)
        kw['comment'] = kwargs.get('comment', None)
        kw['comment_url'] = kwargs.get('comment_url', None)
        kw['rfc2109'] = kwargs.get('rfc2109', False)
        kw['rest'] = kwargs.get('rest', dict(HttpOnly=True))
        kw['secure'] = kwargs.get('secure', False)
        return kw

    def create_session_cookie(self, *args, **kw):
        kwargs = self.get_session_cookie_args(*args, **kw)
        return Cookie(**kwargs)

    def add_session_cookie(self, *args, **kw):
        cookie = self.create_session_cookie(*args, **kw)
        self.client.cookie_jar.set_cookie(cookie)
        return cookie

    def delete_session_cookie(self, *args, **kw):
        args = self.get_session_cookie_args(*args, **kw)
        args = (args['domain'], args['path'], args['name'])
        self.client.cookie_jar.clear(*args)
        return self
