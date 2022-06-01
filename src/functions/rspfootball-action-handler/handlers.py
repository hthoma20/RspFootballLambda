import logging
import random

import rspmodel
from rspmodel import Action, KickoffChoice, KickoffElectionChoice, PatChoice, Play, RollAgainChoice, RspChoice, State, TouchbackChoice
from rsputil import get_opponent

class IllegalActionException(Exception):
    pass

GAME_LENGTH = 80

def set_call_play_state(game):
    game.state = State.PLAY_CALL
    game.actions[game.possession] = ['CALL_PLAY', 'PENALTY']
    game.actions[get_opponent(game.possession)] = ['POLL', 'PENALTY']
    game.play = None

def set_kickoff_state(game, yardline):
    game.ballpos = yardline
    game.firstDown = None
    
    game.state = State.KICKOFF_CHOICE
    game.actions[game.possession] = ['KICKOFF_CHOICE']


def touchdown(game):
    game.score[game.possession] += 6
    game.state = State.PAT_CHOICE
    game.actions[game.possession] = ['PAT_CHOICE']

def safety(game):
    game.score[get_opponent(game.possession)] += 2
    game.result += [rspmodel.SafetyResult()]

    if game.playCount > GAME_LENGTH:
        set_game_over_state(game)    
    else:
        set_kickoff_state(game, 20)


def end_play(game):

    game.play = None
    game.playCount += 1
    game.down += 1

    if game.ballpos >= 100:
        touchdown(game)
        return
    
    if game.ballpos <= 0:
        safety(game)
        return

    if game.playCount > GAME_LENGTH:
        set_game_over_state(game)
        return
    
    if game.ballpos >= game.firstDown:
        set_first_down(game)
    elif game.down > 4:
        switch_possession(game)
        set_first_down(game)
    
    set_call_play_state(game)

def set_first_down(game):
    game.down = 1
    game.firstDown = game.ballpos + 10
    game.firstDown = min(game.firstDown, 100)

def set_game_over_state(game):
    game.state = State.GAME_OVER
    game.actions = {
        'home': [],
        'away': []
    }

def switch_possession(game):
    game.possession = get_opponent(game.possession)
    game.ballpos = 100 - game.ballpos

def process_touch_down(game):
    game.score[game.possession] += 6

    game.state = State.PAT_CHOICE
    game.actions[game.possession] = ['PAT_CHOICE']

def roll_dice(count):
    return [random.randint(1, 6) for _ in range(count)]

class ActionHandler:

    # A list of states that the game can be in for this
    # action handler to be invoked
    states = None
    # A list of types of actions that this action handler can handle
    actions = None

    # Handle the given action taken by the given player
    # This method must only be called if both
    # - game.state in states
    # - type(action) in actions
    # This method will mutate the given game according to the given action
    # If the action is illegal, IllegalActionException will be raised
    def handle_action(game, player, action):
        raise NotImplementedError()


class RspActionHandler(ActionHandler):
    # Handle an action that requires an RSP completion
    # subclasses should override the states class member, and implement handle_rsp_action
    # subclasses should *not* override actions. If a handler wants to accept
    # other types of actions other than RspAction, it should not subclass RspActionHandler
    actions = [rspmodel.RspAction]

    def handle_rsp_action(self, game, winner):
        raise NotImplementedError()

    def handle_action(self, game, player, action):
        game.rsp[player] = action.choice

        opponent = get_opponent(player)

        if game.rsp[opponent]:
            game.result += [rspmodel.RspResult(
                home = game.rsp['home'],
                away = game.rsp['away']
            )]
            winner = self.get_rsp_winner(game.rsp)
            logging.info(f'RSP winner: {winner}')
            game.rsp = {
                'home': None,
                'away': None,
            }
            self.handle_rsp_action(game, winner)
        else:
            game.actions[opponent] = ['RSP']

    def get_rsp_winner(self, rsp):
        if rsp['home'] == rsp['away']:
            return None
        
        wins = {
            RspChoice.ROCK: RspChoice.SCISSORS,
            RspChoice.SCISSORS: RspChoice.PAPER,
            RspChoice.PAPER: RspChoice.ROCK
        }

        if wins[rsp['home']] == rsp['away']:
            return 'home'
        return 'away'

class CoinTossActionHandler(RspActionHandler):
    states = [State.COIN_TOSS]

    def handle_rsp_action(self, game, winner):
        # during the cointoss a tie is a redo
        if winner is None:
            game.actions['home'] = ['RSP']
            game.actions['away'] = ['RSP']
        else:
            game.state = State.KICKOFF_ELECTION
            game.actions[winner] = ['KICKOFF_ELECTION']
            game.actions[get_opponent(winner)] = ['POLL']


class RollActionHandler(ActionHandler):
    # Handle an action that requires a roll action
    # subclasses should override the "allowed_counts" class member,
    # the states class member, and implement handle_roll_action
    # subclasses should *not* override actions. If a handler wants to accept
    # other types of actions other than RollAction, it should not subclass RollActionHandler
    actions = [rspmodel.RollAction]

    # a collection of allowed number of dice to accept
    allowed_counts = None

    def handle_roll_action(self, game, roll):
        raise NotImplementedError()

    def handle_action(self, game, player, action):
        if action.count not in self.allowed_counts:
            raise IllegalActionException(f'Must roll {self.allowed_counts} dice in state {game.state}')
        
        roll = roll_dice(action.count)
        game.result += [rspmodel.RollResult(roll=roll)]
        self.handle_roll_action(game, roll)

class KickoffActionHandler(RollActionHandler):
    states = [State.KICKOFF]
    allowed_counts = [3]

    def handle_roll_action(self, game, roll):
        # mark that this is not a play, this will be checked when the return is complete
        # needed because a punt can also result in a TOUCHBACK_CHOICE, and after a punt,
        # the play counter must be increased
        game.play = None

        game.ballpos += 5 * sum(roll)

        switch_possession(game)

        if sum(roll) <= 8:
            game.ballpos = 40
            set_first_down(game)
            set_call_play_state(game)

        elif game.ballpos <= -10:
            game.ballpos = 20
            set_first_down(game)
            set_call_play_state(game)

        elif game.ballpos <= 0:
            game.state = State.TOUCHBACK_CHOICE
            game.actions[game.possession] = ['TOUCHBACK_CHOICE']

        else:
            game.state = State.KICK_RETURN
            game.actions[game.possession] = ['ROLL']

class OnsideKickActionHandler(RollActionHandler):
    states = [State.ONSIDE_KICK]
    allowed_counts = [2]

    def handle_roll_action(self, game, roll):
        game.ballpos = 45

        if sum(roll) > 5:
            switch_possession(game)
        
        set_call_play_state(game)
        set_first_down(game)

class KickReturnActionHandler(RollActionHandler):
    states = [State.KICK_RETURN]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        
        game.ballpos += 5 * roll

        if roll == 1:
            game.state = State.KICK_RETURN_1
            game.actions[game.possession] = ['ROLL_AGAIN_CHOICE']
        elif roll == 6:
            game.state = State.KICK_RETURN_6
            game.actions[game.possession] = ['ROLL']
        else:
            set_call_play_state(game)
            set_first_down(game)

class KickReturn6ActionHandler(RollActionHandler):
    states = [State.KICK_RETURN_6]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        
        if roll == 6:
            process_touch_down(game)
        else:
            game.ballpos += 5 * roll
            set_first_down(game)
            set_call_play_state(game)

class KickReturn1ActionHandler(ActionHandler):
    states = [State.KICK_RETURN_1]
    actions = [rspmodel.RollAgainChoiceAction]

    def handle_action(self, game, player, action):
        
        if action.choice == RollAgainChoice.HOLD:
            set_call_play_state(game)
            set_first_down(game)
            return
        
        # choice is ROLL
        roll = roll_dice(count=1)
        game.result += [rspmodel.RollResult(roll=roll)]

        [roll] = roll
        game.ballpos += 5 * roll

        if roll == 1:
            game.state = State.FUMBLE
            game.actions = {
                'home': ['RSP'],
                'away': ['RSP']
            }
        else:
            set_call_play_state(game)
            set_first_down(game)

class KickoffElectionActionHandler(ActionHandler):
    states = [State.KICKOFF_ELECTION]
    actions = [rspmodel.KickoffElectionAction]

    def handle_action(self, game, player, action):

        if action.choice == KickoffElectionChoice.KICK:
            kicker = player
        else: # choice is RECIEVE
            kicker = get_opponent(player)
        
        game.firstKick = kicker
        game.possession = kicker

        set_kickoff_state(game, 35)

class KickoffChoiceActionHandler(ActionHandler):
    states = [State.KICKOFF_CHOICE]
    actions = [rspmodel.KickoffChoiceAction]
        
    def handle_action(self, game, player, action):
        if action.choice == KickoffChoice.REGULAR:
            game.state = State.KICKOFF
        else: # choice is ONSIDE
            game.state = State.ONSIDE_KICK
        
        game.actions[player] = ['ROLL']

class TouchbackChoiceActionHandler(ActionHandler):
    states = [State.TOUCHBACK_CHOICE]
    actions = [rspmodel.TouchbackChoiceAction]
        
    def handle_action(self, game, player, action):
        if action.choice == TouchbackChoice.TOUCHBACK:
            game.ballpos = 20
            set_first_down(game)
            set_call_play_state(game)
        else: # choice is RETURN
            game.play = None # since a punt can end with a kick return, mark that there is not a play to end
            game.state = State.KICK_RETURN
            game.actions[player] = ['ROLL']


class PlayCallActionHandler(ActionHandler):
    states = [State.PLAY_CALL]
    actions = [rspmodel.CallPlayAction]

    def handle_action(self, game, player, action):
        game.play = action.play

        if game.play == Play.SHORT_RUN:
            game.state = State.SHORT_RUN
        else:
            raise IllegalActionException("Unexpected play")
        
        game.actions = {
            'home': ['RSP'],
            'away': ['RSP']
        }

class ShortRunActionHandler(RspActionHandler):
    states = [State.SHORT_RUN, State.SHORT_RUN_CONT]

    def handle_rsp_action(self, game, winner):
        opponent = get_opponent(game.possession)

        # if this is a continuation, we can treat a loss as a tie
        if game.state == State.SHORT_RUN_CONT and winner == opponent:
            winner = None
        
        if winner == game.possession:
            game.ballpos += 5
            
            if game.ballpos >= 100:
                end_play(game)
            else:
                game.state = State.SHORT_RUN_CONT
                game.actions = {
                    'home': ['RSP'],
                    'away': ['RSP']
                }
        elif winner == opponent:
            game.state = State.SACK_ROLL
            game.actions[opponent] = ['ROLL']

        else:
            end_play(game)

class SackActionHandler(RollActionHandler):
    states = [State.SACK_ROLL]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):

        [roll] = roll

        if game.play == Play.SHORT_RUN:
            if roll >= 5:
                game.ballpos -= 5
        else:
            raise Exception(f'Unexpected play [{game.play}] for sack roll')
        
        end_play(game)

class PatChoiceActionHandler(ActionHandler):
    states = [State.PAT_CHOICE]
    actions = [rspmodel.PatChoiceAction]

    def handle_action(self, game, player, action):
        if action.choice == PatChoice.ONE_POINT:
            game.state = State.EXTRA_POINT
            game.actions[player] = ['ROLL']
        else: # choice is TWO_POINT
            game.state = State.EXTRA_POINT_2
            game.actions = {
                'home': ['RSP'],
                'away': ['RSP']
            }

def end_pat(game):
    if game.playCount > GAME_LENGTH:
        set_game_over_state(game)
    else:
        set_kickoff_state(game, 35)


class ExtraPointKickActionHandler(RollActionHandler):
    states = [State.EXTRA_POINT]
    allowed_counts = [2]

    def handle_roll_action(self, game, roll):
        
        if sum(roll) >= 4:
            game.score[game.possession] += 1
        
        end_pat(game)

class TwoPointConversionActionHandler(RspActionHandler):
    states = [State.EXTRA_POINT_2]

    def handle_rsp_action(self, game, winner):
        if winner == game.possession:
            game.score[game.possession] += 2
        
        end_pat(game)