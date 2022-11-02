import json
import sys

sys.path.append(f'src/layers/rspfootball-util')

import rsputil
import rspmodel

DEFAULT_GAME = rspmodel.Game(
        gameId = 'test_default_id',
        version = 0,
        players = {
            'home': 'harry',
            'away': 'daylin',
        },
        state = rspmodel.State.PLAY_CALL,
        score = {
            'home': 0,
            'away': 0
        },
        penalties = {
            'home': 2,
            'away': 2
        },
        possession = 'home',
        firstKick = 'home',
        ballpos = 5,
        playCount = 1,
        down = 1,
        firstDown = 20,
        play = None,
        rsp = {
            'home': None,
            'away': None
        },
        roll = [],
        actions = {
            'home': ['CALL_PLAY', 'PENALTY'],
            'away': ['POLL']
        },
        result = [])

def set_game(overrides):
    game = {**DEFAULT_GAME.dict(), **overrides}

    rsputil.store_game(rspmodel.Game(**game))

if __name__ == '__main__':

    overrides = {}
    args = sys.argv[1:]
    for argindex, arg in enumerate(args):
        if '=' in arg:
            key, val = arg.split('=')
            overrides[key] = val
        elif arg == '--json':
            if len(overrides) > 0:
                print('= args cannot be used with a --json arg', file=sys.stderr)
                exit(1)
            
            overrides = json.loads(args[argindex + 1])
            break
        else:
            print('''Unrecognized arg. Use <key>=<val> to override default attributes, or
                --json to provide a full game''', file=sys.stderr)

    set_game(overrides)
