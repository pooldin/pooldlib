from pooldlib.postgresql import db


class KeyValueMixin(object):
    key = db.Column(db.String(64), nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)


class MetadataMixin(object):
    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            pass

        value = self._get_meta_value(name)
        if not value:
            msg = "'%s' object has no attribute '%s'"
            msg %= (self.__class__, name)
            raise AttributeError(msg)
        return value

    def _get_meta_value(self, key):
        # NOTE :: Instance level caching of metadata keys
        # NOTE :: might be smart here...
        metadata = object.__getattribute__(self, 'metadata')
        value = [m.value for m in metadata if m.key == key]
        if not value:
            return None
        return value[0]
