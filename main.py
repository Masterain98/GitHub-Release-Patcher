from fastapi import FastAPI
from authorization import jwt
from authorization.db_connection import db
from routers import patch_admin, repo, patch, token
from config import INIT_PASSWORD


def initial_run():
    sql = r"SELECT * FROM user LIMIT 1"
    result = db.fetch_all(sql=sql)
    if len(list(result)) != 0:
        print("User table is not empty, skip default user creation")
        return None
    username = "ghrp-admin"
    password = INIT_PASSWORD
    hashed_password = jwt.get_password_hash(password)
    sql = r"INSERT INTO user (username, password, email) VALUES ('%s', '%s', '%s')" \
          % (username, hashed_password, "admin@admin.com")
    db.execute(sql=sql)
    print("Default user created")
    print("Username: ghrp-admin")
    print(f"Password: {INIT_PASSWORD}")


app = FastAPI()
initial_run()
app.include_router(jwt.router)
app.include_router(patch.router)
app.include_router(patch_admin.router)
app.include_router(repo.router)
app.include_router(token.router)


@app.get("/", tags=["index"])
async def hello_world():
    return {"message": "Patch system is running"}
