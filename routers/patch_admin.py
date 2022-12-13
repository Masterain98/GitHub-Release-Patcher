"""
patch_admin.py contains router that handles patch data from GitHub API.
Patch data will be stored in database.
Some operation tool APIs are also included in this router.
"""
import json
import requests
from fastapi import APIRouter, HTTPException, status, Request
from authorization.jwt import handle_auth_header
from authorization.db_connection import db
import routers.repo

router = APIRouter(
    prefix="/patch/admin",
)


def find_repo_tag_from_db(repo_id: int, tag_name: str):
    """
    Check if tag_name of a specific repo exists in database.
    :param repo_id: The repo_id of the searching repository.
    :param tag_name: The target tag_name.
    :return: True if tag_name exists, False if not.
    """
    sql = r"SELECT * FROM patch_history WHERE repo_id='%s' AND tag_name='%s'" % (repo_id, tag_name)
    result = db.fetch_one(sql=sql)
    if result is None:
        return False
    else:
        return True


def update_repo_patch(repo_name: str):
    """
    Update patch the latest release data of a specific repository.
    :param repo_name: full name of the repository, including owner name. i.e. "owner_name/repo_name"
    :return: a dict with the result message
    """
    github_api_url = "https://api.github.com/repos/%s/releases/latest" % repo_name
    response = json.loads(requests.get(github_api_url).text)
    if "message" in response.keys():
        # This happens when there's no stable release in the repository.
        return {"result": "No release"}
    repo_id = routers.repo.get_repo_info_by_name(repo_name=repo_name)["id"]
    release_description = response["body"].replace("'", "\\'").replace('"', '\\"')
    tag_name = response["tag_name"]
    publish_time = response["published_at"].replace("T", " ").replace("Z", "")  # UTC Time

    try:
        client_download_url = response["assets"][0]["browser_download_url"]
    except IndexError:
        return {"result": "No attachment for this release"}
    if not find_repo_tag_from_db(repo_id=repo_id, tag_name=tag_name):
        sql = r"INSERT INTO patch_history (repo_id, publish_time, tag_name, body, download_url, is_prerelease) " \
              r"VALUES ('%s', '%s','%s', '%s', '%s', %s)" % (repo_id, publish_time, tag_name, release_description,
                                                             client_download_url, 1)
        result = db.execute(sql=sql)
        if result:
            return {"result": "Update successful"}
        else:
            return {"result": "Update failed"}
    else:
        return {"result": "No update"}


@router.post("/make-all-patch-cache", tags=["patch-admin"])
async def make_all_repo_patch_cache(request: Request):
    """
    Update the latest patch record of all repositories in database.
    :param request: HTTP request object, to validate the user
    :return: A dict with the result message.
    """
    auth_result = await handle_auth_header(request=request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    function_result = {}
    repo_list = routers.repo.list_repo_from_db()
    for repo_name in repo_list:
        this_result = update_repo_patch(repo_name=repo_name)
        function_result[repo_name] = this_result["result"]
    return function_result


@router.post("/{repo_friendly_name}/make", tags=["patch-admin"])
async def make_repo_patch_cache(request: Request, repo_friendly_name: str):
    """
    Update the latest patch record of a specific repository.
    :param repo_friendly_name:
    :param request: HTTP request object, to validate the user and transfer JSON body data.
    :return: A dict with the result message.
    """
    auth_result = await handle_auth_header(request=request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    repo_name = routers.repo.get_repo_info_by_friendly_name(friendly_name=repo_friendly_name)["repo_name"]
    return update_repo_patch(repo_name=repo_name)


@router.post("/update-cn-patch-url", tags=["patch-admin"])
async def update_repo_cn_patch_url(request: Request):
    """
    Update the Chinese patch download URL of a specific repository by friendly name.
    For CN users, this recorded URL will overwrite the original GitHub download URL.
    :return: A dict with the result message.
    """
    # Handle authorization
    auth_result = await handle_auth_header(request=request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    # Handle JSON body
    request_json_body = await request.json()
    friendly_name = request_json_body.get("friendly_name")
    url = request_json_body.get("url")
    channel = request_json_body.get("channel")

    # Determine which DB column is associated
    if channel == "stable":
        affected_column_name = "cn_url"
    elif channel == "beta":
        affected_column_name = "cn_url_beta"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid channel")

    # Check if there's a CN patch record in database already
    existing_checker = r"SELECT * FROM cn_boost_patch INNER JOIN repo_list " \
                       r"ON cn_boost_patch.repo_id=repo_list.id WHERE repo_list.friendly_name='%s'" % friendly_name
    existing_result = db.fetch_one(sql=existing_checker)
    if existing_result:
        # If there's a record, update it.
        if url.lower() == "null":
            sql = r"UPDATE cn_boost_patch SET %s=%s WHERE repo_id= %s" % (
                affected_column_name, 'NULL', existing_result[0])
        else:
            sql = r"UPDATE cn_boost_patch SET %s='%s' WHERE repo_id='%s'" % (
                affected_column_name, url, existing_result[0])
        result = db.execute(sql=sql)
        if result:
            return {"result": "Update successful"}
        else:
            return {"result": "Update failed"}
    else:
        # If there's no record, create a new one.
        sql = r"INSERT INTO cn_boost_patch (repo_id, %s) VALUES ('%s', '%s')" \
              % (affected_column_name,
                 routers.repo.get_repo_info_by_friendly_name(friendly_name=friendly_name)["id"],
                 url)
        result = db.execute(sql=sql)
        if result:
            return {"result": "Add successful"}
        else:
            return {"result": "Add failed"}


@router.get("/{repo_friendly_name}/purge", tags=["patch-admin"])
async def purge_repo_patch(repo_friendly_name: str, request: Request = None):
    """
    Force purge the patch record of a specific repository. Add all releases to the patch history DB.
    **This function is different from the update_repo_patch function, which only fetches the latest release**
    **This function will fetch all releases, including pre-release records**
    :param repo_friendly_name: Friendly name of the repository.
    :param request: Dependency injection of current user.
    :return: A dict with the result message.
    """
    # Handle authorization
    if request is None:
        print("local call")
    else:
        auth_result = await handle_auth_header(request=request)
        if auth_result is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    # Initial the error message string
    error_message = ""

    # Delete all current patch records
    sql = r"DELETE patch_history FROM patch_history INNER JOIN repo_list " \
          r"ON repo_list.id=patch_history.repo_id WHERE repo_list.friendly_name='%s'" % repo_friendly_name
    db.execute(sql=sql)

    # Fetch all releases from GitHub API, reverse the list to make the oldest release on top
    # So the latest release can get the highest ID in the database
    repo_name = routers.repo.get_repo_info_by_friendly_name(friendly_name=repo_friendly_name)["repo_name"]
    github_api_url = "https://api.github.com/repos/%s/releases" % repo_name
    repo_id = routers.repo.get_repo_info_by_name(repo_name=repo_name)["id"]
    response = json.loads(requests.get(github_api_url).text)
    if type(response) is dict:
        error_message += str(response)
    else:
        response.reverse()
        for release in response:
            if len(release["assets"]) == 0:
                continue
            else:
                release_description = release["body"].replace("'", "\\'").replace('"', '\\"')
                tag_name = release["tag_name"]
                download_url = release["assets"][0]["browser_download_url"]
                publish_time = release["published_at"].replace("T", " ").replace("Z", "")
                if release["prerelease"]:
                    is_prerelease = 1
                else:
                    is_prerelease = 0
                sql = r"INSERT INTO patch_history (repo_id, publish_time, tag_name, body, download_url, " \
                      r"is_prerelease) VALUES ('%s', '%s', '%s', '%s', '%s', %s)" % (repo_id, publish_time, tag_name,
                                                                                     release_description, download_url,
                                                                                     is_prerelease)
                try:
                    db.execute(sql=sql)
                except Exception as e:
                    error_message += str(e) + "\n"

    if error_message:
        return {"result": "Purge request sent", "error_message": error_message}
    return {"result": "Purge done"}


@router.post("/{repo_friendly_name}/update-all-release", tags=["patch-admin"])
async def update_repo_all_release(friendly_name: str, request: Request):
    """
    Fetch all release data from GitHub API and update the database.
    :param friendly_name: Friendly name of the repository.
    :param request: Dependency injection of current user.
    :return: A dict with the result message. Will return error message if any.
    """
    # Handle authorization
    auth_result = await handle_auth_header(request=request)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization")

    # Initial the error message string
    error_message = ""

    # Fetch all releases from GitHub API, reverse the list to make the oldest release on top
    # So the latest release can get the highest ID in the database
    repo_name = routers.repo.get_repo_info_by_friendly_name(friendly_name=friendly_name)["repo_name"]
    github_api_url = "https://api.github.com/repos/%s/releases" % repo_name
    repo_id = routers.repo.get_repo_info_by_name(repo_name=repo_name)["id"]
    response = json.loads(requests.get(github_api_url).text)
    if type(response) is dict:
        error_message += str(response)
    else:
        response.reverse()
        for release in response:
            if len(release["assets"]) == 0:
                continue
            else:
                tag_name = release["tag_name"]
                existing_sql = "SELECT * FROM patch_history WHERE repo_id='%s' AND tag_name='%s'" % (repo_id, tag_name)
                existing_result = db.fetch_one(sql=existing_sql)
                if existing_result:
                    continue
                else:
                    release_description = release["body"].replace("'", "\\'").replace('"', '\\"')
                    download_url = release["assets"][0]["browser_download_url"]
                    publish_time = release["published_at"].replace("T", " ").replace("Z", "")
                    if release["prerelease"]:
                        is_prerelease = 1
                    else:
                        is_prerelease = 0
                    sql = r"INSERT INTO patch_history (repo_id, publish_time, tag_name, body, " \
                          r"download_url, is_prerelease) " \
                          r"VALUES ('%s', '%s', '%s', '%s', '%s', %s)" % (repo_id, publish_time, tag_name,
                                                                          release_description, download_url,
                                                                          is_prerelease)
                    try:
                        db.execute(sql=sql)
                    except Exception as e:
                        error_message += str(e) + "\n"

    if error_message:
        return {"result": "Update request sent", "error_message": error_message}
    return {"result": "Update done"}


@router.get("/list-latest", tags=["patch-admin"])
async def list_latest_release():
    """
    List all latest release of each repository.
    :return: A list of dict with the latest release of each repository.
    """
    sql = r"SELECT r.friendly_name, p.tag_name, p.body " \
          r"FROM patch_history p LEFT JOIN repo_list r ON p.repo_id = r.id " \
          r"JOIN(SELECT MAX(p.id) maxid " \
          r"FROM patch_history p " \
          r"LEFT JOIN repo_list r ON r.id = p.repo_id " \
          r"GROUP BY r.friendly_name) maxlist " \
          r"ON maxlist.maxid = p.id"
    result = [x for x in db.fetch_all(sql=sql)]
    return {"result": result}


@router.get("/list-cn-boost-settings", tags=["patch-admin"])
async def list_cn_boost_settings():
    """
    List all CN boost settings.
    :return: A list of dict with the CN boost settings.
    """
    sql = r"SELECT r.friendly_name, c.cn_url, c.cn_url_beta FROM repo_list r " \
          r"LEFT JOIN cn_boost_patch c ON c.repo_id = r.id"
    result = [x for x in db.fetch_all(sql=sql)]
    return {"result": result}
