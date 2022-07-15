from email.message import Message
import logging
import os

from bd.mongo import get_admin_scores
from discord import Client
from discord.ext import commands
from discord.ext.commands import Context
from pool.pool import pool
from utils.qubicservicesutils import get_pretty_revenues, get_user_revenues
from utils.utils import (admin_scores_pretty, get_user_score_from_admin, prepare_file_name,
                         reply_data_as_file)

from cogs.basecog import BaseCog


class AdminCog(BaseCog):
    def __init__(self, bot: Client) -> None:
        super().__init__(bot)
        self.__admin_scores_file_name = "admin_scores.txt"
        self.__revenues_file_name = "revenues.txt"

    async def _reply(self, ctx: Context, content):
        await ctx.reply(content, delete_after=self._delete_after_time)

    async def _reply_missing_data(self, ctx: Context):
        await self._reply(ctx, "The data is missing")

    @commands.command()
    async def qubic_admin(self, ctx: Context, *args):
        if len(args) > 0:
            await pool.add_command(self.__admin, ctx, *args)

    async def __admin(self, ctx: Context, *args):
        user_id = ""
        args_list = list(args)
        command_name = args_list[0]

        if len(args_list) > 1:
            user_id = args_list[1]

        match command_name:
            case "scores":
                await self.__admin_scores(ctx, user_id)
            case "revenues":
                await self.__revenues(ctx, user_id)

    async def __admin_scores(self, ctx: Context, user_id: str = ""):
        admin_scores = await get_admin_scores()

        if len(admin_scores) <= 0:
            await self._reply_missing_data(ctx)
            return

        if user_id != "":
            try:
                user_data = await get_user_score_from_admin(admin_scores, user_id)
                await self._reply(ctx, f"{user_data[0]}. {user_data[1]} - {user_data[2]}")
                return
            except Exception as e:
                logging.warning(e)
                await self._reply_missing_data(ctx)
                return

        # pretty_data = admin_scores_pretty(admin_scores)
        # if len(pretty_data) <= 0:
        #     await self._reply_missing_data(ctx)
        #     return

        # file_name = prepare_file_name(self.__admin_scores_file_name)
        # await reply_data_as_file(ctx, file_name, f"{os.linesep}".join(pretty_data), self._delete_after_time)


    async def __revenues(self, ctx: Context, user_id: str = ""):
        if user_id != "":
            try:
                user_data = await get_user_revenues(user_id)
                if user_data == None:
                    await self._reply(ctx, "This ID could not be found")
                    return

                await self._reply(ctx, f"{user_data[0]} - {user_data[1]}%")
                return
            except Exception as e:
                logging.warning(e)
                await self._reply_missing_data(ctx)
                return
        else:
            pass 
            # try:
            #     pretty_revenues = await get_pretty_revenues()
            # except Exception as e:
            #     logging.warning(e)
            #     await self._reply_missing_data(ctx)
            #     return

            # file_name = prepare_file_name(self.__revenues_file_name)
            # await reply_data_as_file(ctx, file_name, f"{os.linesep}".join(pretty_revenues), delete_after=self._delete_after_time)
