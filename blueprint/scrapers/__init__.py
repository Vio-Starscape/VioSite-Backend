from quart import Blueprint, jsonify, current_app, request
from database import motor
from helpers import token_required, scraper_required, owner_api_key_required
from Objects import UserPermissions, Scraper
from pymongo import UpdateOne

scrapers_bp = Blueprint("scrapers", __name__)

@scrapers_bp.route('/', methods=["GET"], strict_slashes=False)
@token_required
async def scraper(user: UserPermissions):
    if not user.scraper:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403
    
    scrapers = [Scraper.mongo_load(account) async for account in motor.db.Scrapers.find()]

    return jsonify([scraper.model_dump() for scraper in scrapers])


@scrapers_bp.route('/update', methods=["POST"])
@token_required
@scraper_required
async def scraper_update(*, user: UserPermissions = None, updated_scraper: Scraper = None):
    if not user.scraper:
        return jsonify({"message": "You do not have permission to access this endpoint"}), 403
    
    await motor.db.Scrapers.update_one({"_id": updated_scraper.name}, {"$set": updated_scraper.mongo_dump()}, upsert=True)

    return jsonify({"message": "success"})
    

@scrapers_bp.route('/getall', methods=["GET"])
@owner_api_key_required
async def scraper_getall():
    host = request.args.get("host")
    if not host:
        return jsonify({"message": "No host provided"}), 400
    
    scrapers = [Scraper.mongo_load(account) async for account in motor.db.Scrapers.find({"host": host})]
    return jsonify([scraper.model_dump() for scraper in scrapers])

@scrapers_bp.route('/update/active', methods=["POST"])
@owner_api_key_required
@scraper_required
async def scraper_update_active(*, updated_scraper: Scraper = None):
    
    host = request.args.get("host")
    if not host:
        return jsonify({"message": "No host provided"}), 400
    
    await motor.db.Scrapers.update_many({"host": host}, {"$set": {"active": False}})
    await motor.db.Scrapers.update_one({"_id": updated_scraper.name}, {"$set": {"active": updated_scraper.active}})
    return jsonify({"message": "success"})

@scrapers_bp.route('/update/yoinked', methods=["POST"])
@owner_api_key_required
@scraper_required
async def scraper_update_yoinked(*, updated_scraper: Scraper = None):
    await motor.db.Scrapers.update_one({"_id": updated_scraper.name}, {"$set": updated_scraper.mongo_dump()})
    return jsonify({"message": "success"})

@scrapers_bp.route('/sync', methods=["POST"])
@owner_api_key_required
@scraper_required
async def scraper_add(*, scrapers: list[Scraper] = None):
    
    host = request.args.get("host")
    if not host:
        return jsonify({"message": "No host provided"}), 400

    current_scrapers = set([scraper["_id"] async for scraper in motor.db.Scrapers.find({"host": host})])
    
    new_scrapers = set([scraper.name for scraper in scrapers])

    if current_scrapers == new_scrapers:
        return jsonify({"message": "No changes required"})

    await motor.db.Scrapers.bulk_write(
        [
            UpdateOne(
                {"_id": scraper.name},
                {"$set": scraper.mongo_dump()},
                upsert=True
            ) for scraper in scrapers
        ]
    )

    await motor.db.Scrapers.delete_many({"_id": {"$nin": [scraper.name for scraper in scrapers]}, "host": host})
        
    return jsonify({"message": "success"})