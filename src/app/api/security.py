from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer


security = HTTPBearer()


def validate_token(token: str = Depends(security)):
    # In production, validate the token against a trusted source (e.g., JWT)
    if token.credentials != "dev-secret":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token