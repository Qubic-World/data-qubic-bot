import asyncio
from datetime import datetime
import logging
import os

from discord import Client, Message, Embed
from dotenv import load_dotenv
from pool.pool import pool
from utils.qubicservicesutils import get_tick

from bd.mongo import get_min_max_admin_scores

__TICK_FIELD = "tick"
__AMOUNT_FIELD = "amount"


class TimerCommands():
    def __init__(self, bot: Client) -> None:
        self.__bot: Client = bot
        load_dotenv()
        self.__tick_channel = bot.get_channel(
            int(os.getenv("TICK_CHANNEL_ID")))
        if self.__tick_channel == None:
            raise ValueError("__tick_channel cannot be None")

        self.__background_tasks = []

    @staticmethod
    def get_utc():
        return datetime.utcnow().replace(second=0, microsecond=0)

    async def __get_messages_startwith(self, startwith: str = "", limit: int = 200) -> list:
        tick_messages = []
        message: Message = None
        async for message in self.__tick_channel.history(limit=limit):
            embeds = message.embeds
            if len(embeds) <= 0:
                continue

            e:Embed = embeds[-1]
            if message.author == self.__bot.user and e.title.find(startwith) != -1:
                tick_messages.append(message)

        return tick_messages

    async def __get_last_tick_message(self) -> Message:
        messages = await self.__get_all_tick_message()
        if len(messages) > 0:
            return messages[0]
        return None

    async def __get_all_tick_message(self, limit: int = 200) -> list:
        return await self.__get_messages_startwith(startwith="Tick", limit=limit)

    async def __get_minmax_messages(self, limit: int = 200) -> list:
        return await self.__get_messages_startwith(startwith="Admin scores [min..max]", limit=limit)

    async def __get_last_minmax_message(self) -> Message:
        messages = await self.__get_minmax_messages()
        if len(messages) > 0:
            return messages[0]
        return None

    async def __cleanup(self):
        logging.debug("TimerCommands.__cleanup")

        def is_me(message: Message):
            return message.author == self.__bot.user

        while True:
            l = len(await self.__tick_channel.purge(check=is_me)) 
            print(l)
            if l <= 0:
                break

        return

    async def start(self):
        print("Cleanup")
        await self.__cleanup()
        print("Start")
        task = asyncio.create_task(self.loop())
        task.add_done_callback(self.__background_tasks.remove)
        self.__background_tasks.append(task)

    async def __send_min_max(self):
        try:
            min, max = await get_min_max_admin_scores()
            message = await self.__get_last_minmax_message()
            e = Embed(title="Admin scores [min..max]",
                      description=f"[{min}..{max}]")
            e.set_footer(text=str(TimerCommands.get_utc()))
            if message != None:
                await message.edit(embed=e)
            else:
                await self.__tick_channel.send(embed=e)
        except Exception as e:
            logging.warning(e)

    async def __send_tick(self):
        try:
            tick_data = await get_tick()
        except Exception as e:
            logging.warning(e)
            return

        pretty_tick = []
        for data in tick_data[:10]:
            try:
                tick = data["tick"]
                amount = data["amount"]
            except Exception as e:
                logging.warning(e)
                return

            pretty_tick.append(f"{tick}: {amount}")

        if len(pretty_tick) > 0:
            message: Message = await self.__get_last_tick_message()
            e = Embed(title="Ticks",
                      description=f"{os.linesep}".join(pretty_tick))
            e.set_footer(text=str(TimerCommands.get_utc()))
            if message != None:
                await message.edit(embed=e)
            else:
                await self.__tick_channel.send(embed=e)

    async def loop(self):
        while True:
            await pool.add_command(self.__send_min_max)
            await pool.add_command(self.__send_tick)

            await asyncio.sleep(60)
