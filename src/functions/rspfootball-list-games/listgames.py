import json

import boto3

import rsputil

def lambda_handler(event, context):
    
    games = get_games()
    
    return {
        'statusCode': 200,
        'body': json.dumps(games)
    }


def get_games():
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('rspfootball-games')

    result = table.scan(
        ProjectionExpression = 'gameId,home,away',
        FilterExpression = 'players.away = :null',
        ExpressionAttributeValues = {':null': None}
    )

    return result['Items']
    