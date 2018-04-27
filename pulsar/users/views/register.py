import pytz
import flask
from datetime import datetime
from sqlalchemy.sql import func
from voluptuous import Schema
from voluptuous.validators import Email, Match

from . import bp
from pulsar.invites.models import Invite
from pulsar import db, APIException
from pulsar.utils import USERNAME_REGEX, PASSWORD_REGEX, validate_data
from pulsar.users.models import User
from pulsar.users.schemas import user_schema

app = flask.current_app

registration_schema = Schema({
    'username': Match(USERNAME_REGEX, msg=(
        'Usernames must start with an alphanumeric character and can only contain '
        'alphanumeric characters, underscores, hyphens, and spaces.')),
    'password': Match(PASSWORD_REGEX, msg=(
        'Password must be 12 or more characters and contain at least 1 letter, '
        '1 number, and 1 special character.')),
    'email': Email(),
}, required=True)


@bp.route('/register/<code>', methods=['POST'])
@bp.route('/register', methods=['POST'])
@validate_data(registration_schema)
def register(username, password, email, code=None):
    if app.config['REQUIRE_INVITE_CODE']:
        validate_invite_code(code)
    validate_username(username)

    user = User(
        username=username,
        password=password,
        email=email)
    db.session.add(user)
    db.session.commit()
    return user_schema.jsonify(user)


def validate_username(username):
    """
    Ensures that a username is not taken and that it matches the required length
    and doesn't contain any invalid characters.
    """
    if (User.query.filter(func.lower(User.username) == username.lower()).one_or_none()):
        raise APIException(f'Another user already has the username `{username}`.')


def validate_invite_code(code):
    """
    Check an invite code against existing invite codes;
    Raises an exception if the code isn't valid.
    """
    invite = Invite.from_code(code)
    if invite and not invite.invitee_id:
        time_since_usage = datetime.utcnow().replace(tzinfo=pytz.utc) - invite.time_sent
        if time_since_usage.total_seconds() < app.config['INVITE_LIFETIME']:
            return
    if code:
        raise APIException(f'{code} is not a valid invite code.')
    raise APIException(f'An invite code is required for registration.')