import os
import time

import boto3

import rsputil

def lambda_handler(event, context):
    body = rsputil.get_event_body(event)
    
    if body is None:
        return rsputil.api_client_error("Couldn't read event body")
    
    try:
        game_id = body['gameId']
        client_version = body['version']
    except KeyError as e:
        return rsputil.api_client_error(f'Missing required attribute: {e}')

    max_poll_time = float(os.environ['MAX_POLL_TIME'])
    poll_interval = float(os.environ['POLL_INTERVAL'])

    stop_time = time.time() + max_poll_time

    game = rsputil.get_game(game_id)
    if game is None:
        return rsputil.api_client_error('Game not found')

    while (time.time() < stop_time) and (client_version >= game.version):
        time.sleep(poll_interval)
        game = rsputil.get_game(game_id)

    return rsputil.api_success(game.dict())

    