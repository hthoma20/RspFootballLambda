#!/bin/bash

if [ $# -ne 1 ]
then
    echo "Usage: $0 <function name>"
    exit 1
fi

./zipcode.sh

function=$1

aws lambda update-function-code \
    --function-name $function \
    --zip-file fileb://build/functions/$function.zip \
    | cat
