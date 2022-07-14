
import asyncio
import json
from asyncio.exceptions import TimeoutError


__QUBIC_SERVICES_IP = "172.19.0.2"
__QUBIC_SERVICES_REVENUES_PORT = 21845
__QUBIC_SERVICES_TICK_PORT = 21846
__CONNECTION_TIMEOUT = 5
__READ_TIMEOUT = 5

__ID_FIELD = "id"
__REVENUE_FIELD = "revenue"

async def get_tick():
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(__QUBIC_SERVICES_IP, __QUBIC_SERVICES_TICK_PORT), __CONNECTION_TIMEOUT)
    except TimeoutError:
        raise TimeoutError("get_tick: Failed to connect")

    try:
        tick_data = await asyncio.wait_for(reader.read(), timeout=__READ_TIMEOUT)
    except TimeoutError:
        raise TimeoutError("Failed to read tick data")
    finally:
        writer.close()
        await writer.wait_closed()

    return json.loads(tick_data.decode())




async def get_user_revenues(user_id: str):
    if user_id == "":
        raise ValueError("user_id cannot be empty")

    revenues = await get_revenues()

    for revenue in revenues:
        id = revenue[__ID_FIELD]
        if id == user_id:
            return (id, revenue[__REVENUE_FIELD])

    raise None


async def get_pretty_revenues():
    revenues = await get_revenues()

    pretty_revenues = []

    for revenue in revenues:
        id = revenue[__ID_FIELD]
        rev_value = revenue[__REVENUE_FIELD]
        pretty_revenues.append(f"{id} - {rev_value}%")

    return pretty_revenues


async def get_revenues():
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(__QUBIC_SERVICES_IP, __QUBIC_SERVICES_REVENUES_PORT), __CONNECTION_TIMEOUT)
    except asyncio.exceptions.TimeoutError:
        raise asyncio.exceptions.TimeoutError(
            "get_revenues: Failed to connect to qubic_services")

    try:
        data = await asyncio.wait_for(reader.read(), timeout=__READ_TIMEOUT)
    except asyncio.exceptions.TimeoutError:
        raise asyncio.exceptions.TimeoutError(
            "get_revenues: Failed to read data")

    writer.close()
    await writer.wait_closed()

    return json.loads(data.decode())
