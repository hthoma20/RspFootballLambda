import functools

import boto3
from boto3.dynamodb.conditions import Attr
import pydantic

import rspmodel
import rsputil

# This api is exposed to search for games
# If no query parameters are supplied, a list of all available games is returned
def lambda_handler(event, context):

    try:
        query = rspmodel.ListGamesQuery(**rsputil.get_event_query_params(event))
    except pydantic.error_wrappers.ValidationError as error:
        return rsputil.api_client_error(str(error))

    if (not query.available) and (not query.user):
        return rsputil.api_success({
            'games': [],
            'message': 'The provided query requests no results'
        })

    filters = []
    
    if query.available:
        filters.append(Attr('players.away').eq(None))
    
    if query.user:
        filters.append(Attr('players.home').eq(query.user) | Attr('players.away').eq(query.user))

    filter = functools.reduce(lambda a, b: a | b, filters)
    games = get_games(filter)

    # if query.user:

    #     games = get_games(
    #         FilterExpression = ':user IN (players.home, players.away)',
    #         ExpressionAttributeValues  = {':user': query.user}
    #     )
    # else:
    #     games = get_games(
    #         FilterExpression = 'players.away = :null',
    #         ExpressionAttributeValues = {':null': None}
    #     )
    
    return rsputil.api_success({
        'games': games
    })


def get_games(FilterExpression):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('rspfootball-games')

    result = table.scan(
        ProjectionExpression = 'gameId,players.home,players.away',
        FilterExpression = FilterExpression
    )

    return result['Items']
    