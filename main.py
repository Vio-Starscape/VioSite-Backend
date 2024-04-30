import os
import uvicorn
import logging
import aiohttp
from functools import wraps
from jose import jwt
from quart import Quart, jsonify, request, redirect, url_for, session
from quart_motor import Motor
from pymongo import UpdateOne
from quart_cors import cors
from dotenv import load_dotenv

from Objects import Token, User, UserPermissions, Scraper

load_dotenv(override=True)

logger = logging.getLogger(__name__)

app = Quart(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["OWNER_API_KEY"] = os.getenv("OWNER_API_KEY")
app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")

app.config["DISCORD_BASE_URL"] = "https://discord.com/api/v10"
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")

app.config["MONGO_URI"] = os.getenv("MONGO_URI")

app = cors(app, allow_origin=os.getenv("ALLOW_ORIGIN"))
motor = Motor(app)

def owner_api_key_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if request.headers.get("x-api-key") == app.config["OWNER_API_KEY"]:
            return await f(*args, **kwargs)
        return jsonify({"message": "Unauthorized"}), 401
    return decorated_function

def token_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                user = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                decoded_user = User(**user)
                user_permissions = await motor.db.Permissions.find_one({"_id": decoded_user.id})
                if user_permissions:
                    user_permissions = UserPermissions(user=decoded_user, **user_permissions["permissions"])
                else:
                    user_permissions = UserPermissions(user=decoded_user)
                kwargs["user"] = user_permissions

            except Exception as e:
                logger.error(e)
                return jsonify({"message": "Token validation error"}), 401
        else:
            return jsonify({"message": "Token is missing"}), 401
        return await f(*args, **kwargs)
    return decorated_function

def scraper_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        data = await request.get_json()
        try:
            if isinstance(data, list):
                kwargs["scrapers"] = [Scraper(**scraper) for scraper in data]
            else:
                kwargs["updated_scraper"] = Scraper(**data)
        except Exception as e:
            logger.error(e)
            return jsonify({"message": "Invalid Scraper data"}), 400
        return await f(*args, **kwargs)
    return decorated_function

async def validate_user(token) -> Token:
    async with aiohttp.ClientSession() as session:
        data = {
            "grant_type": "authorization_code",
            "code": token,
            "redirect_uri": app.config["DISCORD_REDIRECT_URI"],
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client_id = app.config["DISCORD_CLIENT_ID"]
        client_secret = app.config["DISCORD_CLIENT_SECRET"]

        auth = aiohttp.BasicAuth(client_id, client_secret)

        async with session.post(
                app.config["DISCORD_BASE_URL"] + "/oauth2/token",
                data=data,
                headers=headers,
                auth=auth
                ) as response:
            response.raise_for_status()
            info = await response.json()
            token = Token(**info)
        
        async with session.get(
                app.config["DISCORD_BASE_URL"] + "/users/@me",
                headers={"Authorization": f"Bearer {token.access_token}"},
                ) as response:
            response.raise_for_status()
            user = await response.json()
            return User(**user)

## Discord Authentication

@app.route("/api/auth/@me/permissions", methods=["GET"])
@token_required
async def get_user_permissions(*, user: UserPermissions = None):
    return jsonify(user.model_dump())

@app.route("/api/auth/register", methods=["POST"])
async def register_user():
    data = await request.get_json()
    try:
        if code := data.get("code", None): # If the DISCORD Authentication token is present
            user = await validate_user(code)

            return jsonify({
                "message": "success",
                "token": jwt.encode(user.model_dump(), app.config["SECRET_KEY"], algorithm="HS256")
                })
    except Exception:
        return jsonify({"message": "error"}), 404
    return jsonify({"message": "error"}), 404

@app.route('/api/scrapers', methods=["GET"])
@token_required
async def scraper(*, user: UserPermissions = None):
    if not user.scraper:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403
    
    scrapers = [Scraper.mongo_load(account) async for account in motor.db.Scrapers.find()]

    return jsonify([scraper.model_dump() for scraper in scrapers])

@app.route('/api/scraper/update', methods=["POST"])
@token_required
@scraper_required
async def scraper_update(*, user: UserPermissions = None, updated_scraper: Scraper = None):
    if not user.scraper:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403
    
    await motor.db.Scrapers.update_one({"_id": updated_scraper.name}, {"$set": updated_scraper.mongo_dump()}, upsert=True)

    return jsonify({"message": "success"})

@app.route('/api/scraper/getall', methods=["GET"])
@owner_api_key_required
async def scraper_getall():
    scrapers = [Scraper.mongo_load(account) async for account in motor.db.Scrapers.find()]
    return jsonify([scraper.model_dump() for scraper in scrapers])


@app.route('/api/scraper/bulk_update', methods=["POST"])
@owner_api_key_required
@scraper_required
async def scraper_add(*, scrapers: list[Scraper] = None):

    await motor.db.Scrapers.bulk_write(
        [
            UpdateOne(
                {"_id": scraper.name},
                {"$set": scraper.mongo_dump()},
                upsert=True
            ) for scraper in scrapers
        ]
    )

    await motor.db.Scrapers.delete_many({"_id": {"$nin": [scraper.name for scraper in scrapers]}})
        
    return jsonify({"message": "success"})


if __name__ == "__main__":
    uvicorn.run("main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT")))