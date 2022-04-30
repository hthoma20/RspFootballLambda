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
    PLAY_CALL = 'PLAY_CALL'

RSP_STATES = [State.COIN_TOSS]

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

Result = Union[RspResult, RollResult]

class Game(BaseModel):
    gameId: str
    version: int
    players: dict[Player, Optional[str]]

    state: State
    play: Optional[Play]
    possession: Optional[Player]
    ballpos: int
    
    playCount: int
    down: int

    firstKick: Optional[Player]

    rsp: dict[Player, Optional[RspChoice]]
    roll: list[int]
    score: dict[Player, int]
    penalties: dict[Player, int]

    actions: dict[Player, list[str]]
    result: Optional[Result]


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
    ROLL = 'ROLL'

class TouchbackChoiceAction(BaseModel):
    name: Literal['TOUCHBACK_CHOICE']
    choice: TouchbackChoice

Action = Union[RspAction, KickoffElectionAction, RollAction, KickoffChoiceAction, CallPlayAction]

class ActionRequest(BaseModel):
    gameId: str
    user: str
    action: Action
