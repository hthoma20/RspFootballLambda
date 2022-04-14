#!/bin/bash

if [ $# -ne 1 ]
then
    echo "Usage:"
    echo "$0 <layer name>"
    exit 1
fi

aws lambda list-layers | jq -r '.Layers|map(select(.LayerName == "rspfootball-util"))[].LatestMatchingVersion.LayerVersionArn'
