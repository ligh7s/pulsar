from typing import Union

import flask
from flask_sqlalchemy import Model
from sqlalchemy import func
from sqlalchemy.orm.session import make_transient_to_detached

if False:
    from flask import BaseQuery  # noqa
    from sqlalchemy.sql import BinaryExpression  # noqa


class BaseModel(Model):
    """
    This is a custom model for the pulsar project, which adds caching
    and JSON serialization methods to the base model. Subclasses are
    expected to define their serializable attributes, permission restrictions,
    and cache key template with the following class attributes. They are required
    if one wants to cache or serialize data for a model. By default, all "serialize"
    tuples are empty, so only the populated ones need to be defined.

    * ``__cache_key__`` (``str``)
    * ``__serialize__`` (``tuple``)
    * ``__serialize_self__`` (``tuple``)
    * ``__serialize_detailed__`` (``tuple``)
    * ``__serialize_very_detailed__`` (``tuple``)
    * ``__serialize_nested_include__`` (``tuple``)
    * ``__serialize_nested_exclude__`` (``tuple``)
    * ``__permission_detailed__`` (``str``)
    * ``__permission_very_detailed__`` (``str``)

    When a model is serialized, the permissions assigned to a user and the
    permissions listed in the above attributes will determine which properties
    of the model are returned. ``__serialize__`` is viewable to anyone with permission
    to see the resource, ``__serialize_self__`` is viewable by anyone who passes the
    ``belongs_to_user`` function. ``__serialize_detailed__`` and
    ``__serialize_very_detailed__`` are viewable by users with the permission ``str``s
    stored as ``__permission_detailed__`` and ``__permission_very_detailed__``,
    respectively.

    Nested model properties will also be serialized if they are the value of a ``dict``
    or in a ``list``. When nested models are serialized, all attributes listed in
    ``__serialize_nested_exclude__`` will be excluded, while all attributes in
    ``__serialize_nested_include__`` will be included.

    Due to how models are cached, writing out the logic to obtain from cache and,
    if the model wasn't cached, execute a query for every model is tedious and repetitive.
    Generalized functions to abstract those are included in this class, and are
    expected to be utilized wherever possible.
    """

    # Default values

    __cache_key__ = None  # type: str

    __serialize__ = tuple()  # type: tuple
    __serialize_self__ = tuple()  # type: tuple
    __serialize_detailed__ = tuple()  # type: tuple
    __serialize_very_detailed__ = tuple()  # type: tuple
    __serialize_nested_include__ = tuple()  # type: tuple
    __serialize_nested_exclude__ = tuple()  # type: tuple

    __permission_detailed__ = None  # type: str
    __permission_very_detailed__ = None  # type: str

    @property
    def cache_key(self) -> str:
        """
        Default property for cache key which should be overridden if the
        cache key is not formatted with an ID column. If the cache key
        string for the model only takes an {id} param, then this function
        will suffice.

        :return: A ``str`` cache key representing the model
        """
        return self.__cache_key__.format(id=self.id)

    @classmethod
    def from_id(cls,
                id: int, *,
                include_dead: bool = False,
                _404: bool = False,
                asrt: bool = False) -> Union['BaseModel', None]:
        """
        Default classmethod constructor to get an object by its PK ID.
        If the object has a deleted/revoked/expired column, it will compare a
        ``include_dead`` kwarg against it. This function first attempts to load
        an object from the cache by formatting its ``__cache_key__`` with the
        ID parameter, and executes a query if the object isn't cached.
        Can optionally raise a ``_404Exception`` if the object is not queried.

        :param int id: The primary key ID of the object to query for.
        :param bool include_dead: Whether or not to return deleted/revoked/expired objects
        :param _404: Whether or not to raise a _404Exception with the value of _404 and
            the given ID as the resource name if a model is not found
        :param asrt: Whether or not to check for ownership of the model or a permission.
            Can be a boolean to purely check for ownership, or a permission string which
            can override ownership and access the model anyways.

        :return: A ``BaseModel`` model or ``None``
        :raises _404Exception: If ``_404`` is passed and a model is not found, or
            ``asrt`` and ``_404`` are passed and the permission checks fail
        """
        from pulsar import _404Exception
        model = cls.from_cache(
            key=cls.__cache_key__.format(id=id),
            query=cls.query.filter(cls.id == id))
        if model:
            if include_dead or not (
                    getattr(model, 'deleted', False)
                    or getattr(model, 'revoked', False)
                    or getattr(model, 'expired', False)):
                if not asrt or model.belongs_to_user() or flask.g.user.has_permission(asrt):
                    return model
        if _404:
            raise _404Exception(f'{_404} {id}')
        return None

    @classmethod
    def from_cache(cls,
                   key: str, *,
                   query: 'BaseQuery' = None) -> Union['BaseModel', None]:
        """
        Check the cache for an instance of this model and attempt to load
        its attributes from the cache instead of from the database.
        If found, the object is merged into the database session and returned.
        Otherwise, if a query is passed, the query is ran and the result is cached and
        returned. Model returns ``None`` if the object doesn't exist.

        :param str key: The cache key to get
        :param query: The SQLAlchemy query

        :return: The uncached ``BaseModel`` or ``None``
        """
        from pulsar import db, cache
        data = cache.get(key)
        if data and isinstance(data, dict):
            if cls._valid_data(data):
                obj = cls(**data)
                make_transient_to_detached(obj)
                obj = db.session.merge(obj, load=False)
                return obj
            else:
                cache.delete(key)
        if query:
            obj = query.first()
            cache.cache_model(obj)
            return obj
        return None

    @classmethod
    def from_query(cls, *, key, filter=None, order=None):
        """
        Function to get a single object from the database (limit(1), first()).
        Getting the object via the provided cache key will be attempted first; if
        it does not exist, then a query will be constructed with the other
        parameters. The resultant object (if exists) will be cached and returned.

        *The queried model must have a primary key column named ``id`` and a
        ``from_id`` classmethod constructor.*

        :param str key: The cache key to check
        :param filter: A SQLAlchemy expression to filter the query with
        :param order: A SQLAlchemy expression to order the query by

        :return: A ``BaseModel`` object of the ``model`` class, or ``None``
        """
        from pulsar import cache
        cls_id = cache.get(key)
        if not cls_id:
            query = cls._construct_query(cls.query, filter, order)
            model = query.limit(1).first()
            if model:
                if not cache.has(model.cache_key):
                    cache.cache_model(model)
                cache.set(key, model.id)
                return model
            return None
        return cls.from_id(cls_id)

    @classmethod
    def get_many(cls, *, key, filter=None, order=None, required_properties=tuple(),
                 include_dead=False, page=None, limit=None, expr_override=None):
        """
        Abstraction function to get a list of IDs from the cache with a cache
        key, and query for those IDs if the key does not exist. If the query
        needs to be ran, a list will be created from the first element in
        every returned tuple result, like so:
        ``[x[0] for x in cls.query.all()]``

        That list will be converted into models, using the keyword arguments to
        modify which elements are included and which aren't. Pagination is optional
        and ignored if neither page nor limit is set.

        :param str key: The cache key to check (and return if present)
        :param filter: A SQLAlchemy filter expression to be applied to the query
        :param order: A SQLAlchemy order_by expression to be applied to the query
        :param required_properties: Properties required to validate to ``True``
            for a retrieved item to be included in the returned list
        :param bool include_dead: Whether or not to include deleted/revoked/expired models
        :param int page: The page number of results to return
        :param int limit: The limit of results to return, defaults to 50 if page
            is set, otherwise infinite
        :param expr_override: If passed, this will override filter and order, and be
            called verbatim in a ``db.session.execute`` if the cache key does not exist

        :return: A ``list`` of objects belonging to the class this method was called from
        """
        from pulsar import db, cache
        ids = cache.get(key)
        if not ids:
            if expr_override is not None:
                ids = [x[0] for x in db.session.execute(expr_override)]
            else:
                query = cls._construct_query(db.session.query(cls.id), filter, order)
                ids = [x[0] for x in query.all()]
            cache.set(key, ids)

        if page is not None:
            limit = limit or 50
            ids = ids[(page - 1) * limit:]

        models = []
        for id in ids:
            model = cls.from_id(id, include_dead=include_dead)
            if model:
                for prop in required_properties:
                    if not getattr(model, prop, False):
                        break
                else:
                    models.append(model)
                    if limit and len(models) >= limit:
                        break
        return models

    @classmethod
    def _valid_data(cls, data):
        """
        Validate the data returned from the cache by ensuring that it is a dictionary
        and that the returned values match the columns of the object.

        :param dict data: The stored object data to validate

        :return: ``True`` if valid or ``False`` if invalid
        """
        return isinstance(data, dict) and set(data.keys()) == set(cls.__table__.columns.keys())

    @classmethod
    def new(cls, **kwargs):
        """
        Create a new instance of the model, add it to the instance, cache it,
        and return it.

        :param kwargs: The new attributes of the model.
        """
        from pulsar import db, cache
        model = cls(**kwargs)
        db.session.add(model)
        db.session.commit()
        cache.cache_model(model)
        return model

    def count(self, *, key, attribute, filter=None):
        """
        Abstraction function for counting a number of elements. If the
        cache key exists, its value will be returned; otherwise, the
        query will be ran and the resultant count cached and returned.

        :param str key: The cache key to check
        :param attribute: The attribute to count; a model's column
        :param filter: The SQLAlchemy filter expression
        """
        from pulsar import db, cache
        count = cache.get(key)
        if not count:
            query = self._construct_query(db.session.query(func.count(attribute)), filter)
            count = query.first()[0]
            cache.set(key, count)
        return count

    def belongs_to_user(self):
        """
        Function to determine whether or not the model "belongs" to a user
        by comparing against flask.g.user This is meant to be overridden
        by subclasses, and returns False by default (if not overridden).

        :return: ``True`` if "belongs to user", else ``False``
        """
        return False

    def clear_cache(self):
        """Clear the cache key for this model instance."""
        from pulsar import cache
        cache.delete(self.cache_key)

    @staticmethod
    def _construct_query(query: 'BaseQuery',
                         filter: 'BinaryExpression' = None,
                         order: 'BinaryExpression' = None) -> 'BaseQuery':
        """
        Convenience function to save code space for query generations.
        Takes filters and orders and applies them to the query if they are present,
        returning a query ready to be ran.

        :param BaseQuery query: A query that can be built upon
        :param filter: A SQLAlchemy query filter expression
        :param order: A SQLAlchemy query order_by expression

        :return: A Flask-SQLAlchemy ``BaseQuery``
        """
        if filter is not None:
            query = query.filter(filter)
            print(type(filter))
        if order is not None:
            query = query.order_by(order)
        return query
