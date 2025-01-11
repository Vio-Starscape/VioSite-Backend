from quart import Blueprint, jsonify, current_app, request
from database import motor
from helpers import token_required
from Objects import UserPermissions, Scraper
from pymongo import UpdateOne

terminal_bp = Blueprint("terminal", __name__)

@terminal_bp.route('/items', methods=["GET", "POST"], strict_slashes=False)
@token_required
async def items(user: UserPermissions):
    if request.method == "GET":
        items = (await motor.db.Info.find_one({"_id": 0}))["items"]
        return jsonify(items)
    
    if request.method == "POST" and user.admin:
        items_to_remove = await request.get_json()
        
        items = (await motor.db.Info.find_one({"_id": 0}))["items"]
        
        for item in items_to_remove:
            items.remove(item)
        
        await motor.db.Info.update_one(
            {"_id": 0},
            {"$set": {"items": items}}
        )

        return jsonify({"message": "Item updated"})
    else:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403