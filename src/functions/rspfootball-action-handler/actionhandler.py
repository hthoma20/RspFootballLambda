import logging
import os

from boto3.dynamodb.conditions import Attr
from pydantic.error_wrappers import ValidationError

import rsputil
import rspmodel

import handlers

def lambda_handler(event, context):
    
    rsputil.configure_logger()

    body = rsputil.get_event_body(event)
    
    if body is None:
        return rsputil.api_client_error("Couldn't read event body")
    
    try:
        request = rspmodel.ActionRequest(**body)
    except ValidationError as e:
        print(e)
        print("\n\n\n\n\n\n\n")
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
        game.result = []
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
    handlers.TouchbackChoiceActionHandler(),
    handlers.PlayCallActionHandler(),
    handlers.ShortRunActionHandler(),
    handlers.LongRunActionHandler(),
    handlers.LongRunRollActionHandler(),
    handlers.SackActionHandler(),
    handlers.PatChoiceActionHandler(),
    handlers.ExtraPointKickActionHandler(),
    handlers.TwoPointConversionActionHandler(),
    handlers.FumbleActionHandler()
]

# mutate the game in place
# raise IllegalActionException if the action is illegal
def process_action(game, player, action):
    for handler in ACTION_HANDLERS:
        if (game.state in handler.states) and (type(action) in handler.actions):
            logging.debug(f'init game: {game}')
            logging.info(f'selected handler: {type(handler).__name__}')
            logging.debug(f'handled game: {game}')
            handler.handle_action(game, player, action)
            return
    
    raise Exception(f"No handler found for action {type(action)} in state {game.state}")

