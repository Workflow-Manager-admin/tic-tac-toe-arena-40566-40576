from fastapi import FastAPI, Depends, HTTPException, status, Body, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List, Optional

from .auth import authenticate_user, create_access_token, get_password_hash, Token, get_current_user
from .models import User, Game, Move, GameStatus, PlayerSymbol
from .state import (
    users, add_user, add_game, join_game,
    get_game, record_move, games
)

app = FastAPI(
    title="FastAPI Tic Tac Toe API",
    description="Backend API for Tic Tac Toe game, with user authentication.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoint"},
        {"name": "auth", "description": "User authentication (register, login, whoami)"},
        {"name": "game", "description": "Game management and gameplay"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# ========================== AUTH/USER ENDPOINTS ==========================

# PUBLIC_INTERFACE
class RegisterRequest(BaseModel):
    """Payload for registering new user."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

@app.post("/register", summary="Register a new user", tags=["auth"], response_model=User, status_code=201)
def register(data: RegisterRequest = Body(...)):
    """
    Registers a new user with the provided username and password.
    - **username**: desired username (must be unique)
    - **password**: password
    Returns the created user object.
    """
    # Check if username is taken
    if any(u.username == data.username for u in users.values()):
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_pw = get_password_hash(data.password)
    user = add_user(data.username)
    user.hashed_password = hashed_pw
    users[user.id] = user # update with password
    return user

@app.post("/login", summary="Authenticate and get JWT", tags=["auth"], response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticates the user and returns a JWT access token.
    - Uses OAuth2PasswordRequestForm ("username", "password" as form fields)
    - Returns: Token(access_token, token_type)
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, token_type="bearer")

@app.get("/me", summary="Get current user info", tags=["auth"], response_model=User)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Returns user information for the currently authenticated user.
    """
    return current_user

# ========================== GAME ENDPOINTS ==========================
# Helper logic for turn, move validation, win/tie

def get_player_symbol(game: Game, user: User) -> Optional[PlayerSymbol]:
    if game.player_x == user.id:
        return PlayerSymbol.X
    if game.player_o == user.id:
        return PlayerSymbol.O
    return None

def is_valid_move(game: Game, move: Move, current_user: User) -> (bool, str):
    # Ensure cell is within bounds is already checked by Pydantic schema.
    # Ensure cell is empty
    if game.board[move.x][move.y] is not None:
        return False, "Cell is already occupied"
    # Ensure it's player's turn
    if len(game.move_history) == 0:
        # X always starts
        expected = PlayerSymbol.X
    else:
        last = game.move_history[-1]
        expected = PlayerSymbol.O if last.symbol == PlayerSymbol.X else PlayerSymbol.X
    player_symbol = get_player_symbol(game, current_user)
    if player_symbol is None:
        return False, "You are not a player in this game"
    if move.symbol != player_symbol:
        return False, "Invalid symbol for your user"
    if move.symbol != expected:
        return False, f"It is {expected}'s turn"
    if game.status != GameStatus.IN_PROGRESS:
        return False, f"Game is not in progress (current status: {game.status})"
    return True, ""

def check_win(board: List[List[Optional[PlayerSymbol]]]) -> Optional[PlayerSymbol]:
    # Rows, columns, diagonals
    for i in range(3):
        # Check rows
        if board[i][0] == board[i][1] == board[i][2] and board[i][0] is not None:
            return board[i][0]
        # Check cols
        if board[0][i] == board[1][i] == board[2][i] and board[0][i] is not None:
            return board[0][i]
    # Diagonals
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] is not None:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] is not None:
        return board[0][2]
    return None

def is_tie(board: List[List[Optional[PlayerSymbol]]]) -> bool:
    for row in board:
        for cell in row:
            if cell is None:
                return False
    # If all cells filled and no winner
    return True

# PUBLIC_INTERFACE
class StartGameRequest(BaseModel):
    """Request to start a new game."""
    # No fields
    pass

# PUBLIC_INTERFACE
class JoinGameRequest(BaseModel):
    """Request to join an existing game."""
    game_id: str = Field(..., description="Game ID to join")

# PUBLIC_INTERFACE
class MoveRequest(BaseModel):
    """Request to make a move."""
    game_id: str = Field(..., description="Game ID to make move in")
    x: int = Field(..., ge=0, le=2, description="Row index [0-2]")
    y: int = Field(..., ge=0, le=2, description="Col index [0-2]")

@app.post("/games", summary="Start a new game", tags=["game"], status_code=201, response_model=Game)
def start_game(current_user: User = Depends(get_current_user)):
    """
    Starts a new game for the current user (as player X). Returns the created game object.
    """
    game = add_game(player_x_id=current_user.id)
    return game

@app.post("/games/{game_id}/join", summary="Join an existing game", tags=["game"], response_model=Game)
def join_existing_game(game_id: str = Path(..., description="ID of game to join"), current_user: User = Depends(get_current_user)):
    """
    Joins the specified game as player O.
    Returns the updated game object.
    """
    game = get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.player_x == current_user.id:
        raise HTTPException(status_code=400, detail="You are already in this game")
    if game.player_o is not None:
        raise HTTPException(status_code=400, detail="Game already has both players")
    updated = join_game(game_id, current_user.id)
    return updated

@app.post("/games/{game_id}/move", summary="Make a move", tags=["game"], response_model=Game)
def make_move(
    game_id: str = Path(..., description="ID of game"),
    move_req: MoveRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a move to the specified game. Handles validation, switches turn, and checks for win/tie.
    Returns the new game state.
    """
    game = get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    # Check if game is in progress
    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail=f"Game not in progress (status: {game.status})")
    # Determine player's symbol
    if game.player_x == current_user.id:
        symbol = PlayerSymbol.X
    elif game.player_o == current_user.id:
        symbol = PlayerSymbol.O
    else:
        raise HTTPException(status_code=403, detail="You are not a player in this game")
    move = Move(player_id=current_user.id, x=move_req.x, y=move_req.y, symbol=symbol)
    valid, reason = is_valid_move(game, move, current_user)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid move: {reason}")
    # Apply move
    record_move(game_id, move)
    # Check for winner/tie and update
    winner_symbol = check_win(game.board)
    if winner_symbol:
        game.status = GameStatus.FINISHED
        if winner_symbol == PlayerSymbol.X:
            game.winner = game.player_x
        else:
            game.winner = game.player_o
    elif is_tie(game.board):
        game.status = GameStatus.FINISHED
        game.winner = None # Tie
    return game

@app.get("/games/{game_id}", summary="Get game state", tags=["game"], response_model=Game)
def get_game_state(game_id: str = Path(..., description="ID of game"), current_user: User = Depends(get_current_user)):
    """
    Retrieves the current game state for the specified game, if current user is a player in it.
    """
    game = get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if current_user.id not in [game.player_x, game.player_o]:
        raise HTTPException(status_code=403, detail="You are not authorized to view this game")
    return game

@app.get("/games/my", summary="List current user's games", tags=["game"], response_model=List[Game])
def list_user_games(current_user: User = Depends(get_current_user)):
    """
    Returns a list of games for which the current user is a player.
    """
    my_games = [
        game
        for game in games.values()
        if (game.player_x == current_user.id or game.player_o == current_user.id)
    ]
    return my_games
