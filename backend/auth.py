import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .models import Student

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'devsecret')
JWT_ALGO = 'HS256'

def get_password_hash(password: str) -> str:
    # bcrypt has a 72-byte input limit; truncate UTF-8 bytes to avoid ValueError
    if isinstance(password, str):
        pw_bytes = password.encode('utf-8')
        if len(pw_bytes) > 72:
            pw_bytes = pw_bytes[:72]
        # decode ignoring errors, so we never get a partial character
        password = pw_bytes.decode('utf-8', 'ignore')
    else:
        # If password is bytes, truncate directly
        password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    # Ensure the same truncation logic when verifying
    if isinstance(plain_password, str):
        pw_bytes = plain_password.encode('utf-8')
        if len(pw_bytes) > 72:
            pw_bytes = pw_bytes[:72]
        plain_password = pw_bytes.decode('utf-8', 'ignore')
    else:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: str, role: str = "student", expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": subject, "role": role}
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)
    return encoded_jwt

def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def require_student(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")
    role = payload.get("role")
    if role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return payload

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = None):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")
    user_email = payload.get('sub')
    if not user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    # db lookup if provided
    if db is not None:
        user = db.query(Student).filter(Student.email == user_email).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    return {"email": user_email}
