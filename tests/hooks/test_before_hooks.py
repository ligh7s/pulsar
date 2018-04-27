import flask
import pytest
from voluptuous import Schema, Optional
from pulsar.utils import validate_data
from conftest import CODE_1, HASHED_CODE_1, add_permissions, check_json_response
from pulsar import db
from pulsar.auth.models import Session


@pytest.fixture(autouse=True)
def populate_db(client):
    db.engine.execute(
        f"""INSERT INTO sessions (hash, user_id, csrf_token) VALUES
        ('abcdefghij', 1, '{CODE_1}')
        """)
    db.engine.execute(
        f"""INSERT INTO api_keys (hash, user_id, keyhashsalt) VALUES
        ('abcdefghij', 1, '{HASHED_CODE_1}')
        """)
    yield
    db.engine.execute("DELETE FROM api_keys")


def test_user_session_auth(app, client):
    @app.route('/test_sess')
    def test_session():
        assert flask.g.user_session.hash == 'abcdefghij'
        assert flask.g.user_session.user_agent == 'pulsar-test-client'
        assert flask.g.user_session.ip == '127.0.0.1'
        assert flask.g.user.id == 1
        assert not flask.g.api_key
        return flask.jsonify('completed')

    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['session_hash'] = 'abcdefghij'
    response = client.get('/test_sess', environ_base={
        'HTTP_USER_AGENT': 'pulsar-test-client',
        'REMOTE_ADDR': '127.0.0.1',
        })
    check_json_response(response, 'completed')
    session = Session.from_hash('abcdefghij')
    assert session.user_agent == 'pulsar-test-client'


@pytest.mark.parametrize(
    'user_id, session_hash', [
        ('testings', 'abcdefghij'),
        ('1', 'notarealkey'),
    ])
def test_user_bad_session(app, client, user_id, session_hash):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['session_hash'] = session_hash
    response = client.get('/users/1')
    check_json_response(response, 'Resource does not exist.')


def test_api_key_auth_and_ip_override(app, client):
    add_permissions(app, 'no_ip_history')

    @app.route('/test_api_key')
    def test_api_key():
        assert flask.g.api_key.hash == 'abcdefghij'
        assert flask.g.api_key.user_agent == ''
        assert flask.g.api_key.ip == '0.0.0.0'
        assert flask.g.user.id == 1
        assert not flask.g.user_session
        return flask.jsonify('completed')

    response = client.get('/test_api_key', environ_base={
            'HTTP_USER_AGENT': '',
            'REMOTE_ADDR': '127.0.0.1',
        }, headers={
            'Authorization': f'Token abcdefghij{CODE_1}',
        })
    check_json_response(response, 'completed')


@pytest.mark.parametrize(
    'authorization_header', [
        'Token abcdefgnotarealone',
        'Token abcdefghij123456789012345678901234',
        'Token 1234567',
        'TokenMalformed',
    ])
def test_user_bad_api_key(app, client, authorization_header):
    response = client.get('/users/1', headers={
        'Authorization': authorization_header})
    check_json_response(response, 'Resource does not exist.')


def test_csrf_validation(app, client):
    @app.route('/test_csrf', methods=['POST'])
    @validate_data(Schema({
        Optional('csrf_token', default='NonExistent'): str,
        }))
    def test_csrf(csrf_token):
        assert csrf_token == 'NonExistent'
        return flask.jsonify('completed')

    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['session_hash'] = 'abcdefghij'

    response = client.post('/test_csrf', json=dict(csrf_token=CODE_1))
    resp_data = response.get_json()
    assert 'csrf_token' in resp_data and resp_data['csrf_token'] == CODE_1
    check_json_response(response, 'completed')


def test_unneeded_csrf_validation(app, client):
    @app.route('/test_csrf', methods=['POST'])
    def test_csrf():
        return flask.jsonify('completed')

    response = client.post('/test_csrf', headers={
        'Authorization': f'Token abcdefghij{CODE_1}'})
    resp_data = response.get_json()
    assert 'csrf_token' not in resp_data
    check_json_response(response, 'completed')


@pytest.mark.parametrize(
    'endpoint', [
        '/users/change_password',
        '/not/a/real/route',
    ])
def test_false_csrf_validation_authkey(app, client, endpoint):
    response = client.post(endpoint, headers={
        'Authorization': f'Token abcdefghij{CODE_1}'})
    check_json_response(response, 'Resource does not exist.')


@pytest.mark.parametrize(
    'endpoint', [
        '/users/change_password',
        '/not/a/real/route',
    ])
def test_false_csrf_validation_session(app, client, endpoint):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['session_hash'] = 'abcdefghij'

    response = client.post(endpoint)
    check_json_response(response, 'Invalid authorization key.')


@pytest.mark.parametrize(
    'endpoint', [
        '/users/change_password',
        '/not/a/real/route',
    ])
def test_no_authorization_post(app, client, endpoint):
    response = client.post(endpoint)
    check_json_response(response, 'Resource does not exist.')


def test_bad_data(app, client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['session_hash'] = 'abcdefghij'

    response = client.post('/fake_endpoint', data=b'{a malformed ",json"}')
    check_json_response(response, 'Malformed input. Is it JSON?')