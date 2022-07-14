from datetime import datetime
import logging
import aiofiles
from discord.ext.commands import Context
from discord import File


SCORE_FIELD = "score"
ID_FIELD = "id"
TIMESTAMP_FIELD = 'timestamp'
INVALID_ID = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACDFMDM"

async def reply_data_as_file(ctx: Context, file_name: str, data:str, delete_after:float = None):
    async with aiofiles.open(file_name, "w") as file:
        await file.write(data)

    await ctx.reply(file=File(file_name), delete_after=delete_after)


def admin_scores_pretty(admin_scores: list):
    if len(admin_scores) <= 0:
        return []

    min_index = 675 if len(admin_scores) > 675 else -1
    min_score = admin_scores[min_index][SCORE_FIELD]
    max_score = admin_scores[0][SCORE_FIELD]

    pretty_list = []
    pretty_list.append(f"[{min_score}..{max_score}]")

    for index, admin_score in enumerate(admin_scores):
        try:
            id = admin_score[ID_FIELD]
        except Exception as e:
            logging.warning(e)
            id = INVALID_ID

        if id == INVALID_ID:
            continue

        try:
            score = admin_score[SCORE_FIELD]
        except Exception as e:
            logging.warning(e)
            score = 0

        try:
            timestamp = admin_score[TIMESTAMP_FIELD]
        except Exception as e:
            logging.warning(e)
            timestamp = 0

        date_time = datetime.fromtimestamp(timestamp)

        if(score > 0 and index < 676):
            list_item = f"{index + 1:>4}. {id} - {score} - {date_time}"
        else:
            list_item = f"{index + 1:>4}. {id} - None - {date_time}"

        pretty_list.append(list_item)

    return pretty_list

async def get_user_score_from_admin(admin_scores: list, user_id: str) -> dict:
    if len(admin_scores) <= 0:
        raise ValueError("admin_scores cannot be empty")

    if user_id == "":
        raise ValueError("user_id cannot be empty")

    for idx, admin_score in enumerate(admin_scores):
        try:
            if admin_score[ID_FIELD] == user_id:
                return (idx + 1, admin_score[ID_FIELD], admin_score[SCORE_FIELD])
        except Exception as e:
            raise e