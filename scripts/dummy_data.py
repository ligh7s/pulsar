#!/usr/bin/env python3

import psycopg2
from conftest import (CODE_1, CODE_2, CODE_3, HASHED_CODE_1, HASHED_CODE_2,
                      HASHED_CODE_3, HASHED_PASSWORD_1, HASHED_PASSWORD_2)

conn = psycopg2.connect('postgresql:///pulsar')
cursor = conn.cursor()

cursor.execute("DELETE FROM permissions")
cursor.execute("DELETE FROM invites")
cursor.execute("DELETE FROM api_permissions")
cursor.execute("DELETE FROM api_keys")
cursor.execute("DELETE FROM sessions")
cursor.execute("DELETE FROM users")


cursor.execute(
    f"""INSERT INTO users (id, username, passhash, email, invites, inviter_id) VALUES
    (1, 'lights', '{HASHED_PASSWORD_1}', 'lights@puls.ar', 1, NULL),
    (2, 'paffu', '{HASHED_PASSWORD_2}', 'paffu@puls.ar', 0, 1)
    """)
cursor.execute("ALTER SEQUENCE users_id_seq RESTART WITH 3")
cursor.execute(
    """INSERT INTO permissions (user_id, permission) VALUES
    (1, 'sample_perm_one'),
    (1, 'sample_perm_two'),
    (1, 'sample_perm_three'),
    (1, 'sample_permission')
    """)
cursor.execute(
    f"""INSERT INTO invites (inviter_id, email, code, time_sent, active) VALUES
    (1, 'bright@puls.ar', '{CODE_1}', NOW(), 't'),
    (1, 'bitsu@puls.ar', '{CODE_2}', NOW(), 'f'),
    (1, 'bright@quas.ar', '{CODE_3}', '2018-03-25 01:09:35.260808+00', 't')
    """)
cursor.execute(
    f"""INSERT INTO api_keys (user_id, hash, keyhashsalt, active) VALUES
    (1, 'abcdefghij', '{HASHED_CODE_1}', 't'),
    (1, '0987654321', '{HASHED_CODE_3}','t'),
    (2, '1234567890', '{HASHED_CODE_2}', 'f')
    """)
cursor.execute(
    """INSERT INTO permissions (user_id, permission) VALUES
    (1, 'view_api_keys'),
    (1, 'revoke_api_keys'),
    (1, 'manipulate_permissions'),
    (1, 'list_permissions'),
    (1, 'change_password')
    """)
cursor.execute(
    """INSERT INTO api_permissions (api_key_hash, permission) VALUES
    ('abcdefghij', 'sample_permission'),
    ('abcdefghij', 'sample_2_permission'),
    ('abcdefghij', 'sample_3_permission')
    """)
cursor.execute(
    f"""INSERT INTO sessions (hash, user_id, csrf_token) VALUES
    ('abcdefghij', 1, '{CODE_1}'),
    ('fc087ea0e6', 1, '8557e86c3d16dc54be6f5468')
    """)

conn.commit()
conn.close()