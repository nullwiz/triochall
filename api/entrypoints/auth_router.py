from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated
from api.entrypoints import schemas
from api.domain.enums import UserRole
from api.bootstrap import bootstrap
from api.service_layer.messagebus import MessageBus
from api.domain import commands
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from api.utils.hashoor import create_access_token
from api.utils.hashoor import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from datetime import timedelta
from jose import JWTError, jwt

auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_bus() -> MessageBus:
    return bootstrap()


@auth_router.post("/token", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    bus: MessageBus = Depends(get_bus),
):
    cmd = commands.AuthenticateUser(
        email=form_data.username, password=form_data.password
    )
    user = await bus.handle(cmd)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# These functions are the middleware necessary for Depends()
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    bus: MessageBus = Depends(get_bus),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
        token_email = token_data.email
    except JWTError:
        raise credentials_exception
    if token_email is None:
        raise credentials_exception
    cmd = commands.GetUserByEmail(email=token_email)
    user = await bus.handle(cmd)
    if user is None:
        raise credentials_exception
    return user


async def get_current_manager(
    token: Annotated[str, Depends(oauth2_scheme)],
    bus: MessageBus = Depends(get_bus),
):
    user = await get_current_user(token, bus)
    if user.role.value != UserRole.MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )
    return user


async def get_current_customer(
    token: Annotated[str, Depends(oauth2_scheme)],
    bus: MessageBus = Depends(get_bus),
):
    user = await get_current_user(token, bus)
    if user.role.value != UserRole.CUSTOMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )
    return user


@auth_router.get("/users/me/", response_model=schemas.User, tags=["General"])
async def read_users_me(current_user=Depends(get_current_user)):
    return current_user
