import pytest

from conftest import CODE_1, CODE_2, CODE_3
from pulsar import cache, db
from pulsar.auth.models import Session


def hex_generator(_):
    return next(HEXES)


def test_new_session(app):
    with app.app_context():
        session = Session.new(2, '127.0.0.2', 'ua-example')
        assert session.ip == '127.0.0.2'
        assert session.user_id == 2


def test_session_collision(app, monkeypatch):
    global HEXES
    HEXES = iter([CODE_2[:10], CODE_3[:10], CODE_3])
    monkeypatch.setattr('pulsar.models.secrets.token_hex', hex_generator)
    with app.app_context():
        session = Session.new(2, '127.0.0.2', 'ua-example')
        assert session.id != CODE_2[:10]
        assert session.csrf_token != CODE_2
        with pytest.raises(StopIteration):
            hex_generator(None)


def test_from_id(app, client):
    session = Session.from_id('abcdefghij')
    assert session.user_id == 1
    assert session.csrf_token == CODE_1


def test_from_id_cached(app, client):
    session = Session.from_id('abcdefghij')
    cache_key = cache.cache_model(session, timeout=60)
    session = Session.from_id('abcdefghij')
    assert session.user_id == 1
    assert session.csrf_token == CODE_1
    assert cache.ttl(cache_key) < 61


def test_from_user(app, client):
    sessions = Session.from_user(1)
    assert len(sessions) == 2
    assert sessions[0].user_id == 1
    assert sessions[0].csrf_token == CODE_1


def test_from_user_cached(app, client):
    cache_key = Session.__cache_key_of_user__.format(user_id=1)
    cache.set(cache_key, ['1234567890'], timeout=60)
    sessions = Session.from_user(1, include_dead=True)
    assert len(sessions) == 1
    assert sessions[0].user_id == 2
    assert sessions[0].csrf_token == CODE_2


def test_from_id_incl_dead(app, client):
    session = Session.from_id('1234567890', include_dead=True)
    assert session.csrf_token == CODE_2


def test_get_nonexistent_session(app, client):
    session = Session.from_id('1234567890')
    assert not session


def test_session_expire_all(app, client):
    Session.expire_all_of_user(1)
    db.session.commit()
    session = Session.from_id('abcdefghij', include_dead=True)
    assert session.expired


def test_session_expire_all_cached(app, client):
    session = Session.from_id('abcdefghij')
    cache_key = cache.cache_model(session, timeout=60)
    assert cache.ttl(cache_key) < 61

    Session.expire_all_of_user(1)
    db.session.commit()
    session = Session.from_id('abcdefghij', include_dead=True)
    assert session.expired is True
    assert cache.ttl(cache_key) > 61


def test_session_is_expired_not_persistent(app, client):
    db.session.execute(
        "UPDATE sessions SET last_used = NOW() - INTERVAL '31 MINUTES', persistent = 'f'")
    db.session.commit()
    session = Session.from_id('abcdefghij')
    assert not session.expired
    assert session.is_expired()
    session = Session.from_id('abcdefghij', include_dead=True)
    assert session.expired


@pytest.mark.parametrize(
    'code, expired', [
        ('abcdefghij', False),
        ('1234567890', True),
        ('0987654321', True),
        ('bcdefghijk', False),
        ('cdefghijkl', False),
    ])
def test_session_expiry(app, client, code, expired):
    session = Session.from_id(code, include_dead=True)
    assert session.is_expired() is expired
