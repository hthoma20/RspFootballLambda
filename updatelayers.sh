#!/bin/bash

./zipcode.sh

aws lambda publish-layer-version \
		--layer-name rspfootball-util \
		--compatible-runtimes python3.9 \
		--compatible-architectures x86_64 \
		--zip-file fileb://build/layers/rspfootball-util.zip \
        | cat

for function in 'rspfootball-action-handler' 'rspfootball-new-game' 'rspfootball-list-games' 'rspfootball-poll-game' 'rspfootball-join-game'
do    
    aws lambda update-function-configuration \
        --function-name "$function" \
        --layers $(./layerversion.sh rspfootball-util) \
        | cat
    # aws lambda wait function-updated --function-name "$function"
done
