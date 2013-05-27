from . import config


def authenticate(username, password):
    return {'result': True, 'difficulty': config.target_difficulty,
            'username': username}


def share_accepted(username):
    return True


def block_found(username, height):
    return True
