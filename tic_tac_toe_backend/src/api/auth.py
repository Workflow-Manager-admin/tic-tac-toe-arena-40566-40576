from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .state import users, get_user
from .models import User

# Secret and algorithm (for MVP, fixed values - in production, use environment variables)
SECRET_KEY = "super-secret-key"  # In prod: use os.getenv
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# CryptContext for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# PUBLIC_INTERFACE
class Token(BaseModel):
    """Returned on successful login."""
    access_token: str
    token_type: str

# PUBLIC_INTERFACE
class TokenData(BaseModel):
    """Data inside access token."""
    user_id: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[User]:
    # Find user by username (MVP: by looping; in DB, would index)
    user = next((u for u in users.values() if u.username == username), None)
    if not user:
        return None
    hashed = getattr(user, "hashed_password", None)
    if not hashed or not verify_password(password, hashed):
        return None
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency: gets the currently authenticated user, or raises if invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user
