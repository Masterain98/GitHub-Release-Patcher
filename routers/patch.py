"""
patch.py contains router that handles patch distribution.
User will fetch patch from this router.
"""
import time
from fastapi import APIRouter, HTTPException, status
from authorization.db_connection import db

router = APIRouter(
    prefix="/patch",
)

MEMORY_CACHE_TIME = 60
patch_info_memory_cache = {}
patch_info_memory_cache_update_time = int(time.time())
cn_patch_info_memory_cache = {}
cn_patch_info_memory_cache_update_time = int(time.time())


@router.get("/", tags=["patch"])
async def showing_patch_sys_msg():
    return {"message": "Patch system is running, admin privilege is disabled in this level."}


@router.get("/global/{friendly_name}/{channel}", tags=["patch"])
def get_repo_patch_by_friendly_name(friendly_name: str, channel: str):
    global patch_info_memory_cache, patch_info_memory_cache_update_time

    # Determine channel
    if channel == "stable":
        channel_code = 0
    elif channel == "beta":
        channel_code = 1
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid channel")

    if int(time.time()) - patch_info_memory_cache_update_time > MEMORY_CACHE_TIME or \
            friendly_name+"/"+channel not in patch_info_memory_cache.keys():
        select_sql = r"SELECT tag_name, body, download_url, publish_time FROM patch_history WHERE " \
                     r"repo_id =(SELECT id FROM repo_list WHERE friendly_name = '%s' AND is_prerelease=%s) " \
                     r"ORDER BY publish_time DESC LIMIT 1" % (friendly_name, channel_code)
        select_sql_result = db.fetch_one(sql=select_sql)
        if select_sql_result:
            result_dict = {
                "tag_name": select_sql_result[0],
                "body": select_sql_result[1],
                "browser_download_url": select_sql_result[2],
                "cache_time": select_sql_result[3]
            }
            patch_info_memory_cache[friendly_name+"/"+channel] = result_dict
            patch_info_memory_cache_update_time = int(time.time())
            return result_dict
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No patch found")
    else:
        return patch_info_memory_cache[friendly_name+"/"+channel]


@router.get("/cn/{friendly_name}/{channel}", tags=["patch"])
def get_repo_cn_patch_by_friendly_name(friendly_name: str, channel: str):
    global cn_patch_info_memory_cache, cn_patch_info_memory_cache_update_time

    # Determine channel
    if channel == "stable":
        channel_code = 0
    elif channel == "beta":
        channel_code = 1
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid channel")

    if int(time.time()) - cn_patch_info_memory_cache_update_time > MEMORY_CACHE_TIME or \
            friendly_name+"/"+channel not in cn_patch_info_memory_cache.keys():
        select_sql = r"SELECT p.tag_name, p.body, c.cn_url, p.publish_time, p.download_url " \
                     r"FROM patch_history p LEFT JOIN cn_boost_patch c ON p.repo_id = c.repo_id " \
                     r"INNER JOIN repo_list r ON p.repo_id = r.id " \
                     r"WHERE r.friendly_name = '%s' AND p.is_prerelease = %s " \
                     r"ORDER BY p.publish_time DESC LIMIT 1" % (friendly_name, channel_code)
        select_sql_result = db.fetch_one(sql=select_sql)
        if select_sql_result:
            if select_sql_result[2] is not None:
                result_dict = {
                    "tag_name": select_sql_result[0],
                    "body": select_sql_result[1],
                    "browser_download_url": select_sql_result[2],
                    "cache_time": select_sql_result[3],
                }
            else:
                result_dict = {
                    "tag_name": select_sql_result[0],
                    "body": select_sql_result[1],
                    "browser_download_url": select_sql_result[4],
                    "cache_time": select_sql_result[3]
                }
            cn_patch_info_memory_cache[friendly_name+"/"+channel] = result_dict
            cn_patch_info_memory_cache_update_time = int(time.time())
            return result_dict
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No patch found")
    else:
        return cn_patch_info_memory_cache[friendly_name+"/"+channel]
