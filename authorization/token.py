from .db_connection import db


def validate_token(token: str):
    """
    Validate token
    :param token: token to validate
    :return: User_id if token is valid, 0 (false) if token is invalid
    """
    sql = f"SELECT user_id, username, email, value FROM user LEFT JOIN token ON " \
          f"token.user_id = user.id WHERE token.value='{token}'"
    result = db.fetch_one(sql=sql)
    if result is None:
        return None
    else:
        return {"username": result[1], "email": result[2]}
