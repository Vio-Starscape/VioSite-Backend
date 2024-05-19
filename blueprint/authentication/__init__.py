from quart import Blueprint, current_app, request, jsonify
from database import motor
from helpers import token_required, owner_api_key_required, scraper_required
from Objects import UserPermissions, Token, User
from jose import jwt
import aiohttp

authentication = Blueprint("authentication", __name__)

async def validate_user(token) -> Token:
    async with aiohttp.ClientSession() as session:
        data = {
            "grant_type": "authorization_code",
            "code": token,
            "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client_id = current_app.config["DISCORD_CLIENT_ID"]
        client_secret = current_app.config["DISCORD_CLIENT_SECRET"]

        auth = aiohttp.BasicAuth(client_id, client_secret)

        async with session.post(
                current_app.config["DISCORD_BASE_URL"] + "/oauth2/token",
                data=data,
                headers=headers,
                auth=auth
                ) as response:
            response.raise_for_status()
            info = await response.json()
            token = Token(**info)
        
        async with session.get(
                current_app.config["DISCORD_BASE_URL"] + "/users/@me",
                headers={"Authorization": f"Bearer {token.access_token}"},
                ) as response:
            response.raise_for_status()
            user = await response.json()
            return User(**user)

@authentication.route("/@me/permissions", methods=["GET"])
@token_required
async def get_user_permissions(*, user: UserPermissions = None):
    return jsonify(user.model_dump())

@authentication.route("/register", methods=["POST"])
async def register_user():
    data = await request.get_json()
    print(data)
    try:
        if code := data.get("code", None): # If the DISCORD Authentication token is present
            user = await validate_user(code)
            
            print(user)

            return jsonify({
                "message": "success",
                "token": jwt.encode(user.model_dump(), current_app.config["SECRET_KEY"], algorithm="HS256")
                })
    except Exception as e:
        print(e)
        return jsonify({"message": "error"}), 404
    return jsonify({"message": "error"}), 404