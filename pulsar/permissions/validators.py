from collections import defaultdict
from typing import Dict, List, Tuple

import flask
from voluptuous import Invalid

from pulsar import APIException
from pulsar.models import User, UserPermission
from pulsar.utils import get_all_permissions


def permissions_list(perm_list: List[str]) -> List[str]:
    """
    Validates that every permission in the list is a valid permission.

    :param perm_list: A list of permissions encoded as ``str``

    :return:          The inputted perm_list
    :raises Invalid:  If a permission in the list isn't valid or input isn't a list
    """
    permissions = get_all_permissions()
    invalid = []
    if isinstance(perm_list, list):
        for perm in perm_list:
            if perm not in permissions:
                invalid.append(perm)
    else:
        raise Invalid('Permissions must be in a list,')
    if invalid:
        raise Invalid(f'The following permissions are invalid: {", ".join(invalid)},')
    return perm_list


def permissions_list_of_user(perm_list: List[str]) -> List[str]:
    """
    Takes a list of items and asserts that all of them are in the permissions list of
    a user.

    :param perm_list: A list of permissions encoded as ``str``

    :return:          The input perm_list
    :raises Invalid:  If the user does not have a permission in the list
    """
    if isinstance(perm_list, list):
        for perm in perm_list:
            if perm not in flask.g.user.permissions:
                break
        else:
            return perm_list
    raise Invalid('permissions must be in the user\'s permissions list')


def permissions_dict(permissions: dict) -> dict:
    """
    Validates that a dictionary contains valid permission name keys
    and has boolean values.

    :param permissions:    Dictionary of permissions and booleans

    :return:         The input value
    :raises Invalid: A permission name is invalid or a value isn't a bool
    """
    all_permissions = get_all_permissions()
    if isinstance(permissions, dict):
        for perm_name, action in permissions.items():
            if not isinstance(action, bool):
                raise Invalid('permission actions must be booleans')
            elif perm_name not in all_permissions and action is True:
                # Do not disallow removal of non-existent permissions.
                raise Invalid(f'{perm_name} is not a valid permission')
    else:
        raise Invalid('input value must be a dictionary')
    return permissions


def check_permissions(user: User,  # noqa: C901
                      permissions: Dict[str, bool]) -> Tuple[List[str], List[str], List[str]]:
    """
    Validates that the provided permissions can be applied to the user.
    Permissions can be added if they were previously taken away or aren't
    a permission given to the user class. Permissions can be removed if
    were specifically given to the user previously, or are included in their userclass.

    :param user:          The recipient of the permission changes
    :param permissions:   A dictionary of permission changes, with permission name
                          and boolean (True = Add, False = Remove) key value pairs
    :return:              A tuple of lists, one of permissions to add, another with
                          permissions to ungrant, and another of permissions to remove
    :raises APIException: If the user already has a to-add permission or
                          lacks a to-delete permission
    """
    add: List[str] = []
    ungrant: List[str] = []
    delete: List[str] = []
    errors: Dict[str, List[str]] = defaultdict(list)

    uc_permissions: List[str] = user.user_class.permissions
    user_permissions: Dict[str, bool] = UserPermission.from_user(user.id)

    for perm, active in permissions.items():
        if active is True:
            if perm in user_permissions:
                if user_permissions[perm] is False:
                    delete.append(perm)
                    add.append(perm)
            elif perm not in uc_permissions:
                add.append(perm)
            if perm not in add + delete:
                errors['add'].append(perm)
        else:
            if perm in user_permissions and user_permissions[perm] is True:
                delete.append(perm)
            if perm in uc_permissions:
                ungrant.append(perm)
            if perm not in delete + ungrant:
                errors['delete'].append(perm)

    if errors:
        message = []
        if 'add' in errors:
            message.append('The following permissions could not be added: {}.'.format(
                ", ".join(errors['add'])))
        if 'delete' in errors:
            message.append('The following permissions could not be deleted: {}.'.format(
                ", ".join(errors['delete'])))
        raise APIException(' '.join(message))

    return add, ungrant, delete
