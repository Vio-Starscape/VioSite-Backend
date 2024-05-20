from quart import Blueprint, jsonify, current_app, request
from database import motor
from helpers import token_required, scraper_required, owner_api_key_required
from Objects import UserPermissions, Scraper


terminal_bp = Blueprint("terminal", __name__)

@terminal_bp.route('/item', methods=["GET"])
@token_required
async def get_item(user: UserPermissions):
    name = request.args.get("name")
    if not name:
        return jsonify({"message": "No item name provided"}), 400
    
    all_items = (await motor.db.Info.find_one({"_id": 0}))["items"]
    if name not in all_items:
        return jsonify({"message": "Item not found"}), 404

    response = await motor.db.Market.find_one(
        filter={"_id": {"$gt": 0}, f"items.{name}": {"$exists": True}},
        projection={"_id": 1, "time_scanned": 1, f"items.{name}": 1},
        sort=[("_id", -1)]
        )
    
    return jsonify(response), 200