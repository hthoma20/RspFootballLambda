import os

import boto3
from boto3.dynamodb.conditions import Attr
from pydantic.error_wrappers import ValidationError

import rsputil
import rspmodel
from rspmodel import KickoffChoice, KickoffElectionChoice, RspChoice, State, TouchbackChoice

import handlers

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

        if request.action.name not in game.actions[player]:
            return rsputil.api_client_error('Action not allowed')

        version = game.version
        game.result = None
        game.actions = {'home': ['POLL'], 'away': ['POLL']}

        try:
            process_action(game, player, request.action)
        except handlers.IllegalActionException as e:
            return rsputil.api_client_error(f"Illegal action: {e}")

        try:
            game.version = version + 1
            rsputil.store_game(game, condition=Attr('version').eq(version))
            return rsputil.api_success(game.dict())
        except rsputil.ConditionalCheckFailedException:
            continue
        
    return rsputil.api_server_fault("Failed to update game")


ACTION_HANDLERS = [
    handlers.CoinTossActionHandler(),
    handlers.KickoffElectionActionHandler(),
    handlers.KickoffChoiceActionHandler(),
    handlers.KickoffActionHandler(),
    handlers.OnsideKickActionHandler(),
    handlers.KickReturnActionHandler(),
    handlers.KickReturn6ActionHandler(),
    handlers.KickReturn1ActionHandler(),
    handlers.TouchbackChoiceActionHandler()
]

# mutate the game in place
# raise IllegalActionException if the action is illegal
def process_action(game, player, action):
    for handler in ACTION_HANDLERS:
        if (game.state in handler.states) and (type(action) in handler.actions):
            handler.handle_action(game, player, action)
            return
    
    raise Exception(f"No handler found for action {type(action)} in state {game.state}")

