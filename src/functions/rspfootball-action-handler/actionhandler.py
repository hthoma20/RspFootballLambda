import base64
import json
import os
import random

import boto3
from boto3.dynamodb.conditions import Attr
from pydantic.error_wrappers import ValidationError

import rsputil
import rspmodel
from rspmodel import KickoffChoice, KickoffElectionChoice, RspChoice, State

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
        game.result = None

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
    
    elif type(action) is rspmodel.KickoffElectionAction:
        game.state = State.KICKOFF_CHOICE

        if action.choice == KickoffElectionChoice.KICK:
            kicker = player
            reciever = rsputil.get_opponent(player)
        else: # choice is RECIEVE
            kicker = rsputil.get_opponent(player)
            reciever = player
        
        game.firstKick = kicker
        game.possession = kicker
        game.actions[kicker] = ['KICKOFF_CHOICE']
        game.actions[reciever] = ['POLL']
    
    elif type(action) is rspmodel.KickoffChoiceAction:
        
        if action.choice == KickoffChoice.REGULAR:
            game.state = State.KICKOFF
        else: # choice is ONSIDE
            game.state = State.ONSIDE_KICK
        
        game.actions[player] = ['ROLL']
        game.actions[opponent] = ['POLL']

    elif type(action) is rspmodel.RollAction:
        process_roll_action(game, player, action.count)


def process_roll_action(game, player, count: int):

    if game.state in [State.KICKOFF, State.ONSIDE_KICK]:
        required_count = 3 if game.state == State.KICKOFF else 2
        require_die_count(required_count, count, game.state)

        roll = roll_dice(count)
        game.result = rspmodel.RollResult(roll=roll)

        game.ballpos += 5 * sum(roll)

        switch_possession(game)

        if game.ballpos <= -10:
            game.ballpos = 20
            game.state = State.PLAY_CALL
            game.actions[game.possession] = ['CALL_PLAY']
            game.actions[player] = ['POLL']

        elif game.ballpos <= 0:
            game.state = State.TOUCHBACK_CHOICE
            game.actions[game.possession] = ['TOUCHBACK_CHOICE']
            game.actions[player] = ['POLL']

        else:
            game.state = State.KICK_RETURN
            game.actions[game.possession] = ['ROLL']
            game.actions[player] = ['POLL']
    
    else:
        raise IllegalActionException('Invalid state for roll - this represents an unexpected state')


def switch_possession(game):
    game.possession = rsputil.get_opponent(game.possession)
    game.ballpos = 100 - game.ballpos

def require_die_count(required, count, description):
    if count != required:
        raise IllegalActionException(f'Must roll {required} dice for {description}')

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


def roll_die():
    return random.randint(1, 6)

def roll_dice(count):
    return [roll_die() for _ in range(count)]

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
