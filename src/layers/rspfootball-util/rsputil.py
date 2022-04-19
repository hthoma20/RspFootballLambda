import base64
import decimal
import json

import boto3

from rspmodel import Game

def get_event_body(event):
    if 'body' not in event:
        return None
    
    body = event['body']
    
    if 'isBase64Encoded' in event and event['isBase64Encoded']:
        body = base64.b64decode(body)
    
    if type(body) in [str, bytes]:
        return json.loads(body)
    
    if type(body) is dict:
        return body
    
    return None

def api_response(status, body):
    return {
        'statusCode': status,
        'body': json.dumps(body)
    }

def api_success(body):
    return api_response(200, body)

def api_client_error(body):
    return api_response(400, body)

def api_server_fault(body):
    return api_response(500, body)

def get_game(gameId) -> Game:
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('rspfootball-games')

    response = table.get_item(
        Key = {'gameId': gameId},
    )

    if 'Item' not in response:
        return None

    return Game(**response['Item'])

class ConditionalCheckFailedException(Exception):
    pass

def store_game(game: Game, condition=None):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('rspfootball-games')

    game = game.dict()
    try:
        if condition is None:
            table.put_item(Item = game)
        else:
            table.put_item(
                Item = game,
                ConditionExpression = condition,
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException as e:
        raise ConditionalCheckFailedException(e)

# given an object, convert all sub-elements of type Decimal to int
# modify the argument as needed, and return the converted form
def convert_decimals(obj):
    if type(obj) is decimal.Decimal:
        return int(obj)
    
    if type(obj) is dict:
        for key, value in obj.items():
            obj[key] = convert_decimals(value)
    elif type(obj) == list:
        for index, value in enumerate(obj):
            obj[index] = convert_decimals(value)
    
    return obj

# return 'home', 'away', or None, given the game and user
def get_player(game, user):
    for player in ['home', 'away']:
        if game.players[player] == user:
            return player
    return None
