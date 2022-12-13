from fastapi import APIRouter, HTTPException, status, Request
from authorization.jwt import handle_auth_header
from authorization.db_connection import db
import string
import routers.patch_admin

router = APIRouter(
    prefix="/repo",
)


def list_repo_from_db():
    """
    List all repo from database
    :return: all repo name in db as a list
    """
    sql = r"SELECT repo_name FROM repo_list"
    return [repo[0] for repo in db.fetch_all(sql=sql)]


def get_repo_info_by_name(repo_name: str):
    """
    Get repo info by repo name (including id, repo_name, friendly_name)
    :param repo_name: repository full name (including owner, i.e. "owner_name/repo_name")
    :return: None if repository not found, a dict with repo info if found.
    """
    sql = r"SELECT * FROM repo_list WHERE repo_name='%s'" % repo_name
    result = db.fetch_one(sql=sql)
    if result is None:
        return None
    else:
        return {
            "id": result[0],
            "repo_name": result[1],
            "friendly_name": result[2],
        }


@router.get("/info/{repo_friendly_name}", tags=["repo"])
def get_repo_info_by_friendly_name(friendly_name: str):
    """
    Get repo info by repo friendly name (including id, repo_name, friendly_name)
    :param friendly_name: friendly name of the repo, set by user
    :return: raise HTTPException 404 Error if repo not found, a dict with repo info if found.
    """
    sql = r"SELECT * FROM repo_list WHERE friendly_name='%s'" % friendly_name
    result = db.fetch_one(sql=sql)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    else:
        return {"id": result[0], "repo_name": result[1], "friendly_name": result[2]}


@router.get("/", tags=["repo"])
async def get_repo_list():
    """
    Get all repo list. HTTP request version of list_repo_from_db()
    :return: Raise HTTPException 404 Error if no repo found, a list of repo name if found.
    """
    result = list_repo_from_db()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No repository found")
    else:
        return {"repo_list": result}


@router.post("/new", tags=["repo"])
async def add_new_repo_to_patch_system(request: Request):
    """
    Add new repository to patch system
    :param request: JSON request body includes repo_name and friendly_name:
            repo_name: repository full name (including owner, i.e. "owner_name/repo_name")
            friendly_name: a friendly name for the repo, characters are not allowed
    :return: A dict with message
    """
    # Handle login session
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    # Handle request body
    request_body_json = await request.json()
    repo_name = request_body_json.get("repo_name")
    friendly_name = request_body_json.get("friendly_name")

    # Handle function
    repo_name = repo_name.strip()  # Remove leading and trailing spaces
    friendly_name = friendly_name.strip().replace(string.punctuation, "")  # Remove punctuation
    repo_name_checker = r"SELECT * FROM repo_list WHERE repo_name='%s'" % repo_name
    repo_name_checker_result = db.fetch_one(sql=repo_name_checker)
    repo_friendly_name_checker = r"SELECT * FROM repo_list WHERE friendly_name='%s'" % friendly_name
    repo_friendly_name_checker_result = db.fetch_one(sql=repo_friendly_name_checker)
    if repo_name_checker_result is not None or repo_friendly_name_checker_result is not None:
        # If repo name or friendly name already exists, raise HTTPException 400 Error
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository already exists")
    sql = r"INSERT INTO repo_list (repo_name, friendly_name) VALUES ('%s', '%s')" % (repo_name, friendly_name)
    db.execute(sql=sql)
    purge_result = await routers.patch_admin.purge_repo_patch(repo_friendly_name=friendly_name)
    if db is not None:
        return {"message": "Repository added successfully", "purge_result": purge_result["result"]}
    else:
        # MysqlCoon class will print the error message
        raise HTTPException(status_code=status.HTTP_400_NOT_FOUND, detail="Database error")


@router.post("/delete", tags=["repo"])
async def delete_repo_from_patch_system(request: Request):
    """
    Delete repository from patch system
    :param request: JSON request body includes repo_name and friendly_name:
            repo_name: repository full name (including owner, i.e. "owner_name/repo_name")
            friendly_name: a friendly name for the repo, characters are not allowed
    :return: A dict with message
    """
    # Handle login session
    auth_result = await handle_auth_header(request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    # Handle request body
    request_body_json = await request.json()
    json_key = request_body_json.keys()
    if "friendly_name" in json_key:
        friendly_name = request_body_json.get("friendly_name")
        # Handle function
        # Delete repo's patch first
        try:
            patch_delete_sql = r"DELETE p FROM `patch_history` p LEFT JOIN repo_list r ON p.repo_id = r.id" \
                               r"WHERE friendly_name = '%s'" % friendly_name
            db.execute(sql=patch_delete_sql)
            # Delete cn_boost_patch record
            cn_boost_patch_delete_sql = r"DELETE c FROM `cn_boost_patch` c LEFT JOIN repo_list r " \
                                        r"ON c.repo_id = r.id WHERE friendly_name = '%s'" % friendly_name
            db.execute(sql=cn_boost_patch_delete_sql)
            # Delete repo record
            repo_delete_sql = r"DELETE FROM repo_list WHERE friendly_name = '%s'" % friendly_name
            db.execute(sql=repo_delete_sql)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_NOT_FOUND, detail="Database error")
        return {"message": "Repository deleted successfully"}
    elif "repo_name" in json_key:
        repo_name = request_body_json.get("repo_name")
        # Handle function
        try:
            patch_delete_sql = r"DELETE p FROM `patch_history` p LEFT JOIN repo_list r ON p.repo_id = r.id " \
                               r"WHERE repo_name = '%s'" % repo_name
            db.execute(sql=patch_delete_sql)
            # Delete cn_boost_patch record
            cn_boost_patch_delete_sql = r"DELETE c FROM `cn_boost_patch` c LEFT JOIN repo_list r " \
                                        r"ON c.repo_id = r.id WHERE repo_name = '%s'" % repo_name
            db.execute(sql=cn_boost_patch_delete_sql)
            # Delete repo record
            repo_delete_sql = r"DELETE FROM repo_list WHERE repo_name = '%s'" % repo_name
            db.execute(sql=repo_delete_sql)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_NOT_FOUND, detail="Database error")
        return {"message": "Repository deleted successfully"}
