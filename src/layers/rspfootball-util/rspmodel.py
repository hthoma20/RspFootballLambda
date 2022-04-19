from enum import Enum
from typing import Optional

from pydantic import BaseModel

class Player(str, Enum):
    HOME = 'home'
    AWAY = 'away'

class State(str, Enum):
    RSP = 'RSP'

class Play(str, Enum):
    COIN_TOSS = 'COIN_TOSS'

class RspChoice(str, Enum):
    ROCK = 'ROCK'
    PAPER = 'PAPER'
    SCISSORS = 'SCISSORS'

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
