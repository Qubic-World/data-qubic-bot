import asyncio
from datetime import datetime
from io import BytesIO
import logging
import os

from discord import Client, Message, Embed, Attachment, File
from dotenv import load_dotenv
from pool.pool import pool
from utils.qubicservicesutils import get_pretty_revenues, get_tick

from bd.mongo import get_admin_scores, get_min_max_admin_scores, get_pretty_scores
from utils.utils import admin_scores_pretty, prepare_file_name

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

        self.__functions:list = [self.__send_min_max, self.__send_tick, self.__send_revenues, self.__send_admin_scores, self.__send_scores]

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

            e: Embed = embeds[-1]
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
            return True or message.author == self.__bot.user

        messages = await self.__tick_channel.history(limit=10).flatten()

        if len(messages) <= len(self.__functions):
            return

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
                tick = data["tick"] - 1
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

    async def __get_last_file_message(self, file_name: str, limit=100):
        message: Message = None
        async for message in self.__tick_channel.history(limit=limit):
            a: Attachment = None
            for a in message.attachments:
                if a.filename.startswith(file_name):
                    return message

        return None

    async def __send_revenues(self):
        try:
            revenues = await get_pretty_revenues()
        except Exception as e:
            logging.warning(e)
            return

        if len(revenues) <= 0:
            logging.warning("__send_revenues: revenues is empty")
            return

        file_name = prepare_file_name('revenues.txt')
        message: Message = await self.__get_last_file_message("revenues")
        await self.__send_edit_file_message(message=message, file_name=file_name, content=f"{os.linesep}".join(revenues))


    async def __send_admin_scores(self):
        admin_scores = await get_admin_scores()
        if len(admin_scores) <= 0:
            logging.warning("__send_admin_scores: admin_scores is empty")
            return

        pretty_data = admin_scores_pretty(admin_scores)
        file_name = prepare_file_name('admin_scores.txt')
        message: Message = await self.__get_last_file_message("admin_scores")
        await self.__send_edit_file_message(message, file_name, f"{os.linesep}".join(pretty_data))

    async def __send_edit_file_message(self, message: Message = None, file_name: str = "", content: str = ""):
        if file_name == None:
            logging.warning(
                "TimerCommands.__send_edit_file_message: file_name is empty")
            return

        b = content.encode('utf-8')

        file = File(BytesIO(b), filename=file_name)

        time = str(datetime.utcnow().replace(second=0, microsecond=0))
        if message != None:
            await message.delete()

        await self.__tick_channel.send(time, file=file)

    async def __send_scores(self):
        try:
            scores = await get_pretty_scores()
        except Exception as e:
            logging.warning(e)
            return

        file_name = prepare_file_name('scores.txt')
        message: Message = await self.__get_last_file_message("scores")
        await self.__send_edit_file_message(message, file_name, f"{os.linesep}".join(scores))
        

    async def loop(self):
        while True:
            tasks = []
            for function in self.__functions:
                tasks.append(asyncio.create_task(function()))

            tasks.append(asyncio.create_task(asyncio.sleep(60)))
            await asyncio.wait(tasks)