from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

# PUBLIC_INTERFACE
class User(BaseModel):
    """This model represents a registered user."""
    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")

# PUBLIC_INTERFACE
class PlayerSymbol(str, Enum):
    """Enum for player symbols in the game."""
    X = "X"
    O = "O"

# PUBLIC_INTERFACE
class GameStatus(str, Enum):
    """Enum for possible game statuses."""
    WAITING_FOR_PLAYER = "WAITING_FOR_PLAYER"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"

# PUBLIC_INTERFACE
class Move(BaseModel):
    """Represents a move in the tic tac toe game."""
    player_id: str = Field(..., description="User ID of player making the move")
    x: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    y: int = Field(..., ge=0, le=2, description="Column index (0-2)")
    symbol: PlayerSymbol = Field(..., description="X or O")

# PUBLIC_INTERFACE
class Game(BaseModel):
    """Holds info on a single game instance."""
    id: str = Field(..., description="Unique game identifier")
    player_x: Optional[str] = Field(None, description="User ID for player X")
    player_o: Optional[str] = Field(None, description="User ID for player O")
    board: List[List[Optional[PlayerSymbol]]] = Field(..., description="3x3 game board state")
    status: GameStatus = Field(..., description="Current game status")
    move_history: List[Move] = Field(default_factory=list, description="List of moves played")
    winner: Optional[str] = Field(None, description="User ID of the winner (if game finished)")
