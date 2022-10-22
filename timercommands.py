import asyncio
from dataclasses import dataclass
import json
import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from custom_nats.custom_nats import Nats
from custom_nats.handler import Handler, HandlerStarter
from discord import Attachment, Client, Embed, File, Message
from dotenv import load_dotenv
from nats.aio.msg import Msg
from qubic.qubicdata import DataSubjects, QUORUM, MAX_REVENUE_VALUE

from utils.utils import prepare_file_name

_ticks = dict()
_scores = dict()
_revenues = dict()


class HandlerTick(Handler):
    async def get_sub(self):
        if self._nc.is_disconected:
            return None

        return await self._nc.subscribe(DataSubjects.TICKS)

    async def _handler_msg(self, msg: Msg):
        if msg is None or len(msg.data) <= 0:
            return

        try:
            logging.info('Got the tics')
            global _ticks
            _ticks = json.loads(msg.data)
            # logging.info(_ticks)
        except Exception as e:
            logging.exception(e)
            return


class HandlerScores(Handler):
    async def get_sub(self):
        if self._nc.is_disconected:
            return None

        return await self._nc.subscribe(DataSubjects.SCORES)

    async def _handler_msg(self, msg: Msg):
        if msg is None or len(msg.data) <= 0:
            return

        try:
            logging.info('Got the scores')
            global _scores
            _scores = json.loads(msg.data)
        except Exception as e:
            logging.exception(e)
            return


class HandlerRevenues(Handler):
    async def get_sub(self):
        if self._nc.is_disconected:
            return None

        return await self._nc.subscribe(DataSubjects.REVENUES)

    async def _handler_msg(self, msg: Msg):
        import zstandard

        if msg is None or len(msg.data) <= 0:
            return

        try:
            logging.info('Got the revenues')
            global _revenues
            _revenues = json.loads(zstandard.decompress(msg.data))
        except Exception as e:
            logging.exception(e)
            return


class TimerCommands():
    digets_in_revenue = len(str(int(MAX_REVENUE_VALUE)))

    @dataclass
    class MessageTitles:
        TICK = 'Tick'
        MINMAX = 'Scores'

    def __init__(self, bot: Client, nc: Optional[Nats] = None) -> None:
        self.__bot: Client = bot
        load_dotenv()
        self.__tick_channel = bot.get_channel(
            int(os.getenv("STATS_CHANNEL_ID")))
        if self.__tick_channel == None:
            raise ValueError("__tick_channel cannot be None")

        self.__background_tasks = []

        self.__functions: list = [self.__send_min_max, self.__send_tick,
                                  self.__send_revenues, self.__send_scores]

        self.__nc = nc
        self.__minmax_message = None
        self.__tick_message = None

    @staticmethod
    def get_utc():
        return datetime.utcnow().replace(microsecond=0)

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
        return await self.__get_messages_startwith(startwith=TimerCommands.MessageTitles.TICK, limit=limit)

    async def __get_minmax_messages(self, limit: int = 200) -> list:
        return await self.__get_messages_startwith(startwith=TimerCommands.MessageTitles.MINMAX, limit=limit)

    async def __get_last_minmax_message(self) -> Message:
        messages = await self.__get_minmax_messages()
        if len(messages) > 0:
            return messages[0]
        return None

    async def __cleanup(self):
        logging.debug("TimerCommands.__cleanup")

        def is_me(message: Message):
            return True or message.author == self.__bot.user

        # messages = await self.__tick_channel.history(limit=10).flatten()

        # if len(messages) <= len(self.__functions):
        #     return

        await self.__tick_channel.purge(check=is_me)

        return

    async def start(self):
        print("Cleanup")
        await self.__cleanup()
        print("Start")
        task = asyncio.create_task(self.loop())
        task.add_done_callback(self.__background_tasks.remove)
        self.__background_tasks.append(task)

        self.__background_tasks.append(asyncio.create_task(
            HandlerStarter.start(HandlerTick(self.__nc))))
        self.__background_tasks.append(asyncio.create_task(
            HandlerStarter.start(HandlerScores(self.__nc))))
        self.__background_tasks.append(asyncio.create_task(
            HandlerStarter.start(HandlerRevenues(self.__nc))))

    @classmethod
    def set_time_to_footer(cls, e=Embed):
        e.set_footer(text=str(TimerCommands.get_utc()))

    async def __send_scores(self):
        if len(_scores) <= 0:
            return

        pretty_scores = []
        for k, v in _scores.items():
            pretty_scores.append(f'{k} {v}')

        file_name = prepare_file_name('scores.txt')
        message: Message = await self.__get_last_file_message("scores")
        await self.__send_edit_file_message(message=message, file_name=file_name, content=f"{os.linesep}".join(pretty_scores))

    async def __send_revenues(self):
        if len(_revenues) <= 0:
            return

        pretty_revenues = []
        for k, v_list in _revenues.items():
            rev_number = len(v_list)
            if rev_number <= 0:
                value = 0
                percent = 0
            else:
                index = QUORUM - 1 if rev_number >= QUORUM else rev_number - 1
                value = sorted(v_list)[index]
                percent = int(value * 100 / MAX_REVENUE_VALUE)

            pretty_revenues.append(
                '{0} {1:>{rev_offset}} {2:>3}% (NoV: {3:>3})'.format(k, value, percent, rev_number, rev_offset=TimerCommands.digets_in_revenue))

        file_name = prepare_file_name('revenues.txt')
        message: Message = await self.__get_last_file_message('revenues')
        await self.__send_edit_file_message(message=message, file_name=file_name, content=f"{os.linesep}".join(pretty_revenues))

    async def __send_min_max(self):
        from qubic.qubicdata import NUMBER_OF_COMPUTORS
        if len(_scores) <= 0:
            return


        computor_scores = list(_scores.values())[:NUMBER_OF_COMPUTORS]
        min_score = min(computor_scores)
        max_score = max(computor_scores)

        message = self.__minmax_message
        if message is None:
            message = await self.__get_last_minmax_message()
            self.__minmax_message = message

        description = f'[{min_score}..{max_score}]'
        e = Embed(title=TimerCommands.MessageTitles.MINMAX,
                  description=description)
        self.set_time_to_footer(e)
        if message != None:
            await message.edit(embed=e)
        else:
            self.__minmax_message = await self.__tick_channel.send(embed=e)

    async def __send_tick(self):
        import itertools
        global _ticks

        pretty_tick = []
        pairs = [(k, len(list(g)))
                 for k, g in itertools.groupby(sorted(_ticks.values(), reverse=True))]

        for k, v in pairs:
            tick = k - 1
            amount = v
            pretty_tick.append('{0} {1:>2}'.format(tick,  amount))

        if len(pretty_tick) > 0:
            message: Message = self.__tick_message
            if message is None:
                message = await self.__get_last_tick_message()
                self.__tick_message = message

            e = Embed(title=TimerCommands.MessageTitles.TICK,
                      description=f'{os.linesep}'.join(pretty_tick))
            self.set_time_to_footer(e)
            if message != None:
                await message.edit(embed=e)
            else:
                self.__tick_message = await self.__tick_channel.send(embed=e)

    async def __get_last_file_message(self, file_name: str, limit=100):
        message: Message = None
        async for message in self.__tick_channel.history(limit=limit):
            a: Attachment = None
            for a in message.attachments:
                if a.filename.startswith(file_name):
                    return message

        return None

    async def __send_edit_file_message(self, message: Message = None, file_name: str = "", content: str = ""):
        if file_name == None:
            logging.warning(
                "TimerCommands.__send_edit_file_message: file_name is empty")
            return

        b = content.encode('utf-8')

        file = File(BytesIO(b), filename=file_name)

        time = str(datetime.utcnow().replace(microsecond=0))
        if message != None:
            await message.delete()

        await self.__tick_channel.send(time, file=file)

    async def loop(self):
        while True:
            tasks = []
            for function in self.__functions:
                tasks.append(asyncio.create_task(
                    function(), name=function.__name__))
            tasks.append(asyncio.create_task(asyncio.sleep(30)))

            done, pending = await asyncio.wait(tasks, timeout=61, return_when=asyncio.ALL_COMPLETED)
            task: asyncio.Task = None
            for task in done:
                e = task.exception()
                name = task.get_name()
                if isinstance(e, Exception):
                    print(f"{name} threw {type(e)}")

            for task in pending:
                name = task.get_name()
                print(f"{name} is pending")
                task.cancel()
