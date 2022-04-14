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

    try:
        join_game(game_id, user)
    except GameFullException:
        return rsputil.api_client_error('Cannot join game: game is full')
    
    return rsputil.api_success('Joined game')

class GameFullException(Exception):
    pass

def join_game(game_id, user):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('rspfootball-games')

    try:
        table.update_item(
            Key = {"gameId": game_id},
            UpdateExpression = 'SET players.away = :user, version = version + :1',
            ConditionExpression = Attr('players.away').attribute_type('NULL') & Attr('players.home').ne(user),
            ExpressionAttributeValues = {':user': user, ':1': 1},
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException as e:
        raise GameFullException(e)


