import flask
from werkzeug.contrib.cache import RedisCache


class Cache(RedisCache):
    """
    A custom implementation of werkzeug's RedisCache.
    This modifies and adds a few functions to RedisCache.

    All cache key get/set/inc/del are logged in a global variable for
    debugging purposes.
    """

    def __init__(self):
        # Override the RedisCache params we don't need.
        pass

    def init_app(self, app):
        # Required flask extension method.
        super().__init__(**app.config['REDIS_PARAMS'])

    def inc(self, key, delta=1, timeout=None):
        """
        Increment a cache key if it exists, otherwise create it
        and optionally set a timeout.

        :param str key: The cache key to increment
        :param int delta: How much to increment the cache key by
        :param int timeout: If the cache key is newly created,
            how long to persist the key for
        """
        key = key.lower()
        value = super().inc(key, delta)
        if timeout and value == delta:
            self._client.expire(self.key_prefix + key, timeout)
        flask.g.cache_keys['inc'].add(key)
        return value

    def get(self, key):
        """
        Look up key in the cache and return the value for it. Key is
        automatically lower-cased.

        :param key: the key to be looked up.
        :returns: The value if it exists and is readable, else ``None``.
        """
        key = key.lower()
        value = super().get(key)
        if value:
            flask.g.cache_keys['get'].add(key)
        return value

    def set(self, key, value, timeout=None):
        """
        Add a new key/value to the cache (overwrites value,
        if key already exists in the cache). Keys are automatically
        lower-cased.

        :param str key: The key to set
        :param value: The value for the key
        :param int timeout: The cache timeout for the key in seconds
            (if not specified, it uses the default timeout).
            A timeout of 0 indicates that the cache never expires.

        :return: ``True`` if key has been updated, ``False`` for backend
            errors. Pickling errors, however, will raise a subclass of
            pickle.PickleError.
        """
        key = key.lower()
        flask.g.cache_keys['set'].add(key)
        return super().set(key, value, timeout)

    def delete(self, key):
        """
        Delete key from the cache.

        :param str key: The key to delete
        :return: A ``bool`` for whether the key existed and has been deleted
        """
        key = key.lower()
        result = super().delete(key)
        if result:
            flask.g.cache_keys['delete'].add(key)
        return result

    def ttl(self, key):
        """
        Return the time to live (time until expiry) for a cache key.

        :return: The seconds left until a key expires (``int``)
        """
        return self._client.ttl((self.key_prefix + key).lower())

    def cache_model(self, model, timeout=None):
        """
        Cache a SQLAlchemy model. Does nothing when ``model`` is ``None``.

        :param Model model: The SQLAlchemy ``Model`` to cache
        :param int timeout: The number of seconds to persist the key for
        """
        from pulsar import PulsarModel
        if model and isinstance(model, PulsarModel):
            data = {}
            for attr in model.__table__.columns.keys():
                data[attr] = getattr(model, attr, None)
            self.set(model.cache_key, data, timeout or self.default_timeout)
            return model.cache_key
