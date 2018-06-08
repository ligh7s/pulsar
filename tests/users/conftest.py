import pytest

from conftest import CODE_1, CODE_2, CODE_3, HASHED_CODE_1, HASHED_CODE_3
from pulsar import db


@pytest.fixture(autouse=True)
def populate_db(client):
    db.engine.execute(
        f"""INSERT INTO invites (inviter_id, email, code, time_sent, expired) VALUES
        (1, 'bright@puls.ar', '{CODE_1}', NOW(), 'f'),
        (1, 'bitsu@puls.ar', '{CODE_2}', NOW(), 't'),
        (1, 'bright@quas.ar', '{CODE_3}', '2018-03-25 01:09:35.260808+00', 'f')
        """)
    db.engine.execute(
        f"""INSERT INTO api_keys (user_id, hash, keyhashsalt, revoked, permissions) VALUES
        (1, 'abcdefghij', '{HASHED_CODE_1}', 'f',
         '{{"sample_permission", "sample_2_permission", "sample_3_permission"}}'),
        (2, 'bcdefghijk', '{HASHED_CODE_3}', 'f', '{{}}')""")
