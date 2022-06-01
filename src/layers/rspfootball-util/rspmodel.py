from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel

class Player(str, Enum):
    HOME = 'home'
    AWAY = 'away'

class State(str, Enum):
    COIN_TOSS = 'COIN_TOSS'
    KICKOFF_ELECTION = 'KICKOFF_ELECTION' # whether to kick or recieve
    KICKOFF_CHOICE = 'KICKOFF_CHOICE' # whether to onside kick
    KICKOFF = 'KICKOFF'
    ONSIDE_KICK = 'ONSIDE_KICK'
    TOUCHBACK_CHOICE = 'TOUCHBACK_CHOICE' # whether to take a knee or run
    KICK_RETURN = 'KICK_RETURN' # rolling from a kickoff or punt
    KICK_RETURN_1 = 'KICK_RETURN_1' # a 1 was rolled, choose to roll again
    KICK_RETURN_6 = 'KICK_RETURN_6' # a 6 was rolled, roll again

    FUMBLE = 'FUMBLE'

    PAT_CHOICE = 'PAT_CHOICE'
    EXTRA_POINT = 'EXTRA_POINT'
    EXTRA_POINT_2 = 'EXTRA_POINT_2'

    PLAY_CALL = 'PLAY_CALL'
    SHORT_RUN = 'SHORT_RUN'
    SHORT_RUN_CONT = 'SHORT_RUN_CONT'

    SACK_ROLL = 'SACK_ROLL'

    GAME_OVER = 'GAME_OVER'

class Play(str, Enum):
    SHORT_RUN = 'SHORT_RUN'

class RspChoice(str, Enum):
    ROCK = 'ROCK'
    PAPER = 'PAPER'
    SCISSORS = 'SCISSORS'

class RspResult(BaseModel):
    name: Literal['RSP'] = 'RSP'
    home: RspChoice
    away: RspChoice

class RollResult(BaseModel):
    name: Literal['ROLL'] = 'ROLL'
    roll: list[int]

class SafetyResult(BaseModel):
    name: Literal['SAFETY'] = 'SAFETY'

Result = Union[RspResult, RollResult, SafetyResult]

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


class RspAction(BaseModel):
    name: Literal['RSP']
    choice: RspChoice

class RollAction(BaseModel):
    name: Literal['ROLL']
    count: int

class KickoffElectionChoice(str, Enum):
    KICK = 'KICK'
    RECIEVE = 'RECIEVE'

class KickoffElectionAction(BaseModel):
    name: Literal['KICKOFF_ELECTION']
    choice: KickoffElectionChoice

class KickoffChoice(str, Enum):
    REGULAR = 'REGULAR'
    ONSIDE = 'ONSIDE'

class KickoffChoiceAction(BaseModel):
    name: Literal['KICKOFF_CHOICE']
    choice: KickoffChoice

class CallPlayAction(BaseModel):
    name: Literal['CALL_PLAY']
    play: Play

class TouchbackChoice(str, Enum):
    TOUCHBACK = 'TOUCHBACK'
    RETURN = 'RETURN'

class TouchbackChoiceAction(BaseModel):
    name: Literal['TOUCHBACK_CHOICE']
    choice: TouchbackChoice

class RollAgainChoice(str, Enum):
    ROLL = 'ROLL'
    HOLD = 'HOLD'

class RollAgainChoiceAction(BaseModel):
    name: Literal['ROLL_AGAIN_CHOICE']
    choice: RollAgainChoice

class PatChoice(str, Enum):
    ONE_POINT = 'ONE_POINT'
    TWO_POINT = 'TWO_POINT'

class PatChoiceAction(BaseModel):
    name: Literal['PAT_CHOICE']
    choice: PatChoice

Action = Union[RspAction, KickoffElectionAction, RollAction, KickoffChoiceAction, CallPlayAction,
    TouchbackChoiceAction, RollAgainChoiceAction, PatChoiceAction]

class ActionRequest(BaseModel):
    gameId: str
    user: str
    action: Action
