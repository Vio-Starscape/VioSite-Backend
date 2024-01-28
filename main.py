import os
import uvicorn
from dateutil.parser import parse
from quart import Quart, jsonify, websocket, request
from quart_motor import Motor
from dotenv import load_dotenv
load_dotenv()

from pprint import pprint

app = Quart(__name__)
mongo = Motor()

print(os.getenv("MONGO_URI"))

app.config["MOTOR_URI"] = os.getenv("MONGO_URI")
mongo.init_app(app, uri=app.config["MOTOR_URI"])

clients = set()

def convert_datetime_objects(data):
    for key, value in data.items():
        try:
            data[key] = parse(value)
        except (TypeError, ValueError):
            pass
    return data

async def get_current_market_data() -> dict:
    count = (await mongo.db.Items.find_one({"_id": 0}))["count"]-1
    print(count)
    data = (await mongo.db.Items.find_one({"_id": count}))
    return data

async def add_scan_to_database(items: dict):
    pprint(items)
    value = await mongo.db.Items.find_one_and_update(
        {"_id": 0},
        {"$inc": {"count": 1}}
    )
    items["_id"] = value["count"]
    await mongo.db.Items.insert_one(items)

@app.route("/")
async def index():
    return "<h1 style=\"text-align: center\">Vio Website</h1>"

@app.route("/data", methods=["POST"])
async def data():
    global clients
    data = await request.get_json()
    for client in clients:
        await client.send_json(data)
    data = convert_datetime_objects(data)
    print(data)
    await add_scan_to_database(data)
    return 'Good', 200

@app.websocket("/")
async def ws_endpoint():
    await websocket.accept()
    global clients
    print(f"Connection Made with: {websocket.remote_addr}")
    clients.add(websocket._get_current_object())
    try:
        while True:
            data = await websocket.receive()
            print(data)
            # await add_scan_to_database(data)
            for client in clients:
                await client.send(data)
    except:
        clients.remove(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT")))