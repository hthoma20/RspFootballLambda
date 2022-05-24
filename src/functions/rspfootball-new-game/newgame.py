import os
import json

import boto3
from boto3.dynamodb.conditions import Attr

import rsputil
from rspmodel import Game, Play, Player, State

def lambda_handler(event, context):
    
    body = rsputil.get_event_body(event)

    try:
        user = body['user']
        game_id = body['gameId']
    except KeyError as e:
        return rsputil.api_client_error(f"Invalid request, missing attribute: {e}")

    game = new_game(game_id)
    game.players['home'] = user

    try:
        
        if os.environ['ALLOW_OVERWRITES'] == 'true':
            condition = None
        else:
            condition = Attr('gameId').not_exists()
        
        rsputil.store_game(game, condition)

    except rsputil.ConditionalCheckFailedException:
        return rsputil.api_client_error('Invalid gameId: game with id already exists')
    
    return rsputil.api_success(game.dict())


def new_game(game_id):    
    return Game(
        gameId = game_id,
        version = 0,
        players = {
            'home': None,
            'away': None,
        },
        state = State.COIN_TOSS,
        score = {
            'home': 0,
            'away': 0
        },
        penalties = {
            'home': 2,
            'away': 2
        },
        possession = None,
        firstKick = None,
        ballpos = 35,
        playCount = 1,
        down = 1,
        play = None,
        rsp = {
            'home': None,
            'away': None
        },
        roll = [],
        actions = {
            'home': ['RSP'],
            'away': ['RSP']
        },
        result = []
    )