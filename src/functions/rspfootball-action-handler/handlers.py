import logging
import random

import rspmodel
from rspmodel import Action, GainResult, IncompletePassResult, KickoffChoice, KickoffElectionChoice, KickoffElectionResult, OutOfBoundsKickResult, OutOfBoundsPassResult, PatChoice, Play, RollAction, RollAgainChoice, RspChoice, SackChoice, ScoreResult, State, TouchbackChoice, TurnoverResult, TurnoverType
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
    game.actions[get_opponent(game.possession)] = ['POLL']
    game.result += [ScoreResult(type = 'TOUCHDOWN')]


def safety(game):
    game.score[get_opponent(game.possession)] += 2
    game.result += [rspmodel.ScoreResult(type = 'SAFETY')]

    if game.ballpos <= -10:
        game.ballpos = -5

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
        game.result += [TurnoverResult(type = TurnoverType.DOWNS)]
    
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
        game.roll = roll
        game.result += [rspmodel.RollResult(roll=roll, player=player)]
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
            game.result += [OutOfBoundsKickResult()]
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
        game.ballpos += 10

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
            touchdown(game)
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
        game.roll = roll_dice(count=1)
        game.result += [rspmodel.RollResult(roll=game.roll, player=player)]

        [roll] = game.roll
        game.ballpos += 5 * roll

        if roll == 1:
            switch_possession(game)
            game.result += [TurnoverResult(type = TurnoverType.FUMBLE)]
        
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
        game.result += [KickoffElectionResult(choice = action.choice)]

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

        if action.play == Play.SHORT_RUN:
            game.state = State.SHORT_RUN
        elif action.play == Play.LONG_RUN:
            game.state = State.LONG_RUN
        elif action.play == Play.SHORT_PASS:
            game.state = State.SHORT_PASS
        elif action.play == Play.LONG_PASS:
            game.state = State.LONG_PASS
        elif action.play == Play.BOMB:
            game.state = State.BOMB
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
            game.result += [GainResult(
                play = Play.SHORT_RUN,
                player = game.possession,
                yards = 5
            )]
            
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

class LongRunActionHandler(RspActionHandler):
    states = [State.LONG_RUN]

    def handle_rsp_action(self, game, winner):
        if winner == game.possession:
            game.state = State.LONG_RUN_ROLL
            game.actions[game.possession] = ['ROLL']
        elif winner == get_opponent(game.possession):
            game.state = State.SACK_ROLL
            game.actions[get_opponent(game.possession)] = ['ROLL']
        else:
            end_play(game)

class LongRunRollActionHandler(RollActionHandler):
    states = [State.LONG_RUN_ROLL]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        distance = roll*5
        game.ballpos += distance
        game.result += [GainResult(
                play = Play.SHORT_RUN,
                player = game.possession,
                yards = distance
            )]

        if roll == 1:
            game.state = State.FUMBLE
            game.actions = {
                'home': ['RSP'],
                'away': ['RSP']
            }
        else:
            end_play(game)

class ShortPassActionHandler(RspActionHandler):
    states = [State.SHORT_PASS, State.SHORT_PASS_CONT]

    def handle_rsp_action(self, game, winner):
        opponent = get_opponent(game.possession)

        # if this is a continuation, we can treat a loss as a tie
        if game.state == State.SHORT_PASS_CONT and winner == opponent:
            winner = None
        
        if winner == game.possession:
            game.ballpos += 10
            game.result += [rspmodel.GainResult(
                play = Play.SHORT_PASS,
                player = game.possession,
                yards = 10
            )]
            
            if game.ballpos >= 100:
                end_play(game)
            else:
                game.state = State.SHORT_PASS_CONT
                game.actions = {
                    'home': ['RSP'],
                    'away': ['RSP']
                }
        elif winner == opponent:
            game.state = State.SACK_CHOICE
            game.actions[opponent] = ['SACK_CHOICE']

        else:
            game.result += [rspmodel.IncompletePassResult()]
            end_play(game)

class LongPassActionHandler(RspActionHandler):
    states = [State.LONG_PASS]

    def handle_rsp_action(self, game, winner):
        if winner == game.possession:
            game.state = State.LONG_PASS_ROLL
            game.actions[game.possession] = ['ROLL']
        elif winner == get_opponent(game.possession):
            game.state = State.SACK_CHOICE
            game.actions[get_opponent(game.possession)] = ['SACK_CHOICE']
        else:
            game.result += [rspmodel.IncompletePassResult()]
            end_play(game)

class LongPassRollActionHandler(RollActionHandler):
    states = [State.LONG_PASS_ROLL]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        distance = 10 + roll*5
        
        if game.ballpos + distance >= 110:
            game.result += [OutOfBoundsPassResult()]
        else:
            game.ballpos += distance
            game.result += [GainResult(
                play = Play.LONG_PASS,
                player = game.possession,
                yards = distance
            )]

        end_play(game)

class BombActionHandler(RspActionHandler):
    states = [State.BOMB]

    def handle_rsp_action(self, game, winner):
        opponent = get_opponent(game.possession)

        if winner == game.possession:
            game.state = State.BOMB_ROLL
            game.actions[game.possession] = ['ROLL']
            game.roll = []
        elif winner == opponent:
            game.state = State.SACK_CHOICE
            game.actions[opponent] = ['SACK_CHOICE']
        else:
            game.result += [rspmodel.IncompletePassResult()]
            end_play(game)

def end_bomb(game):
    roll = sum(game.roll)
    
    if roll % 2 == 0:
        game.result += [rspmodel.IncompletePassResult()]
        end_play(game)
        return
    
    distance = max(35, 5*roll)

    if game.ballpos + distance >= 110:
        game.result += [OutOfBoundsPassResult()]
    else:    
        game.ballpos += distance
        game.result += [GainResult(
            play = Play.BOMB,
            player = game.possession,
            yards = distance
        )]

    end_play(game)

def process_bomb_roll(game):
    roll = roll_dice(1)
    game.roll += roll
    game.result += [rspmodel.RollResult(
        player = game.possession,
        roll = roll
    )]

    if len(game.roll) == 3:
        end_bomb(game)
    elif sum(game.roll) % 2 == 0:
        game.state = State.BOMB_ROLL
        game.actions[game.possession] = ['ROLL']
    else:
        game.state = State.BOMB_CHOICE
        game.actions[game.possession] = ['ROLL_AGAIN_CHOICE']


class BombRollActionHandler(ActionHandler):
    states = [State.BOMB_ROLL]
    actions = [rspmodel.RollAction]

    def handle_action(self, game, player, action):
        if action.count != 1:
            raise IllegalActionException("Bomb roll must have count=1")

        process_bomb_roll(game)

class BombChoiceActionHandler(ActionHandler):
    states = [State.BOMB_CHOICE]
    actions = [rspmodel.RollAgainChoiceAction]

    def handle_action(self, game, player, action):
        if action.choice == RollAgainChoice.ROLL:
            process_bomb_roll(game)
        else: # choice is HOLD
            end_bomb(game)

class SackActionHandler(RollActionHandler):
    states = [State.SACK_ROLL]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):

        [roll] = roll

        distance = self.get_sack_distance(game.play, roll)

        game.ballpos -= distance
        game.result += [rspmodel.LossResult(
            play = game.play,
            player = game.possession,
            yards = distance
        )]
        
        end_play(game)

    def get_sack_distance(self, play, roll):
        if play == Play.SHORT_RUN:
            return 5 if roll >= 5 else 0
        if play == Play.LONG_RUN:
            return 10 if roll == 6 else 5
        
        raise Exception(f'Unexpected play [{play}] for sack roll')

class FumbleActionHandler(RspActionHandler):
    states = [State.FUMBLE]

    def handle_rsp_action(self, game, winner):
        # This handler handles a Fumble only from a Long Run
        # in the case of a fumbled kickoff or punt return, the kicking team
        # immediately recovers

        # The player with possession has the "advantage" - a win or tie
        # retains possession
        if winner == get_opponent(game.possession):

            switch_possession(game)
            game.result += [TurnoverResult(type = TurnoverType.FUMBLE)]

            # it is possible to recover a fumble in own goal
            if game.ballpos <= 0:
                game.ballpos = 20

            set_first_down(game)
            game.down = 0 # mark down as 0, so that when the play is ended, it is first down

        set_call_play_state(game)
        end_play(game)

class SackChoiceActionHandler(ActionHandler):
    states = [State.SACK_CHOICE]
    actions = [rspmodel.SackChoiceAction]

    def handle_action(self, game, player, action):
        if action.choice == SackChoice.SACK:
            self.handle_sack_choice(game, player)
        else: # choice is PICK
            self.handle_pick_choice(game, player)

    def get_sack_yards(self, play):
        if play == Play.SHORT_PASS:
            return 5
        if play == Play.LONG_PASS:
            return 10
        if play == Play.BOMB:
            return 15
        
        raise Exception(f'Unexpected play for SackChoice: {play}')

    def handle_sack_choice(self, game, player):
        sack_yards = self.get_sack_yards(game.play)

        game.ballpos -= sack_yards
        game.result += [rspmodel.LossResult(
            play = game.play,
            player = game.possession,
            yards = sack_yards
        )]

        end_play(game)

    def handle_pick_choice(self, game, player):
        game.state = State.PICK_ROLL
        game.actions[player] = ['ROLL']


# Update the given Game from the point where the ball is thrown,
# and will be intercepted
def complete_interception(game, throw_distance):
        picking_player = get_opponent(game.possession)

        if game.ballpos + throw_distance >= 110:
            game.result += [rspmodel.OutOfBoundsPassResult()]
            end_play(game)
            return
        
        game.ballpos += throw_distance
        if game.ballpos >= 100:
            game.state = State.PICK_TOUCHBACK_CHOICE
            game.actions[picking_player] = ['TOUCHBACK_CHOICE']
        else:
            game.state = State.PICK_RETURN
            game.actions[picking_player] = ['ROLL']

        game.result += [rspmodel.TurnoverResult(type = TurnoverType.PICK)]
        switch_possession(game)
        game.firstDown = None

class PickRollActionHandler(RollActionHandler):
    states = [State.PICK_ROLL]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        
        success = self.is_pick_successful(game.play, roll)

        if not success:
            end_play(game)
            game.result += [IncompletePassResult()]
            return
        
        if game.play == Play.SHORT_PASS:
            complete_interception(game, 10)
        else:
            game.state = State.DISTANCE_ROLL
            game.actions[game.possession] = ['ROLL']
    
    def is_pick_successful(self, play, roll):
        if play == Play.SHORT_PASS:
            return roll == 6
        if play == Play.LONG_PASS:
            return roll >= 5
        if play == Play.BOMB:
            return roll % 2 == 0
        
        raise Exception(f"Unexpected play for PickRoll: {play}")
        
class DistanceRollActionHandler(RollActionHandler):
    states = [State.DISTANCE_ROLL]
    allowed_counts = [1,3]

    def handle_roll_action(self, game, roll):
        distance = self.get_throw_distance(game.play, roll)
        complete_interception(game, distance)

    def get_throw_distance(self, play, roll):
        if play == Play.LONG_PASS:
            if (len(roll) != 1):
                raise IllegalActionException("DistanceRoll for a ShortPass must be 1 die")
            return 10 + 5*sum(roll)
        
        if play == Play.BOMB:
            if (len(roll) != 3):
                raise IllegalActionException("DistanceRoll for a Bomb must be 3 dice")
            return 5*sum(roll)
        
        raise Exception(f"Unexpected play for DistanceRoll: {play}")

def complete_pick_return(game):
    set_first_down(game)
    game.down = 0
    end_play(game)

class PickReturnActionHandler(RollActionHandler):
    states = [State.PICK_RETURN]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        
        game.ballpos += 5 * roll

        if roll == 6:
            game.state = State.PICK_RETURN_6
            game.actions[game.possession] = ['ROLL']
        else:
            complete_pick_return(game)

class PickReturn6ActionHandler(RollActionHandler):
    states = [State.PICK_RETURN_6]
    allowed_counts = [1]

    def handle_roll_action(self, game, roll):
        [roll] = roll
        
        if roll == 6:
            game.ballpos = 100
            end_play(game)
        else:
            complete_pick_return(game)

class PickTouchbackChoiceActionHandler(ActionHandler):
    states = [State.PICK_TOUCHBACK_CHOICE]
    actions = [rspmodel.TouchbackChoiceAction]
        
    def handle_action(self, game, player, action):
        if action.choice == TouchbackChoice.TOUCHBACK:
            game.result += [rspmodel.TouchbackResult()]
            game.ballpos = 20
            complete_pick_return(game)
        else: # choice is RETURN
            game.state = State.PICK_RETURN
            game.actions[player] = ['ROLL']

class PatChoiceActionHandler(ActionHandler):
    states = [State.PAT_CHOICE]
    actions = [rspmodel.PatChoiceAction]

    def handle_action(self, game, player, action):
        game.ballpos = 95
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
            game.result += [ScoreResult(type = 'PAT_1')]
        
        end_pat(game)

class TwoPointConversionActionHandler(RspActionHandler):
    states = [State.EXTRA_POINT_2]

    def handle_rsp_action(self, game, winner):
        if winner == game.possession:
            game.score[game.possession] += 2
            game.result += [ScoreResult(type = 'PAT_2')]
        
        end_pat(game)