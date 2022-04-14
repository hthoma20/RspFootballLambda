import base64
import json
import os

import boto3
from boto3.dynamodb.conditions import Attr

import rsputil

def lambda_handler(event, context):
    
    body = rsputil.get_event_body(event)
    
    if body is None:
        return rsputil.api_client_error("Couldn't read event body")
    
    try:
        gameId = body['gameId']
        user = body['user']
        action = body['action']
    except KeyError as e:
        return rsputil.api_client_error(f'Missing required attribute: {e}')


    attempts_remaining = int(os.environ['MAX_UPDATE_ATTEMPTS'])
    while attempts_remaining > 0:
        attempts_remaining -= 1
        
        game = rsputil.get_game(gameId)
        if game is None:
            return rsputil.api_client_error('Game not found')

        player = rsputil.get_player(game, user)
        if player is None:
            return rsputil.api_client_error('Player not in game')

        version = game['version']

        try:
            process_state(game, player, action)
        except IllegalActionException:
            return rsputil.api_client_error("Illegal action")

        try:
            game['version'] = version + 1
            rsputil.store_game(game, condition=Attr('version').eq(version))
            return rsputil.api_success(game)
        except rsputil.ConditionalCheckFailedException:
            continue
        
    return rsputil.api_server_fault("Failed to update game")


class IllegalActionException(Exception):
    pass

# mutate the game in place
# raise IllegalActionException if the action is illegal
def process_state(game, player, action):
    game['ballpos'] += 10
