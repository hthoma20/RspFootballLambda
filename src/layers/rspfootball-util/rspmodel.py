from enum import Enum
from typing import Literal, Optional, Union
from pydantic import BaseModel

class Player(str, Enum):
    home = 'home'
    away = 'away'

class State(str, Enum):
    COIN_TOSS = 'COIN_TOSS'
    KICKOFF_ELECTION = 'KICKOFF_ELECTION'
    KICKOFF_CHOICE = 'KICKOFF_CHOICE'
    KICKOFF = 'KICKOFF'
    ONSIDE_KICK = 'ONSIDE_KICK'
    TOUCHBACK_CHOICE = 'TOUCHBACK_CHOICE'
    KICK_RETURN = 'KICK_RETURN'
    KICK_RETURN_1 = 'KICK_RETURN_1'
    KICK_RETURN_6 = 'KICK_RETURN_6'
    FUMBLE = 'FUMBLE'
    PAT_CHOICE = 'PAT_CHOICE'
    EXTRA_POINT = 'EXTRA_POINT'
    EXTRA_POINT_2 = 'EXTRA_POINT_2'
    PLAY_CALL = 'PLAY_CALL'
    SHORT_RUN = 'SHORT_RUN'
    SHORT_RUN_CONT = 'SHORT_RUN_CONT'
    LONG_RUN = 'LONG_RUN'
    LONG_RUN_ROLL = 'LONG_RUN_ROLL'
    SHORT_PASS = 'SHORT_PASS'
    SHORT_PASS_CONT = 'SHORT_PASS_CONT'
    LONG_PASS = 'LONG_PASS'
    LONG_PASS_ROLL = 'LONG_PASS_ROLL'
    BOMB = 'BOMB'
    BOMB_ROLL = 'BOMB_ROLL'
    BOMB_CHOICE = 'BOMB_CHOICE'
    SACK_CHOICE = 'SACK_CHOICE'
    SACK_ROLL = 'SACK_ROLL'
    PICK_ROLL = 'PICK_ROLL'
    DISTANCE_ROLL = 'DISTANCE_ROLL'
    PICK_TOUCHBACK_CHOICE = 'PICK_TOUCHBACK_CHOICE'
    PICK_RETURN = 'PICK_RETURN'
    PICK_RETURN_6 = 'PICK_RETURN_6'
    GAME_OVER = 'GAME_OVER'

class Play(str, Enum):
    SHORT_RUN = 'SHORT_RUN'
    LONG_RUN = 'LONG_RUN'
    SHORT_PASS = 'SHORT_PASS'
    LONG_PASS = 'LONG_PASS'
    BOMB = 'BOMB'

class RspChoice(str, Enum):
    ROCK = 'ROCK'
    PAPER = 'PAPER'
    SCISSORS = 'SCISSORS'

class KickoffElectionChoice(str, Enum):
    KICK = 'KICK'
    RECIEVE = 'RECIEVE'

class KickoffChoice(str, Enum):
    REGULAR = 'REGULAR'
    ONSIDE = 'ONSIDE'

class TouchbackChoice(str, Enum):
    TOUCHBACK = 'TOUCHBACK'
    RETURN = 'RETURN'

class RollAgainChoice(str, Enum):
    ROLL = 'ROLL'
    HOLD = 'HOLD'

class PatChoice(str, Enum):
    ONE_POINT = 'ONE_POINT'
    TWO_POINT = 'TWO_POINT'

class SackChoice(str, Enum):
    SACK = 'SACK'
    PICK = 'PICK'

class RspAction(BaseModel):
    name: Literal['RSP'] = 'RSP'
    choice: RspChoice

class RollAction(BaseModel):
    name: Literal['ROLL'] = 'ROLL'
    count: int

class KickoffElectionAction(BaseModel):
    name: Literal['KICKOFF_ELECTION'] = 'KICKOFF_ELECTION'
    choice: KickoffElectionChoice

class KickoffChoiceAction(BaseModel):
    name: Literal['KICKOFF_CHOICE'] = 'KICKOFF_CHOICE'
    choice: KickoffChoice

class CallPlayAction(BaseModel):
    name: Literal['CALL_PLAY'] = 'CALL_PLAY'
    play: Play

class TouchbackChoiceAction(BaseModel):
    name: Literal['TOUCHBACK_CHOICE'] = 'TOUCHBACK_CHOICE'
    choice: TouchbackChoice

class RollAgainChoiceAction(BaseModel):
    name: Literal['ROLL_AGAIN_CHOICE'] = 'ROLL_AGAIN_CHOICE'
    choice: RollAgainChoice

class PatChoiceAction(BaseModel):
    name: Literal['PAT_CHOICE'] = 'PAT_CHOICE'
    choice: PatChoice

class SackChoiceAction(BaseModel):
    name: Literal['SACK_CHOICE'] = 'SACK_CHOICE'
    choice: SackChoice

Action = Union[RspAction, RollAction, KickoffElectionAction, KickoffChoiceAction, CallPlayAction, TouchbackChoiceAction, RollAgainChoiceAction, PatChoiceAction, SackChoiceAction]

class TurnoverType(str, Enum):
    DOWNS = 'DOWNS'
    PICK = 'PICK'
    FUMBLE = 'FUMBLE'

class RspResult(BaseModel):
    name: Literal['RSP'] = 'RSP'
    home: RspChoice
    away: RspChoice

class RollResult(BaseModel):
    name: Literal['ROLL'] = 'ROLL'
    player: Player
    roll: list[int]

class SafetyResult(BaseModel):
    name: Literal['SAFETY'] = 'SAFETY'

class GainResult(BaseModel):
    name: Literal['GAIN'] = 'GAIN'
    play: Play
    player: Player
    yards: int

class LossResult(BaseModel):
    name: Literal['LOSS'] = 'LOSS'
    play: Play
    player: Player
    yards: int

class TurnoverResult(BaseModel):
    name: Literal['TURNOVER'] = 'TURNOVER'
    type: TurnoverType

class OutOfBoundsPassResult(BaseModel):
    name: Literal['OOB_PASS'] = 'OOB_PASS'

class TouchbackResult(BaseModel):
    name: Literal['TOUCHBACK'] = 'TOUCHBACK'

Result = Union[RspResult, RollResult, SafetyResult, GainResult, LossResult, TurnoverResult, OutOfBoundsPassResult, TouchbackResult]

class Game(BaseModel):
    gameId: str
    version: int
    players: dict[Player, Optional[str]]
    state: State
    play: Optional[Play]
    possession: Optional[Player]
    ballpos: int
    firstDown: Optional[int]
    playCount: int
    down: int
    firstKick: Optional[Player]
    rsp: dict[Player, Optional[RspChoice]]
    roll: list[int]
    score: dict[Player, int]
    penalties: dict[Player, int]
    actions: dict[Player, list[str]]
    result: list[Result]

class ActionRequest(BaseModel):
    gameId: str
    user: str
    action: Action

class ListGamesQuery(BaseModel):
    available: bool = True
    user: Optional[str]

