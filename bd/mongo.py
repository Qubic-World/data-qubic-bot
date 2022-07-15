import asyncio
import logging
import os
from datetime import datetime
from urllib.parse import quote_plus

import aiohttp
import motor.motor_asyncio
from bson import SON
from dotenv import load_dotenv

load_dotenv()

__MONGO_USERNAME = os.getenv("MONGO_USERNAME")
__MONGO_PSWD = os.getenv("MONGO_PSWD")
__MONGO_URL = os.getenv("MONGO_URL")
__MONGO_URI = "mongodb+srv://%s:%s@%s" % (
    quote_plus(__MONGO_USERNAME), quote_plus(__MONGO_PSWD), __MONGO_URL
)
__CONNECT_TIMEOUT = 5

__TIMESTAMP_FIELD = "timestamp"
__SCORE_FIELD = "score"
__ID_FIELD = "id"

client_mongo = motor.motor_asyncio.AsyncIOMotorClient(__MONGO_URI)
scores_db = client_mongo["qubic-world"]
scores_collection = scores_db["latestScore"]
admin_scores_collection = scores_db["latestAdminScore"]


def score_to_pretty(id, score, timestamp) -> str:
    return f"{id} - {score:<4} - {datetime.fromtimestamp(timestamp)}"


async def get_pretty_scores():
    scores = await get_scores()

    pretty = []
    for score in scores:
        pretty.append(score_to_pretty(
            score[__ID_FIELD], score[__SCORE_FIELD], score[__TIMESTAMP_FIELD]))

    return pretty


async def get_pretty_user_score(user_id: str):
    user_data = await get_user_scores(user_id)
    if user_data == None:
        raise ValueError("user_data is None")

    return f"{user_data[0]} - {user_data[1]} - {datetime.fromtimestamp(user_data[2])}"


async def get_user_scores(user_id: str):
    if len(user_id) == "":
        raise ValueError("user_id cannot be empty")

    scores = await get_scores()

    for score in scores:
        id = score[__ID_FIELD]
        if id == user_id:
            return (id, score[__SCORE_FIELD], score[__TIMESTAMP_FIELD])

    return None


#TODO: replace
async def get_scores():
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://qubic.world/api/v1/network/scores/"

            async with session.get(url) as resp:
                return await resp.json(encoding='utf-8')
    except Exception as e:
        logging.error(e)
        return []


async def get_min_max_admin_scores():
    admin_scores = await get_admin_scores()
    if len(admin_scores) <= 0:
        raise ValueError()

    min_index = 675 if len(admin_scores) > 675 else -1
    return admin_scores[min_index][__SCORE_FIELD], admin_scores[0][__SCORE_FIELD]


async def get_admin_scores():
    pipeline = [
        {
            u"$group": {
                u"_id": u"$id",
                u"maxScore": {
                    u"$max": {
                        u"$mergeObjects": [
                             {
                                 u"score": u"$score"
                             },
                            u"$$ROOT"
                        ]
                    }
                }
            }
        },
        {
            u"$replaceRoot": {
                u"newRoot": u"$maxScore"
            }
        },
        {
            u"$sort": SON([(u"score", -1)])
        }]
    found_documents = admin_scores_collection.aggregate(pipeline)
    try:
        return await asyncio.wait_for(found_documents.to_list(length=None), __CONNECT_TIMEOUT)
    except asyncio.exceptions.TimeoutError:
        logging.warning(
            "get_admin_scores: Database connection time has expired")
        return []
    except Exception as e:
        logging.warning(e)
        return []
