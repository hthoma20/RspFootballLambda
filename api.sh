#!/bin/bash

if [ $# -lt 1 -o $# -gt 2 ]
then
    echo "Usage: ./api.sh <endpoint> [body]"
    exit 1
fi

apiurl='https://7ldpifsbac.execute-api.us-west-2.amazonaws.com'
endpoint=$1
body=$2

if [[ 'new|action|poll|join' =~ "$endpoint" ]]
then
    set -x
    curl -X POST "$apiurl/$endpoint" -d "$body"
elif [[ 'games' =~ "$endpoint" ]]
then
    set -x
    curl "$apiurl/$endpoint"
else
    echo "Unknown endpoint"
fi
