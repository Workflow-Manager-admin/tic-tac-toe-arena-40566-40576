from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from .auth import authenticate_user, create_access_token, get_password_hash, Token, get_current_user
from .models import User
from .state import users, add_user

app = FastAPI(
    title="FastAPI Tic Tac Toe API",
    description="Backend API for Tic Tac Toe game, with user authentication.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoint"},
        {"name": "auth", "description": "User authentication (register, login, whoami)"},
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
