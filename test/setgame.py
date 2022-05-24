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
        result = None)

def set_game(overrides):
    game = {**DEFAULT_GAME.dict(), **overrides}

    rsputil.store_game(rspmodel.Game(**game))

if __name__ == '__main__':

    overrides = {}
    for arg in sys.argv[1:]:
        key, val = arg.split('=')
        overrides[key] = value

    set_game(overrides)
