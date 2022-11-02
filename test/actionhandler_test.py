import unittest
import sys

sys.path.append(f'src/layers/rspfootball-util')
sys.path.append(f'src/functions/rspfootball-action-handler')

import rspmodel
from rspmodel import GainResult, IncompletePassResult, KickoffChoiceAction, LossResult, OutOfBoundsPassResult, Play, RollAction, ScoreResult, ScoreType, State, TouchbackChoice, TouchbackResult, TurnoverResult, TurnoverType
import rsputil
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
        result = [])

def mock_roll(roll):
    import random
    roll_iter = iter(roll)
    random.randint = lambda min, max: next(roll_iter) 


class AssertionPredicate:

    def __init__(self, predicate):
        self.predicate = predicate

    # return a tuple with the result, and an optional assertion failure message
    def test(self, value):
        return self.predicate(value)

    # Return a predicate that passes if a test object contains
    # all of the given elements in the collection
    @staticmethod
    def containsAll(requiredValues):
        def predicate(collection):
            for requiredValue in requiredValues:
                if requiredValue not in collection:
                    return False, 'Collection missing required value: ' + str(requiredValue)
            return True, None

        return AssertionPredicate(predicate)

class ActionHandlerTest(unittest.TestCase):

    # assert that all the expected keys and values are present
    # in the actual dict. Only check given values, and inspect deep
    # into child dicts
    def assertValues(self, actual, expected):
        self.assertEqual(type(actual), dict)

        for key, expected_value in expected.items():
            self.assertTrue(key in actual, f"key given in expected dict, but not present in actual: {key}")

            if type(expected[key]) is dict:
                self.assertValues(actual[key], expected[key])
            elif isinstance(expected[key], AssertionPredicate):
                assertionValue, message = expected[key].test(actual[key])
                self.assertTrue(assertionValue, f'{message}: key {key}')
            else:
                self.assertEqual(actual[key], expected_value, f'key {key}')


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

    def test_rsp_first_action(self):
        self.action_test_helper(init_game = {
            'state': State.COIN_TOSS
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.COIN_TOSS,
            'rsp': {
                ACTING_PLAYER: 'ROCK',
                OPPONENT: None
            },
            'actions': {ACTING_PLAYER: ['POLL'], OPPONENT: ['RSP']}
        })

    def test_coin_toss_tie(self):
        self.action_test_helper(init_game = {
            'state': State.COIN_TOSS,
            'rsp': {
                OPPONENT: 'ROCK',
                ACTING_PLAYER: None
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.COIN_TOSS,
            'rsp': {
                OPPONENT: None,
                ACTING_PLAYER: None
            },
            'result': [rspmodel.RspResult(
                name = 'RSP',
                home = 'ROCK',
                away = 'ROCK'
            )]
        })

    def test_coin_toss_win(self):
        self.action_test_helper(init_game = {
            'state': State.COIN_TOSS,
            'rsp': {
                OPPONENT: 'ROCK',
                ACTING_PLAYER: None
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.KICKOFF_ELECTION,
            'rsp': {
                OPPONENT: None,
                ACTING_PLAYER: None
            },
            'result': [rspmodel.RspResult(**{
                'name': 'RSP',
                ACTING_PLAYER: 'PAPER',
                OPPONENT: 'ROCK'
            })]
        })
    
    def test_kickoff_election(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF_ELECTION,
            'rsp': {
                OPPONENT: 'ROCK',
                ACTING_PLAYER: None
            }
        }, action = rspmodel.KickoffElectionAction(
            name = 'KICKOFF_ELECTION',
            choice = 'RECIEVE'
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': OPPONENT,
            'result': AssertionPredicate.containsAll([
                rspmodel.KickoffElectionResult(choice = 'RECIEVE')])
        })

    def test_kickoff_choice_regular(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER
        }, action = KickoffChoiceAction(
            name = 'KICKOFF_CHOICE',
            choice = 'REGULAR'
        ), expected_game = {
            'state': State.KICKOFF,
            'possession': ACTING_PLAYER
        })
    
    def test_kickoff_choice_onside(self):
        self.action_test_helper(init_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER
        }, action = KickoffChoiceAction(
            name = 'KICKOFF_CHOICE',
            choice = 'ONSIDE'
        ), expected_game = {
            'state': State.ONSIDE_KICK,
            'possession': ACTING_PLAYER
        })
    
    def test_onside_kick_success(self):
        self.action_test_helper(init_game = {
            'state': State.ONSIDE_KICK,
            'possession': ACTING_PLAYER,
            'ballpos': 35
        }, action = RollAction(
            count = 2
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 45
        }, roll=[2,3])
    
    def test_onside_kick_failure(self):
        self.action_test_helper(init_game = {
            'state': State.ONSIDE_KICK,
            'possession': ACTING_PLAYER,
            'ballpos': 35
        }, action = RollAction(
            count = 2
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'ballpos': 55
        }, roll=[3,3])

    def test_onside_kick_from_safety_success(self):
        self.action_test_helper(init_game = {
            'state': State.ONSIDE_KICK,
            'possession': ACTING_PLAYER,
            'ballpos': 20
        }, action = RollAction(
            count = 2
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 30
        }, roll=[2,3])
    
    def test_onside_kick_from_safety_failure(self):
        self.action_test_helper(init_game = {
            'state': State.ONSIDE_KICK,
            'possession': ACTING_PLAYER,
            'ballpos': 20
        }, action = RollAction(
            count = 2
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'ballpos': 70
        }, roll=[3,3])

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
            'ballpos': 40,
            'firstDown': 50,
            'play': None,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.OutOfBoundsKickResult()])
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
            'ballpos': 20,
            'firstDown': 30,
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
            'firstDown': 30,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        }, roll=[2])
    
    def test_kick_return_6_touchdown(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0},
            'ballpos': 10
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'play': None,
            'actions': {ACTING_PLAYER: ['PAT_CHOICE']}
        }, roll=[6])

    def test_kick_return_6_normal(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 25,
            'firstDown': 35,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        }, roll=[3])
    
    def test_kick_return_1_roll_fumble(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN_1,
            'possession': ACTING_PLAYER,
            'ballpos': 10,
            'playCount': 5,
        }, action = rspmodel.RollAgainChoiceAction(
            name = 'ROLL_AGAIN_CHOICE',
            choice = 'ROLL'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'ballpos': 85,
            'firstDown': 95,
            'down': 1,
            'playCount': 5,
            'play': None,
            'actions': {ACTING_PLAYER: ['POLL', 'PENALTY'], OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = TurnoverType.FUMBLE)])
        }, roll=[1])
    
    def test_kick_return_1_roll_normal(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN_1,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAgainChoiceAction(
            name = 'ROLL_AGAIN_CHOICE',
            choice = 'ROLL'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 20,
            'firstDown': 30,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        }, roll=[2])
    
    def test_kick_return_1_hold(self):
        self.action_test_helper(init_game = {
            'state': State.KICK_RETURN_1,
            'possession': ACTING_PLAYER,
            'ballpos': 10
        }, action = rspmodel.RollAgainChoiceAction(
            name = 'ROLL_AGAIN_CHOICE',
            choice = 'HOLD'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 10,
            'firstDown': 20,
            'play': None,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })

    
    def test_play_call_short_run(self):
        self.action_test_helper(init_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
        }, action = rspmodel.CallPlayAction(
            name = 'CALL_PLAY',
            play = 'SHORT_RUN'
        ), expected_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'actions': {'home': ['RSP'], 'away': ['RSP']}
        })
    
    def test_short_run_win(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 15,
            'actions': {'home': ['RSP'], 'away': ['RSP']},
            'result': AssertionPredicate.containsAll([rspmodel.GainResult(
                play = Play.SHORT_RUN,
                player = ACTING_PLAYER,
                yards = 5
            )])
        })
    
    def test_short_run_loss(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.SACK_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 10,
            'actions': {OPPONENT: ['ROLL']}
        })
    
    def test_short_run_tie(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'playCount': 1,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 10,
            'down': 2,
            'playCount': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })
    
    def test_short_run_touchdown(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'ballpos': 95,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'actions': {ACTING_PLAYER: ['PAT_CHOICE']}
        })
    
    def test_short_run_turnover(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN,
            'possession': ACTING_PLAYER,
            'ballpos': 20,
            'firstDown': 25,
            'down': 4,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'down': 1,
            'ballpos': 80,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.TurnoverResult(type = 'DOWNS')])
        })
    
    def test_short_run_first_down(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'ballpos': 25,
            'firstDown': 25,
            'down': 4,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'down': 1,
            'ballpos': 25,
            'firstDown': 35,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })

    def test_short_run_game_over(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'ballpos': 25,
            'firstDown': 25,
            'down': 2,
            'playCount': 80,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.GAME_OVER,
            'actions': {'home': [], 'away': []}
        })

    def test_short_run_cont_win(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 10,
            'down': 1,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 15,
            'down': 1,
            'actions': {'home': ['RSP'], 'away': ['RSP']},
            'result': AssertionPredicate.containsAll([rspmodel.GainResult(
                play = Play.SHORT_RUN,
                player = ACTING_PLAYER,
                yards = 5
            )])
        })
    
    def test_short_run_cont_loss(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 10,
            'firstDown': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 10,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })
    
    def test_short_run_cont_tie(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 10,
            'firstDown': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 10,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']}
        })
    
    def test_short_run_cont_touchdown(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 95,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'actions': {ACTING_PLAYER: ['PAT_CHOICE']}
        })
    
    def test_short_run_cont_turnover(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'ballpos': 20,
            'firstDown': 25,
            'down': 4,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'ballpos': 80,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.TurnoverResult(type = 'DOWNS')])
        })

    def test_short_run_sack_success(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 15,
            'down': 2,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.LossResult(
                play = Play.SHORT_RUN,
                player = OPPONENT,
                yards = 5
            )])
        }, roll = [5])
    
    def test_short_run_sack_fail(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 20,
            'down': 2,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']}
        }, roll = [4])

    
    def test_play_call_long_run(self):
        self.action_test_helper(init_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
        }, action = rspmodel.CallPlayAction(
            name = 'CALL_PLAY',
            play = 'LONG_RUN'
        ), expected_game = {
            'state': State.LONG_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'actions': {'home': ['RSP'], 'away': ['RSP']}
        })
    
    def test_long_run_win(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.LONG_RUN_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'ballpos': 10,
            'actions': {ACTING_PLAYER: ['ROLL'], OPPONENT: ['POLL']}
        })
    
    def test_long_run_loss(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'ballpos': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.SACK_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'ballpos': 20,
            'actions': {OPPONENT: ['ROLL'], ACTING_PLAYER: ['POLL']}
        })
    
    def test_long_run_tie(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_RUN,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 20,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']}
        })
    
    def test_long_run_roll_fumble(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_RUN_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'ballpos': 25,
            'actions': {ACTING_PLAYER: ['RSP'], OPPONENT: ['RSP']}
        }, roll = [1])
    
    def test_long_run_roll_regular(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_RUN_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11,
            'ballpos': 35,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']}
        }, roll = [3])
    
    def test_long_run_fumble_recover(self):
        self.action_test_helper(init_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11,
            'down': 2,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']}
        })
    
    def test_long_run_roll_recover_touchdown(self):
        self.action_test_helper(init_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'down': 1,
            'ballpos': 100,
            'firstDown': 100,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11,
            'down': 2,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'actions': {ACTING_PLAYER: ['PAT_CHOICE'], OPPONENT: ['POLL']},
            'result': AssertionPredicate.containsAll([ScoreResult(type = ScoreType.TOUCHDOWN)])
        })
    
    def test_long_run_roll_recover_fourth_down(self):
        self.action_test_helper(init_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'down': 4,
            'ballpos': 20,
            'firstDown': 25,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'playCount': 11,
            'down': 1,
            'ballpos': 80,
            'firstDown': 90,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.TurnoverResult(
                type = 'DOWNS'
            )])
        })

    def test_long_run_fumble_turnover(self):
        self.action_test_helper(init_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'down': 1,
            'ballpos': 80,
            'firstDown': 25,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'playCount': 11,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.TurnoverResult(
                type = 'FUMBLE'
            )])
        })

    def test_long_run_roll_turnover_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.FUMBLE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_RUN,
            'playCount': 10,
            'down': 2,
            'ballpos': 100,
            'firstDown': 100,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'playCount': 11,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.TurnoverResult(
                type = 'FUMBLE'
            )])
        })
    
    def test_long_run_sack_five(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_RUN,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 15,
            'down': 2,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.LossResult(
                play = Play.LONG_RUN,
                player = OPPONENT,
                yards = 5
            )])
        }, roll = [1])

    def test_long_run_sack_ten(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_RUN,
            'down': 1,
            'ballpos': 20,
            'firstDown': 30,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 10,
            'down': 2,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([rspmodel.LossResult(
                play = Play.LONG_RUN,
                player = OPPONENT,
                yards = 10
            )])
        }, roll = [6])

    def test_short_pass_win(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.SHORT_PASS_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'actions': {'home': ['RSP'], 'away': ['RSP']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.SHORT_PASS,
                player = ACTING_PLAYER,
                yards = 10
            )])
        })
    
    def test_short_pass_loss(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.SACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 10,
            'actions': {OPPONENT: ['SACK_CHOICE']}
        })
    
    def test_short_pass_tie(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'down': 1,
            'ballpos': 10,
            'firstDown': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'down': 2,
            'ballpos': 10,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']},
        })

    def test_short_pass_cont_win(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.SHORT_PASS_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 30,
            'actions': {'home': ['RSP'], 'away': ['RSP']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.SHORT_PASS,
                player = ACTING_PLAYER,
                yards = 10
            )])
        })

    def test_short_pass_cont_loss(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'firstDown': 30,
            'down': 1,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 20,
            'firstDown': 30,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']},
        })

    def test_short_pass_cont_tie(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_PASS_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'firstDown': 30,
            'down': 1,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 20,
            'firstDown': 30,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']},
        })

    def test_short_pass_sack_choice_sack(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'down': 1,
            'firstDown': 30
        }, action = rspmodel.SackChoiceAction(
            choice = 'SACK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 15,
            'down': 2,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([LossResult(
                player = OPPONENT,
                play = Play.SHORT_PASS,
                yards = 5
            )])
        })

    def test_short_pass_sack_choice_pick(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 20
        }, action = rspmodel.SackChoiceAction(
            choice = 'PICK'
        ), expected_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'actions': {ACTING_PLAYER: ['ROLL']},
        })
    
    def test_pick_roll_short_pass_success(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PICK_RETURN,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': 70,
            'firstDown': None,
            'actions': {ACTING_PLAYER: ['ROLL']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [6])
    
    def test_pick_roll_short_pass_failure(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 20,
            'down': 1,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 20,
            'down': 2,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([IncompletePassResult()])
        }, roll = [5])

    def test_pick_roll_short_pass_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_PASS,
            'ballpos': 95
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PICK_TOUCHBACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_PASS,
            'ballpos': -5,
            'actions': {ACTING_PLAYER: ['TOUCHBACK_CHOICE']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [6])
    
    def test_long_pass_win(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.LONG_PASS_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 10,
            'actions': {ACTING_PLAYER: ['ROLL']},
        })
    
    def test_long_pass_loss(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.SACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 10,
            'actions': {OPPONENT: ['SACK_CHOICE']},
        })
    
    def test_long_pass_tie(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_PASS,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'down': 1,
            'ballpos': 10,
            'firstDown': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'down': 2,
            'ballpos': 10,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']},
        })
    
    def test_long_pass_roll(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_PASS_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 30,
            'firstDown': 40,
            'down': 1,
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.LONG_PASS,
                player = ACTING_PLAYER,
                yards = 20
            )])
        }, roll = [2])
    
    def test_long_pass_roll_oob(self):
        self.action_test_helper(init_game = {
            'state': State.LONG_PASS_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 95,
            'firstDown': 100,
            'down': 1
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'ballpos': 95,
            'firstDown': 100,
            'down': 2,
            'result': AssertionPredicate.containsAll([OutOfBoundsPassResult()])
        }, roll = [2])
    
    def test_long_pass_sack_choice_sack(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'down': 1,
            'firstDown': 30
        }, action = rspmodel.SackChoiceAction(
            choice = 'SACK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 10,
            'down': 2,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([LossResult(
                player = OPPONENT,
                play = Play.LONG_PASS,
                yards = 10
            )])
        })

    def test_long_pass_sack_choice_pick(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20
        }, action = rspmodel.SackChoiceAction(
            choice = 'PICK'
        ), expected_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'actions': {ACTING_PLAYER: ['ROLL']},
        })
    
    def test_pick_roll_long_pass_success(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.DISTANCE_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['ROLL']},
        }, roll = [5])
    
    def test_pick_roll_long_pass_failure(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([IncompletePassResult()])
        }, roll = [4])
    
    def test_distance_roll_long_pass(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PICK_RETURN,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': 55,
            'firstDown': None,
            'actions': {OPPONENT: ['ROLL']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [3])
    
    def test_distance_roll_long_pass_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 90,
            'firstDown': 100
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PICK_TOUCHBACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.LONG_PASS,
            'ballpos': -5,
            'firstDown': None,
            'actions': {OPPONENT: ['TOUCHBACK_CHOICE']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [1])
    
    def test_distance_roll_long_pass_oob(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.LONG_PASS,
            'ballpos': 90,
            'firstDown': 100,
            'down': 1
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 90,
            'firstDown': 100,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([OutOfBoundsPassResult()])
        }, roll = [2])
    
    def test_bomb_loss(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.SACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'actions': {OPPONENT: ['SACK_CHOICE']}
    })
    
    def test_bomb_tie(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'down': 1,
            'ballpos': 10,
            'firstDown': 20,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'down': 2,
            'ballpos': 10,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY'], OPPONENT: ['POLL', 'PENALTY']},
        })
    
    def test_bomb_first_roll_odd(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [1],
            'actions': {ACTING_PLAYER: ['ROLL_AGAIN_CHOICE']},
        }, roll = [1])
    
    def test_bomb_first_roll_even(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.BOMB_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [2],
            'actions': {ACTING_PLAYER: ['ROLL']},
        }, roll = [2])
    
    def test_bomb_choice_roll_again(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [1],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'ROLL'
        ), expected_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'roll': [1,2],
            'actions': {ACTING_PLAYER: ['ROLL_AGAIN_CHOICE']},
        }, roll = [2])
    
    def test_bomb_choice_hold_under_35(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'roll': [1],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'HOLD'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 45,
            'firstDown': 55,
            'down': 1,
            'roll': [1],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.BOMB,
                player = ACTING_PLAYER,
                yards = 35
            )])
        })
    
    def test_bomb_choice_hold_over_35(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'roll': [5, 4],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'HOLD'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 55,
            'firstDown': 65,
            'down': 1,
            'roll': [5, 4],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.BOMB,
                player = ACTING_PLAYER,
                yards = 45
            )])
        })
    
    def test_bomb_third_roll_even(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'roll': [5, 4],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'ROLL'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 10,
            'firstDown': 20,
            'down': 2,
            'roll': [5, 4, 1],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([IncompletePassResult()])
        }, roll = [1])
    
    def test_bomb_third_roll_under_35(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'roll': [1, 1],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 45,
            'firstDown': 55,
            'down': 1,
            'roll': [1, 1, 1],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.BOMB,
                player = ACTING_PLAYER,
                yards = 35
            )])
        }, roll = [1])
    
    def test_bomb_third_roll_over_35(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 10,
            'firstDown': 20,
            'down': 1,
            'roll': [4, 5],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'ROLL'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 75,
            'firstDown': 85,
            'down': 1,
            'roll': [4, 5, 4],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([GainResult(
                play = Play.BOMB,
                player = ACTING_PLAYER,
                yards = 65
            )])
        }, roll = [4])
    
    def test_bomb_third_roll_oob(self):
        self.action_test_helper(init_game = {
            'state': State.BOMB_CHOICE,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 60,
            'firstDown': 70,
            'down': 1,
            'roll': [4, 5],
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RollAgainChoiceAction(
            choice = 'ROLL'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 60,
            'firstDown': 70,
            'down': 2,
            'roll': [4, 5, 4],
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([OutOfBoundsPassResult()])
        }, roll = [4])
    
    def test_bomb_sack_choice_sack(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20,
            'down': 1,
            'firstDown': 30
        }, action = rspmodel.SackChoiceAction(
            choice = 'SACK'
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 5,
            'down': 2,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY'], ACTING_PLAYER: ['POLL', 'PENALTY']},
            'result': AssertionPredicate.containsAll([LossResult(
                player = OPPONENT,
                play = Play.BOMB,
                yards = 15
            )])
        })

    def test_bomb_sack_choice_pick(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20
        }, action = rspmodel.SackChoiceAction(
            choice = 'PICK'
        ), expected_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20,
            'actions': {ACTING_PLAYER: ['ROLL']},
        })
    
    def test_pick_roll_bomb_success(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.DISTANCE_ROLL,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['ROLL']},
        }, roll = [2])
    
    def test_pick_roll_bomb_failure(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_ROLL,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 20,
            'firstDown': 30,
            'actions': {OPPONENT: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([IncompletePassResult()])
        }, roll = [5])
    
    def test_distance_roll_bomb(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 20,
            'firstDown': 30
        }, action = rspmodel.RollAction(
            count = 3
        ), expected_game = {
            'state': State.PICK_RETURN,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': 30,
            'firstDown': None,
            'actions': {OPPONENT: ['ROLL']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [3, 3, 4])
    
    def test_distance_roll_bomb_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 80,
            'firstDown': 90
        }, action = rspmodel.RollAction(
            count = 3
        ), expected_game = {
            'state': State.PICK_TOUCHBACK_CHOICE,
            'possession': OPPONENT,
            'play': Play.BOMB,
            'ballpos': -5,
            'firstDown': None,
            'actions': {OPPONENT: ['TOUCHBACK_CHOICE']},
            'result': AssertionPredicate.containsAll([TurnoverResult(type = 'PICK')])
        }, roll = [1, 1, 3])
    
    def test_distance_roll_bomb_oob(self):
        self.action_test_helper(init_game = {
            'state': State.DISTANCE_ROLL,
            'possession': ACTING_PLAYER,
            'play': Play.BOMB,
            'ballpos': 45,
            'firstDown': 55,
            'down': 1
        }, action = rspmodel.RollAction(
            count = 3
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 45,
            'firstDown': 55,
            'down': 2,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
            'result': AssertionPredicate.containsAll([OutOfBoundsPassResult()])
        }, roll = [4,5,6])
    
    def test_pick_touchback_choice_touchback(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_TOUCHBACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 10,
            'down': 2,
            'ballpos': -5
        }, action = rspmodel.TouchbackChoiceAction(
            choice = TouchbackChoice.TOUCHBACK
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 20,
            'firstDown': 30,
            'down': 1,
            'playCount': 11,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
        })

    def test_pick_touchback_choice_return(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_TOUCHBACK_CHOICE,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': -5
        }, action = rspmodel.TouchbackChoiceAction(
            choice = TouchbackChoice.RETURN
        ), expected_game = {
            'state': State.PICK_RETURN,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': -5,
            'actions': {ACTING_PLAYER: ['ROLL']},
        })
    
    def test_pick_return(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_RETURN,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 10,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11, 
            'ballpos': 20,
            'firstDown': 30,
            'down': 1,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
        }, roll = [2])

    def test_pick_return_6(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_RETURN,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 10
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'play': None,
            'ballpos': 40,
            'actions': {ACTING_PLAYER: ['ROLL']},
        }, roll = [6])

    def test_pick_return_6_regular(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 10,
            'ballpos': 40
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PLAY_CALL,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11,
            'ballpos': 40,
            'firstDown': 50,
            'down': 1,
            'actions': {ACTING_PLAYER: ['CALL_PLAY', 'PENALTY']},
        }, roll = [1])
    
    def test_pick_return_6_touchdown(self):
        self.action_test_helper(init_game = {
            'state': State.PICK_RETURN_6,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 10,
            'ballpos': 40
        }, action = rspmodel.RollAction(
            count = 1
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'play': None,
            'playCount': 11,
            'ballpos': 100,
            'actions': {ACTING_PLAYER: ['PAT_CHOICE']},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'TOUCHDOWN')])
        }, roll = [6])

    def test_touchdown_last_play(self):
        self.action_test_helper(init_game = {
            'state': State.SHORT_RUN_CONT,
            'possession': ACTING_PLAYER,
            'play': Play.SHORT_RUN,
            'playCount': 80,
            'ballpos': 95,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'playCount': 81,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'actions': {ACTING_PLAYER: ['PAT_CHOICE']},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'TOUCHDOWN')])
        })
    
    def test_pat_choice_one_point(self):
        self.action_test_helper(init_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, action = rspmodel.PatChoiceAction(
            name = 'PAT_CHOICE',
            choice = 'ONE_POINT'
        ), expected_game = {
            'state': State.EXTRA_POINT,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['ROLL']},
            'ballpos': 95,
        })
    
    def test_pat_choice_two_point(self):
        self.action_test_helper(init_game = {
            'state': State.PAT_CHOICE,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, action = rspmodel.PatChoiceAction(
            name = 'PAT_CHOICE',
            choice = 'TWO_POINT'
        ), expected_game = {
            'state': State.EXTRA_POINT_2,
            'possession': ACTING_PLAYER,
            'actions': {'home': ['RSP'], 'away': ['RSP']},
            'ballpos': 95,
        })

    def test_pat_kick_success(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 2
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['KICKOFF_CHOICE']},
            'score': {ACTING_PLAYER: 7, OPPONENT: 0},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'PAT_1')])
        }, roll = [1, 3])
    
    def test_pat_kick_miss(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 2
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['KICKOFF_CHOICE']},
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, roll = [1, 2])

    def test_pat_kick_game_over(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT,
            'possession': ACTING_PLAYER,
            'playCount': 81,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 2
        ), expected_game = {
            'state': State.GAME_OVER,
            'possession': ACTING_PLAYER,
            'actions': {'home': [], 'away': []},
            'score': {ACTING_PLAYER: 7, OPPONENT: 0}
        }, roll = [1, 3])
    
    def test_two_point_conversion_win(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT_2,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['KICKOFF_CHOICE']},
            'score': {ACTING_PLAYER: 8, OPPONENT: 0},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'PAT_2')])
        })
    
    def test_two_point_conversion_loss(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT_2,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'SCISSORS'
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['KICKOFF_CHOICE']},
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        })
    
    def test_two_point_conversion_tie(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT_2,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'ROCK'
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': ACTING_PLAYER,
            'actions': {ACTING_PLAYER: ['KICKOFF_CHOICE']},
            'score': {ACTING_PLAYER: 6, OPPONENT: 0}
        })
    
    def test_two_point_conversion_last_play(self):
        self.action_test_helper(init_game = {
            'state': State.EXTRA_POINT_2,
            'possession': ACTING_PLAYER,
            'score': {ACTING_PLAYER: 6, OPPONENT: 0},
            'playCount': 81,
            'rsp': {
                ACTING_PLAYER: None,
                OPPONENT: 'ROCK'
            }
        }, action = rspmodel.RspAction(
            name = 'RSP',
            choice = 'PAPER'
        ), expected_game = {
            'state': State.GAME_OVER,
            'score': {ACTING_PLAYER: 8, OPPONENT: 0}
        })
    
    def test_safety(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 5,
            'firstDown': 30,
            'playCount': 1,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0}
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.KICKOFF_CHOICE,
            'possession': OPPONENT,
            'play': None,
            'ballpos': 20,
            'actions': {OPPONENT: ['KICKOFF_CHOICE']},
            'playCount': 2,
            'score': {ACTING_PLAYER: 2, OPPONENT: 0},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'SAFETY')])
        }, roll = [5])
    
    def test_safety_last_play(self):
        self.action_test_helper(init_game = {
            'state': State.SACK_ROLL,
            'possession': OPPONENT,
            'play': Play.SHORT_RUN,
            'down': 1,
            'ballpos': 5,
            'firstDown': 30,
            'playCount': 80,
            'score': {ACTING_PLAYER: 0, OPPONENT: 0}
        }, action = rspmodel.RollAction(
            name = 'ROLL',
            count = 1
        ), expected_game = {
            'state': State.GAME_OVER,
            'score': {ACTING_PLAYER: 2, OPPONENT: 0},
            'result': AssertionPredicate.containsAll([ScoreResult(type = 'SAFETY')])
        }, roll = [5])

class ActionHandlerRegistrationTest(unittest.TestCase):

    def test_no_conflicts(self):
        # dict from (state, action) to handler
        handlers = {}

        for handler in actionhandler.ACTION_HANDLERS:
            for state in handler.states:
                for action in handler.actions:
                    key = (state, action)
                    if key in handlers:
                        self.assertTrue(False, f'''
                        Multiple handlers registered for: {key}
                        Registered handlers: {type(handlers[key])} and {type(handler)}''')
                    handlers[(state, action)] = handler


if __name__ == '__main__':
    rsputil.configure_logger()
    unittest.main()
