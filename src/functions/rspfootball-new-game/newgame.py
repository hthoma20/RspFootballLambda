import os
import json

import boto3
from boto3.dynamodb.conditions import Attr

import rsputil

def lambda_handler(event, context):
    
    body = rsputil.get_event_body(event)

    try:
        user = body['user']
        game_id = body['gameId']
    except KeyError as e:
        return rsputil.api_client_error(f"Invalid request, missing attribute: {e}")

    game = new_game(game_id)
    game['players']['home'] = user

    try:
        
        if os.environ['ALLOW_OVERWRITES'] == 'true':
            condition = None
        else:
            condition = Attr('gameId').not_exists()
        
        rsputil.store_game(game, condition)

    except rsputil.ConditionalCheckFailedException:
        return rsputil.api_client_error('Invalid gameId: game with id already exists')
    
    return {
        'statusCode': 200,
        'body': json.dumps(game)
    }


def new_game(game_id):    
    return {
        'gameId': game_id,
        'version': 0,
        'players': {
            'home': None,
            'away': None,
        },
        'state': 'RSP',
        'score': {
            'home': 0,
            'away': 0
        },
        'penalties': {
            'home': 2,
            'away': 2
        },
        'ballpos': 35,
        'playNum': 1,
        'down': 1,
        'currentPlay': 'COIN_TOSS',
        'rsp': {
            'home': None,
            'away': None
        },
        'roll': [],
        'actions': {
            'home': 'RSP',
            'away': 'RSP'
        }
    }