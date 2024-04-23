import os
import uvicorn
import secrets
import logging
import aiohttp
from functools import wraps
from jose import jwt
from quart import Quart, jsonify, request, redirect, url_for, session
from quart_motor import Motor
from quart_cors import cors
from dotenv import load_dotenv

from Objects import Token, User, UserPermissions

load_dotenv(override=True)

logger = logging.getLogger(__name__)

app = Quart(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")

app.config["DISCORD_BASE_URL"] = "https://discord.com/api/v10"
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")

app.config["MONGO_URI"] = os.getenv("MONGO_URI")

app = cors(app, allow_origin="*")
motor = Motor(app)

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
                # kwargs["user"] = decoded_user
                kwargs["user"] = user_permissions

            except Exception as e:
                logger.error(e)
                return jsonify({"message": "Token validation error"}), 401
        else:
            return jsonify({"message": "Token is missing"}), 401
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

# @app.route("/api/auth/@me", methods=["GET"])
# @token_required
# async def get_user(*, user: User = None):
#     return jsonify(user.model_dump())

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

@app.route('/api/scraper', methods=["GET"])
@token_required
async def scraper(*, user: UserPermissions = None):
    if not user.scraper:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403

    return jsonify({"message": "scraper"})


if __name__ == "__main__":
    uvicorn.run("main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT")))