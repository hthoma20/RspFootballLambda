import unittest
import sys

sys.path.append(f'src/layers/rspfootball-util')
sys.path.append(f'src/functions/rspfootball-action-handler')

import rspmodel
from rspmodel import State
import actionhandler

ACTING_PLAYER = 'home'
OPPONENT = 'away'

BASE_GAME = rspmodel.Game(
        gameId = 'test_default_id',
        version = 0,
        players = {
            'home': 'harry',
            'away': 'daylin',
        },
        state = rspmodel.State.COIN_TOSS,
        score = {
            'home': 0,
            'away': 0
        },
        penalties = {
            'home': 2,
            'away': 2
        },
        possession = None,
        firstKick = None,
        ballpos = 35,
        playCount = 1,
        down = 1,
        play = None,
        rsp = {
            'home': None,
            'away': None
        },
        roll = [],
        actions = {
            'home': ['POLL'],
            'away': ['POLL']
        },
        result = None)

def mock_roll(roll):
    import random
    roll_iter = iter(roll)
    random.randint = lambda min, max: next(roll_iter) 

class ActionHandlerTest(unittest.TestCase):

    # assert that all the expected keys and values are present
    # in the actual dict. Only check given values, and inspect deep
    # into child dicts
    def assertValues(self, actual, expected):
        self.assertEqual(type(actual), dict)

        for key, expected_value in expected.items():
            self.assertTrue(key in actual)

            if type(expected[key]) is dict:
                self.assertValues(actual[key], expected[key])
            else:
                self.assertEqual(actual[key], expected_value)


    # merge the given init_game into BASE_GAME
    # call actionhandler with the given action
    # assert the given properties on the outcome game
    def action_test_helper(self, init_game, action, expected_game, roll=None):
        game_dict = {**BASE_GAME.dict(), **init_game}
        game = rspmodel.Game(**game_dict)

        if roll:
            mock_roll(roll)

        actionhandler.process_action(game, ACTING_PLAYER, action)
        self.assertValues(game.dict(), expected_game)

    
    def test_kickoff_to_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF,
            'possession': ACTING_PLAYER
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 3
        ), expected_game = {
            'state': State.TOUCHBACK_CHOICE,
            'possession': OPPONENT,
            'actions': {OPPONENT: ['TOUCHBACK_CHOICE']}
        }, roll=[5,5,3])

    def test_kickoff_to_return(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF,
            'possession': ACTING_PLAYER
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 3
        ), expected_game = {
            'state': State.KICK_RETURN,
            'possession': OPPONENT,
            'play': None,
            'actions': {OPPONENT: ['ROLL']}
        }, roll=[3,3,3])
    
    def test_kickoff_out_of_bounds(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF,
            'possession': ACTING_PLAYER
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 3
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']}
        }, roll=[2,2,4])

    def test_touchback_return(self):
        self.action_test_helper(init_game = {
            'state': State.TOUCHBACK_CHOICE,
            'possession': ACTING_PLAYER
        }, action = rspmodel.TouchbackChoiceAction(
            name = 'TOUCHBACK_CHOICE',
            choice = 'RETURN'
        ), expected_game = {
            'state': State.KICK_RETURN,
            'possession': ACTING_PLAYER,
            'play': None,
            'actions': {ACTING_PLAYER: ['ROLL']}
        })
    
    def test_touchback_no_return(self):
        self.action_test_helper(init_game = {
            'state': State.TOUCHBACK_CHOICE,
            'possession': ACTING_PLAYER
        }, action = rspmodel.TouchbackChoiceAction(
            name = 'TOUCHBACK_CHOICE',
            choice = 'TOUCHBACK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })
    
    def test_kick_return_roll_1(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.KICK_RETURN_1,
            'possession': ACTING_PLAYER,
            'ballpos': 15,
            'play': None,
            'actions': {ACTING_PLAYER: ['ROLL_AGAIN_CHOICE']}
        }, roll=[1])
    
    def test_kick_return_roll_6(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.KICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'ballpos': 40,
            'play': None,
            'actions': {ACTING_PLAYER: ['ROLL']}
        }, roll=[6])
    
    def test_kick_return_normal(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 20,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        }, roll=[2])
        
if __name__ == '__main__':
    unittest.main()
