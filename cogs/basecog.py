from datetime import datetime

from discord import Client
from discord.ext import commands
from discord.ext.commands import Context


class BaseCog(commands.Cog):
    def __init__(self, bot: Client) -> None:
        super().__init__()

        self._bot = bot
        self._delete_after_time = 30

    @classmethod
    def _prepare_file_name(self, file_name: str) -> str:
        parts = file_name.split(".")
        if len(parts) <= 0:
            return file_name

        return parts[0] + "_" + str(datetime.utcnow().timestamp()) + "." + parts[1]

    async def _reply(self, ctx: Context, content):
        await ctx.reply(content, delete_after=self._delete_after_time)

    async def _reply_missing_data(self, ctx: Context):
        await self._reply(ctx, "The data is missing")
