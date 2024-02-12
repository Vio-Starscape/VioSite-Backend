import aiohttp
import logging
import asyncio
from datetime import datetime
from quart import Blueprint, current_app, request, websocket, jsonify 
from dateutil.parser import parse

from db import motor

bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)

logger = logging.getLogger(__name__)

clients = set()

@bp.route("/")
async def index():
    return "<h1 style=\"text-align: center\">Vio Website LOL Nothing HERE YET</h1>"

@bp.route("/items")
async def items():
    items = await motor.db.Info.find_one({"_id": 0})
    return jsonify(items["items"])

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def convert_datetime_objects(data):
    for key, value in data.items():
        try:
            data[key] = parse(value)
        except (TypeError, ValueError):
            pass
    return data

async def add_roblox_users_to_database(market_data: dict):
    ids = set()
    for item in market_data["items"].values():
        for listing in item["buy"]:
            ids.add(listing[2])
        for listing in item["sell"]:
            ids.add(listing[2])

    existing_ids = {doc["_id"] async for doc in motor.db.Roblox.find({"_id": {"$in": list(ids)}})}
    ids -= existing_ids

    async with aiohttp.ClientSession() as session:

        chunk_size = 50
        for i in range(0, len(ids), chunk_size):
            async with session.post("https://users.roblox.com/v1/users", json={"userIds": list(ids)[i:i+chunk_size], "excludeBannedUsers": False}) as response:
                users = await response.json()
                logger.debug(f"Got users: {users}")
                for user in users["data"]:
                    logger.debug(f"Updating user: {user}")
                    await motor.db.Roblox.update_one({"_id": user["id"]}, {"$set": user}, upsert=True)
            await asyncio.sleep(15)

async def update_item_names(market_data: dict):
    new_items = {}
    key_names = []
    for key, value in market_data["items"].items():
        new_key = key.replace(".", "")
        key_names.append(new_key)
        new_items[new_key] = value
    market_data["items"] = new_items

    await motor.db.Info.update_one(
        {"_id": 0},
        {"$addToSet": {"items": {"$each": key_names}}},
    )

    return market_data

async def add_scan_to_database(market_data: dict):
    await add_roblox_users_to_database(market_data)
    market_data = await update_item_names(market_data)

    value = await motor.db.Market.find_one_and_update(
        {"_id": 0}, 
        {"$inc": {"count": 1}}
    )
    await motor.db.Info.update_one(
        {"_id": 0},
        {"$addToSet": {"items": {"$each": list(market_data["items"].keys())}}},
    )
    market_data["_id"] = value["count"]+1
    await motor.db.Market.insert_one(market_data)

@bp.route("/data", methods=["POST"])
async def data():
    data = await request.get_json()
    data = convert_datetime_objects(data)
    print(data)
    asyncio.ensure_future(add_scan_to_database(data))
    return 'Good', 200

@bp.websocket("/ws")
async def ws_endpoint():
    await websocket.accept()
    global clients
    print(f"Connection Made with: {websocket.remote_addr}")
    clients.add(websocket._get_current_object())
    try:
        while True:
            data = await websocket.receive()
            for client in clients:
                await client.send(data)
    except:
        clients.remove(websocket)
