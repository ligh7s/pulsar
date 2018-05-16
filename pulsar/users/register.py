from typing import Optional as TOptional

import flask
from voluptuous import Optional, Schema
from voluptuous.validators import Email, Match

from pulsar import PASSWORD_REGEX
from pulsar.models import User
from pulsar.utils import validate_data
from pulsar.validators import val_invite_code, val_username

from . import bp

app = flask.current_app

registration_schema = Schema({
    'username': val_username,
    'password': Match(PASSWORD_REGEX, msg=(
        'Password must be 12 or more characters and contain at least 1 letter, '
        '1 number, and 1 special character.')),
    'email': Email(),
    Optional('code', default=None): str,
}, required=True)


@bp.route('/register', methods=['POST'])
@validate_data(registration_schema)
def register(username: str,
             password: str,
             email: str,
             code: TOptional[str]) -> 'flask.Response':
    """
    Creates a user account with the provided credentials.
    An invite code may be required for registration.

    .. :quickref: User; Register a new user.

    **Example request**:

    .. sourcecode:: http

       POST /register HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

       {
         "username": "lights",
         "password": "y-&~_Wbt7wjkUJdY<j-K",
         "email": "lights@pul.sar",
         "code": "my-invite-code"
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
           "username": "lights"
         }
       }

    :json username: Desired username: must start with an alphanumeric
        character and can only contain alphanumeric characters,
        underscores, hyphens, and periods.
    :json password: Desired password: must be 12+ characters and contain
        at least one letter, one number, and one special character.
    :json email: A valid email address to receive the confirmation email,
        as well as account or security related emails in the future.
    :json code: (Optional) An invite code from another member. Required
        for registration if the site is invite only, otherwise ignored.

    :>jsonarr string username: username the user signed up with

    :statuscode 200: registration successful
    :statuscode 400: registration unsuccessful
    """
    val_invite_code(code)
    user = User.new(
        username=username,
        password=password,
        email=email)
    return flask.jsonify({'username': user.username})
