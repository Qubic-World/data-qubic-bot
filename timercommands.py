import asyncio
import logging
import os

from discord import Client, Message
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

    async def __get_messages_startwith(self, startwith: str = "", limit: int = 200) -> list:
        tick_messages = []
        async for message in self.__tick_channel.history(limit=limit):
            if message.author == self.__bot.user and message.content.find(startwith) != -1:
                tick_messages.append(message)

        return tick_messages

    async def __get_last_tick_message(self) -> Message:
        messages = await self.__get_all_tick_message()
        if len(messages) > 0:
            return messages[0]
        return None

    async def __get_all_tick_message(self, limit: int = 200) -> list:
        return await self.__get_messages_startwith(startwith="Tick", limit=limit)

    async def __get_minmax_messages(self, limit:int = 200)->list:
        return await self.__get_messages_startwith(startwith="Admin scores [min..max]:", limit=limit)

    async def __get_last_minmax_message(self)->Message:
        messages = await self.__get_minmax_messages()
        if len(messages) > 0:
            return messages[0]
        return None

    async def __cleanup(self):
        logging.debug("TimerCommands.__cleanup")

        tick_messages = await self.__get_all_tick_message(None)
        minmax_messages = await self.__get_all_tick_message(None)
        all_messages = tick_messages + minmax_messages
        
        while len(all_messages) > 0:
            logging.debug(f"Message len: {len(all_messages)}")
            await self.__tick_channel.delete_messages(all_messages[:100])
            all_messages = all_messages[:100]

    async def start(self):
        # await self.__cleanup()
        task = asyncio.create_task(self.loop())
        task.add_done_callback(self.__background_tasks.remove)
        self.__background_tasks.append(task)

    async def __send_min_max(self):
        try:
            min, max = await get_min_max_admin_scores()
            message = await self.__get_last_minmax_message()
            message_str = f"```Admin scores [min..max]:\n[{min}..{max}]```"
            if message != None:
                await message.edit(content=message_str)
            else:
                await self.__tick_channel.send(message_str)
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
            message_str = str(f"```Ticks:{os.linesep}" + f"{os.linesep}".join(pretty_tick) + "```")
            if message != None:
                await message.edit(content=message_str)
            else:
                await self.__tick_channel.send(message_str)

    async def loop(self):
        while True:
            await pool.add_command(self.__send_min_max)
            await pool.add_command(self.__send_tick)

            await asyncio.sleep(60)