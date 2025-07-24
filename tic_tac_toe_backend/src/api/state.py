from typing import Dict, List, Optional
from uuid import uuid4

from .models import User, Game, Move, GameStatus

# In-memory 'tables'
users: Dict[str, User] = {}
games: Dict[str, Game] = {}

# PUBLIC_INTERFACE
def add_user(username: str) -> User:
    """Adds a new user and returns the User object."""
    user_id = str(uuid4())
    user = User(id=user_id, username=username)
    users[user_id] = user
    return user

# PUBLIC_INTERFACE
def get_user(user_id: str) -> Optional[User]:
    """Retrieves a user by their user_id."""
    return users.get(user_id)

# PUBLIC_INTERFACE
def add_game(player_x_id: str) -> Game:
    """Creates a new game with the given player as X, waits for O."""
    game_id = str(uuid4())
    empty_board = [[None for _ in range(3)] for _ in range(3)]
    game = Game(
        id=game_id,
        player_x=player_x_id,
        player_o=None,
        board=empty_board,
        status=GameStatus.WAITING_FOR_PLAYER,
        move_history=[],
        winner=None
    )
    games[game_id] = game
    return game

# PUBLIC_INTERFACE
def join_game(game_id: str, player_o_id: str) -> Optional[Game]:
    """Joins an existing game as player O, changing its status to IN_PROGRESS."""
    game = games.get(game_id)
    if game and game.player_o is None:
        game.player_o = player_o_id
        game.status = GameStatus.IN_PROGRESS
        return game
    return None

# PUBLIC_INTERFACE
def get_game(game_id: str) -> Optional[Game]:
    """Retrieves a game by game_id."""
    return games.get(game_id)

# PUBLIC_INTERFACE
def record_move(game_id: str, move: Move) -> Optional[Game]:
    """Records a move in the move history for the given game."""
    game = games.get(game_id)
    if not game:
        return None
    game.move_history.append(move)
    game.board[move.x][move.y] = move.symbol
    return game

# PUBLIC_INTERFACE
def list_users() -> List[User]:
    """Returns a list of all users."""
    return list(users.values())

# PUBLIC_INTERFACE
def list_games() -> List[Game]:
    """Returns a list of all games."""
    return list(games.values())
