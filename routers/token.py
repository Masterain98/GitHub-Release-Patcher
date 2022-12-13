from fastapi import APIRouter, HTTPException, status, Request
from authorization.jwt import handle_auth_header, get_user_id_by_username
from authorization.db_connection import db
import string
import hashlib
import random
import time

router = APIRouter(
    prefix="/token",
)


@router.get("/new", tags=["token"])
async def generate_new_token(request: Request):
    """
    Generate a new token for user
    :param
    :return:
    """
    # Handle login session
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")
    user_id = get_user_id_by_username(auth_result["username"])["id"]

    valid_token = False
    # Generate new token
    while not valid_token:
        new_token = r''.join(random.choices(string.ascii_letters, k=16)) + str(int(time.time()))
        new_token = hashlib.sha256(bytes(new_token, 'utf-8')).hexdigest()
        token_validator = db.fetch_one(sql=r"SELECT * FROM token WHERE value='%s'" % new_token)
        if token_validator is None:
            valid_token = True

    # Insert new token into database
    sql = r"INSERT INTO token (value, user_id) VALUES ('%s', '%s')" % (new_token, user_id)
    sql_result = db.execute(sql=sql)
    return {"token": new_token, "message": str(sql_result)}


@router.get("/my", tags=["token"])
async def show_my_token(request: Request):
    """
    Show all token of current user
    :param
    :return:
    """
    # Handle login session
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")
    user_id = get_user_id_by_username(auth_result["username"])

    # Get all token of current user
    sql = r"SELECT value FROM token WHERE user_id='%s'" % user_id["id"]
    result = [x[0] for x in db.fetch_all(sql=sql)]
    if result is None:
        return {"message": "No token found"}
    else:
        return {"tokens": result}


@router.post("/delete", tags=["token"])
async def delete_token(request: Request):
    """
    Delete token
    :param request:
    :return:
    """
    # Handle login session
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")
    user_id = get_user_id_by_username(auth_result["username"])
    request_body_json = await request.json()
    requested_token = request_body_json.get("token")

    sql = r"SELECT value FROM token WHERE user_id='%s'" % user_id["id"]
    result = [x[0] for x in db.fetch_all(sql=sql)]
    if requested_token not in result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    else:
        sql = r"DELETE FROM token WHERE value='%s'" % requested_token
        db.execute(sql=sql)
        return {"message": "Token deleted"}
