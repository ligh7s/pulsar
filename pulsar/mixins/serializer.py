import inspect
from typing import Dict, Union
from pulsar.mixins.single_pk import SinglePKMixin

import flask


class Attribute:
    """
    A serializable attribute for a model. This is where the attribute filtering
    and permissioning happens.
    """

    def __init__(self,
                 permission: str = None,
                 self_access: bool = True,
                 default: bool = True,
                 nested: Union[bool, tuple] = True) -> None:
        """
        :param permission:  The permission needed to serialize this attribute
                            (``None`` means no permission necessary)
        :param self_access: Whether or not a user who "owns" the object can access it
                            (will bypass permission check)
        :param default:     Whether or not to serialize this permission by default
        :param nested:      Whether or not to serialize this permission when the nested
                            kwarg filter is passed. This is separated from filters for
                            convenience.
        :param filter:      A filter kwarg that can be included in the Serializer's
                            serialize command to forcibly include or exclude this attribute,
                            provided all other criteria are met. The value of the kwarg
                            will be inspected; ``True`` means include, ``False`` means exclude.
        """
        self.permission = permission
        self.self_access = self_access
        self.default = default
        self.nested = nested

    def get_value(self, name, obj, nested):
        """
        Get the attribute of a object, or a null value if the serialization kwargs
        and/or requesting user don't meet the necessary requirements.
        """
        if not self.can_serialize(name, obj, nested):
            return None
        val = getattr(obj, name)
        if isinstance(val, SinglePKMixin):
            nested = self.nested if isinstance(self.nested, tuple) else True
            return val.serialize(nested=nested)
        elif isinstance(val, list) and any(isinstance(v, SinglePKMixin) for v in val):
            nested = self.nested if isinstance(self.nested, tuple) else True
            return [obj.serialize(nested=nested)
                    for obj in val if isinstance(obj, SinglePKMixin)]
        return val

    def can_serialize(self, name, obj, nested):
        has_permission = not self.permission or (
            flask.g.user and flask.g.user.has_permission(self.permission))
        has_self_access = self.self_access and obj.belongs_to_user()
        nested_bypass = self.nested is True or nested is False
        nested_filter = isinstance(nested, tuple) and name not in nested
        return (has_permission or has_self_access) and nested_bypass and not nested_filter


class Serializer:
    """
    Intended to be passed into model arguments as a __serializer__ attr.
    TODO: More documentation.
    """

    @classmethod
    def serialize(cls, obj, nested=False):
        """
        This function takes the attributes in the serializer and adds them to
        the serialized dictionary, if they match the passed kwarg criteria and
        user permissions.
        """
        data = {name: attr.get_value(name, obj, nested)
                for name, attr in cls.attributes().items()}
        return data if not all(v is None for v in data.values()) else None

    @classmethod
    def attributes(cls) -> Dict[str, Attribute]:
        attrs = inspect.getmembers(cls, lambda a: not inspect.isroutine(a))
        return {name: attr for name, attr in attrs if isinstance(attr, Attribute)}
