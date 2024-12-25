from quart import Blueprint, jsonify, current_app, request
from database import motor
from helpers import token_required
from Objects import UserPermissions, Scraper
from pymongo import UpdateOne

user_bp = Blueprint("user", __name__)

@user_bp.route('/permissions/<int:user_id>', methods=["GET", "POST"], strict_slashes=False)
@token_required
async def permissions(user: UserPermissions, user_id: int):
    if not user.admin:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403

    if request.method == "GET":
        permissions = await motor.db.Permissions.find_one({"_id": user_id})
        if permissions is None:
            return jsonify({"evaluation": False, "undercut": False})
        
        return jsonify(permissions["permissions"])
    
    if request.method == "POST":
        data = await request.get_json()
        evaluation = data.get("evaluation", False)
        undercut = data.get("undercut", False)

        await motor.db.Permissions.update_one(
            {"_id": user_id},
            {"$set": 
                {
                    "permissions.evaluation": evaluation,
                    "permissions.undercut": undercut
                }
            },
            upsert=True
        )

        return jsonify({"message": "Permissions updated"})