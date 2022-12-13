from datetime import datetime, timedelta
from fastapi import HTTPException, status, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from jose import JWTError, jwt
from .token import validate_token
from .db_connection import db
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter()


class Token(BaseModel):
    """
    Token model
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Token data model
    """
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_user_id_by_username(username: str):
    sql = r"SELECT id FROM user WHERE username='%s'" % username
    result = db.fetch_one(sql=sql)
    if result is None:
        return None
    else:
        return {"id": result[0]}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str):
    """
    Validate if the user exists in the database
    :param username:
    :return: None if the user does not exist, otherwise return User Object
    """
    sql = r"SELECT email FROM user WHERE username='%s'" % username
    result = db.fetch_one(sql=sql)
    if result is None:
        return None
    else:
        return User(username=username, email=result[0])


def authenticate_user(username: str, password: str):
    """
    Validate username and password, convert password to hashed password
    :param username:
    :param password:
    :return:
    """
    user = get_user(username)
    if user is None:
        return False
    if not verify_password(password, get_password_hash(password)):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def handle_auth_header(request: Request):
    """
    Handle the authorization header
    :param request: HTTP request object
    :return:
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        # If there is no authorization header, return None as no authorization
        return None
    else:
        # Handle the authorization header
        current_session_auth_header = auth_header.split(" ")
        if len(current_session_auth_header) != 2:
            return None
        else:
            current_session_auth_method = current_session_auth_header[0]
            current_session_auth_value = current_session_auth_header[1]
            if current_session_auth_method == "Bearer":
                try:
                    user = await get_current_user(token=current_session_auth_value)
                    return {"username": user.username, "email": user.email}
                except HTTPException:
                    return None
            elif current_session_auth_method == "token":
                return validate_token(current_session_auth_value)
            else:
                return None


async def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@router.post("/token", tags=["jwt"])
async def login_for_access_token(request_body: Request):
    """
    Login for access token
    :param request_body: JSON body, requires username and password field
    :return: JSON body, access_token (JWT token) and token_type (bearer)
    """
    request_json = await request_body.json()
    user = authenticate_user(request_json.get("username"), request_json.get("password"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me/", tags=["jwt"])
async def read_users_me(current_user_request: Request):
    """
    Read current login user
    :param current_user_request:
    :return: return json object of current user's username and email
    """
    auth_result = await handle_auth_header(current_user_request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")
    else:
        return auth_result


@router.post("/users/register", tags=["jwt"])
async def register(request_body: Request):
    """
    Register a new user
    :param request_body: JSON body, requires username, password and email field
    :return: System message via JSON body
    """
    request_json = await request_body.json()
    username = request_json.get("username")
    password = request_json.get("password")
    email = request_json.get("email")
    username_check = get_user(username)
    if username_check is None:
        hashed_password = get_password_hash(password)
        sql = r"INSERT INTO user (username, password, email) VALUES ('%s', '%s', '%s')" \
              % (username, hashed_password, email)
        db.execute(sql=sql)
        return {"message": "Register successfully"}
    else:
        return {"message": "Username already exists"}


@router.post("/delete-default-user", tags=["jwt"])
async def delete_default_user(request: Request):
    """
    Delete default user
    :param request: JSON body, requires username and password field
    :return: System message via JSON body
    """
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")
    username = auth_result["username"]
    if username == "ghrp-admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN_UNAUTHORIZED, detail="You must login with your own "
                                                                                       "account")
    else:
        sql = r"DELETE FROM user WHERE username='ghrp-admin'"
        db.execute(sql=sql)
        return {"message": "Delete user successfully"}
