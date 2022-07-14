import os
import string

import discord
from discord.ext import commands
from dotenv import load_dotenv

from timercommands import TimerCommands
from cogs.admincog import AdminCog
from cogs.qubiccog import QubicCog
from pool.pool import pool
from transfer import transfer

version: str = "0.4.0"

token: string
master_name: string
master_id: int
channel_name: string
mongo_username: string
mongo_pswd: string
mongo_uri: string
client = commands.Bot(command_prefix='/')


@client.event
async def on_ready():
    print(f"Bot: {client.user} Ready!")
    print(f"Version: {version}")

    pool.start()

    timer_commands = TimerCommands(client)
    await timer_commands.start()


def is_valid_channel(ctx):
    return ctx.author != client.user and ctx.channel.name == channel_name


def is_valid_author(author: discord.Member) -> bool:
    return author.id == master_id and author.name == master_name and author != client.user


def is_valid_command(message):
    return message.author != client.user and message.content.startswith(client.command_prefix) and is_valid_channel(message)


@client.event
async def on_message(message):
    if(is_valid_command(message)):
        await client.process_commands(message)
        return

    if not is_valid_author(message.author):
        return

    if message.channel.name != channel_name:
        return


def main():
    global token
    global master_name
    global master_id
    global channel_name

    load_dotenv()

    token = os.getenv("ACCESS_TOKEN")
    master_name = os.getenv("MASTER_NAME")
    master_id = int(os.getenv("MASTER_ID"))
    channel_name = os.getenv("CHANNEL_NAME")

    client.add_cog(AdminCog(client))
    client.add_cog(QubicCog(client))
    client.add_command(transfer)
    client.run(token)


if __name__ == "__main__":
    main()
