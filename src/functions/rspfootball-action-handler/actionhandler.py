import base64
import json
import os

import boto3
from boto3.dynamodb.conditions import Attr
from pydantic.error_wrappers import ValidationError

import rsputil
import rspmodel
from rspmodel import RspChoice, State

def lambda_handler(event, context):
    
    body = rsputil.get_event_body(event)
    
    if body is None:
        return rsputil.api_client_error("Couldn't read event body")
    
    try:
        request = rspmodel.ActionRequest(**body)
    except ValidationError as e:
        return rsputil.api_client_error(f'Illegal request: {e}')


    attempts_remaining = int(os.environ['MAX_UPDATE_ATTEMPTS'])
    while attempts_remaining > 0:
        attempts_remaining -= 1
        
        game = rsputil.get_game(request.gameId)
        if game is None:
            return rsputil.api_client_error('Game not found')

        player = rsputil.get_player(game, request.user)
        if player is None:
            return rsputil.api_client_error('Player not in game')

        version = game.version

        try:
            process_action(game, player, request.action)
        except IllegalActionException as e:
            return rsputil.api_client_error(f"Illegal action: {e}")

        try:
            game.version = version + 1
            rsputil.store_game(game, condition=Attr('version').eq(version))
            return rsputil.api_success(game.dict())
        except rsputil.ConditionalCheckFailedException:
            continue
        
    return rsputil.api_server_fault("Failed to update game")


class IllegalActionException(Exception):
    pass

# mutate the game in place
# raise IllegalActionException if the action is illegal
def process_action(game, player, action):

    if action.name not in game.actions[player]:
        raise IllegalActionException('Action not allowed')

    opponent = rsputil.get_opponent(player)

    if type(action) is rspmodel.RspAction:
        game.rsp[player] = action.choice

        if game.rsp[opponent]:
            process_rsp_complete(game, player)
        else:
            game.actions[player] = ['POLL']
            game.actions[opponent] = ['RSP']

def process_rsp_complete(game, player):
    winner = get_rsp_winner(game.rsp)

    game.result = rspmodel.RspResult(
        home = game.rsp['home'],
        away = game.rsp['away']
    )

    if game.state == State.COIN_TOSS:
        # during the cointoss a tie is a redo
        if winner is None:
            game.rsp = {'home': None, 'away': None}
            game.actions['home'] = ['RSP']
            game.actions['away'] = ['RSP']
        else:
            game.state = State.KICKOFF_ELECTION
            game.actions[winner] = ['KICKOFF_ELECTION']
            game.actions[rsputil.get_opponent(winner)] = ['POLL']

def get_rsp_winner(rsp):
    if rsp['home'] == rsp['away']:
        return None
    
    wins = {
        RspChoice.ROCK: RspChoice.SCISSORS,
        RspChoice.SCISSORS: RspChoice.PAPER,
        RspChoice.PAPER: RspChoice.ROCK
    }

    if wins[rsp['home']] == rsp['away']:
        return 'home'
    return 'away'
