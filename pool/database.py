from __future__ import absolute_import, unicode_literals

import datetime

from pool import config


def authenticate(username, password):
    cur = config.db_connection.cursor()
    cur.execute("SELECT user_id, difficulty FROM miner "
                "WHERE username=%s and password=%s",
                (username, password))
    result = cur.fetchone()
    cur.close()
    config.db_connection.commit()
    if not result:
        return {'result': False}
    return {'result': True, 'id': result[0], 'difficulty': result[1],
            'username': username}


def share_accepted(user_id):
    cur = config.db_connection.cursor()
    cur.execute("SELECT id FROM round ORDER BY created_at DESC LIMIT 1")
    result = cur.fetchone()
    round_id = result[0]
    cur.execute("SELECT id FROM share_data WHERE round_id=%s AND user_id=%s",
                (result[0], user_id))
    result = cur.fetchone()
    if not result:
        cur.execute("INSERT INTO share_data"
                    "(round_id, user_id, count, created_at) "
                    "VALUES(%s, %s, %s, NOW())", (round_id, user_id, 1))
    else:
        cur.execute("UPDATE share_data set count=count+1 "
                    "WHERE round_id=%s and user_id=%s", (round_id, user_id))
    cur.close()
    config.db_connection.commit()
    return True


def block_found(user_id, height):
    cur = config.db_connection.cursor()
    cur.execute("SELECT id from round WHERE height=%s", (height,))
    result = cur.fetchone()
    cur.execute("INSERT INTO found_blocks"
                "(user_id, round_id, created_at) "
                "VALUES(%s, %s, %s)",
                (user_id, result[0], datetime.datetime.now()))
    cur.close()
    config.db_connection.commit()
    return True


def start_round(height):
    cur = config.db_connection.cursor()
    cur.execute("SELECT id from round WHERE height=%s", (height,))
    result = cur.fetchone()
    if not result:
        cur.execute("INSERT INTO round(height, created_at) "
                    "VALUES(%s, NOW())", (height,))

    cur.close()
    config.db_connection.commit()
    return True
