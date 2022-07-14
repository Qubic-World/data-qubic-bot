import logging
import os

from bd.mongo import get_pretty_scores, get_pretty_user_score
from discord import Client
from discord.ext import commands
from discord.ext.commands import Context
from pool.pool import pool
from utils.utils import reply_data_as_file

from cogs.basecog import BaseCog


class QubicCog(BaseCog):
    def __init__(self, bot: Client) -> None:
        super().__init__(bot)
        self.__scores_file_name = "scores.txt"

    @commands.command()
    async def scores(self, ctx: Context, *args):
        await pool.add_command(self.__scores, ctx, *args)

    async def __scores(self, ctx: Context, *args):
        user_id = ""
        if len(args) > 0:
            user_id = args[0]

        # User scores
        if user_id != "":
            try:
                user_data = await get_pretty_user_score(user_id)
            except Exception as e:
                logging.warning(e)
                await self._reply_missing_data(ctx)
                return

            await self._reply(ctx, user_data)
        # All scores
        else:
            try:
                scores = await get_pretty_scores()
            except Exception as e:
                logging.warning(e)
                await self._reply_missing_data(ctx)
                return

            file_name = self._prepare_file_name(self.__scores_file_name)
            await reply_data_as_file(ctx, file_name, f"{os.linesep}".join(scores), self._delete_after_time)
