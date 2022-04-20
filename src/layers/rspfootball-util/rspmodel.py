from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel

class Player(str, Enum):
    HOME = 'home'
    AWAY = 'away'

class State(str, Enum):
    COIN_TOSS = 'COIN_TOSS'
    KICKOFF_ELECTION = 'KICKOFF_ELECTION' # whether to kick or recieve

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

Result = Union[RspResult]

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

Action = Union[RspAction]

class ActionRequest(BaseModel):
    gameId: str
    user: str
    action: Action
