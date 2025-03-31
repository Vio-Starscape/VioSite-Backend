import logging

logger = logging.getLogger(__name__)

from database import motor
from functools import wraps
from quart import jsonify, request, current_app
from jose import jwt
from Objects import User, UserPermissions, Scraper

def owner_api_key_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if request.headers.get("x-api-key") == current_app.config["OWNER_API_KEY"]:
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
                user = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                
                decoded_user = User(**user)
                user_permissions = await motor.db.Permissions.find_one({"_id": decoded_user.id})

                raw_permissions = user_permissions.get("permissions") if user_permissions else None
                perm_data = raw_permissions if isinstance(raw_permissions, dict) else {}

                user_permissions = UserPermissions(
                    user=decoded_user,
                    **perm_data,
                    owner=decoded_user.id == int(current_app.config["OWNER_ID"])
                )
                
                kwargs["user"] = user_permissions

            except Exception as e:
                print("Something went wrongt")
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
        
        host = request.args.get("host")
        if not host:
            return jsonify({"message": "No host provided"}), 400
        
        try:
            if isinstance(data, list):
                kwargs["scrapers"] = [Scraper(**scraper, host=host) for scraper in data]
            else:
                kwargs["updated_scraper"] = Scraper(**data, host=host)
        except Exception as e:
            logger.error(e)
            return jsonify({"message": "Invalid Scraper data"}), 400
        return await f(*args, **kwargs)
    return decorated_function