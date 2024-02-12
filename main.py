import os
import uvicorn
from quart import Quart
from dotenv import load_dotenv

from db import motor

from blueprint.api import bp

load_dotenv(override=True)

app = Quart(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

motor.init_app(app)

app.register_blueprint(bp)

@app.before_serving
async def setup_database():
    collection_names = await motor.db.list_collection_names()
    if "Market" not in collection_names:
        await motor.db.create_collection("Market")
        await motor.db.Market.insert_one({"_id": 0, "count": 1})
    if "Roblox" not in collection_names:
        await motor.db.create_collection("Roblox")
    if "Resources" not in collection_names:
        await motor.db.create_collection("Resources")
        await motor.db.Resources.insert_one({"_id": 0, "count": 1})
    if "Info" not in collection_names:
        await motor.db.create_collection("Info")
        await motor.db.Info.insert_one({"_id": 0, "items": []})

if __name__ == "__main__":
    uvicorn.run("main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT")))