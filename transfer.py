import json
from discord.ext import commands
import asyncio
from threading import Lock

transfer_mutex = Lock()
pool = []

def is_valid_json(json) -> bool:
    try:
        if len(json['source']) != 70:
            return False
        if len(json['destination']) != 70:
            return False
        amount = json['amount']
        if amount < pow(10, 6) or amount > pow(10, 15):
            return False
        if json['tick'] <= 0:
            return False
        if len(json['signature']) <= 0:
            return False

        return True
    except Exception:
        return False

@commands.command()
async def transfer(ctx, *, transfer_data):

    json_array = json.loads("[]")
    try:
        json_obj = json.loads(transfer_data)
        if is_valid_json(json_obj):
            json_array.append(json_obj)
    except Exception as e:
        print(e)
        await ctx.reply(e)


    if len(json_array) > 0:

        pool.append(json_array)
        if transfer_mutex.locked():
            return

        transfer_mutex.acquire()

        while len(pool) > 0:
            print(f"Transfer: pool len -- {len(pool)}")
            reader, writer = await asyncio.open_connection("172.19.0.2", 21847)
            try:
                print("Send transfer")
                json_str = json.dumps(pool.pop(0))
                writer.write(json_str.encode())
                await writer.drain()
                writer.close()
                await asyncio.gather(writer.wait_closed(), ctx.channel.send("Transfer was sent"))
            except Exception as e:
                print(e)

        transfer_mutex.release()
    
