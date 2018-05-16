from typing import Union

from voluptuous import Invalid

from pulsar.permissions.validators import *  # noqa
from pulsar.users.validators import *  # noqa


def bool_get(val: Union[bool, str, None]):
    """
    Takes a string value and returns a boolean based on the input, since GET requests
    always come as strings. '1' and 'true' return True, while '0' and 'false'
    return False. Any other input raises an Invalid exception.

    :param str val: The value to evaluate.
    """
    if isinstance(val, bool):
        return val
    elif isinstance(val, str):
        if val == '1' or val.lower() == 'true':
            return True
        elif val == '0' or val.lower() == 'false':
            return False
    raise Invalid('boolean must be "1", "true", "0", or "false" (case insensitive)')
