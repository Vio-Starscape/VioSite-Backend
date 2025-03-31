from quart import Blueprint, jsonify, current_app, request, render_template, send_file
from database import motor
from helpers import token_required
from Objects import UserPermissions
from io import BytesIO
import uuid
import os
import base64
from pyppeteer import launch

terminal_bp = Blueprint("terminal", __name__)

TEMP_DIR = os.path.join(os.getcwd(), 'workspace', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

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
    
async def insert_roblox_users_to_market(market_data: dict, roblox_users = None) -> None:
        """Insert Roblox Users into the market data.
        
        This function will replace the Vendor ID with a Roblox User Object instead of the ID.
        """
        if roblox_users is None:
            roblox_users = {doc["_id"]: doc async for doc in motor.db["Roblox"].find()}

        for value in market_data["items"].values():
            for listing in value["buy"]:
                try:
                    listing[2] = roblox_users[listing[2]]
                except KeyError:
                    value["buy"].remove(listing)
            for listing in value["sell"]:
                try:
                    listing[2] = roblox_users[listing[2]]
                except KeyError:
                    value["sell"].remove(listing)
        return market_data
    
@terminal_bp.route('/image/<item>', methods=["GET"], strict_slashes=False)
async def image(item):
    if not item:
        return jsonify({"message": "No item provided"}), 400
    
    item_instance = (await motor.db.Market.find_one({f"items.{item}": {"$exists": True}}, {f"items.{item}": 1, "time_scanned":1}, sort={"_id": -1}))
    item_instance = await insert_roblox_users_to_market(item_instance)
    
    if not item_instance:
        return jsonify({"message": "Item not found"}), 404
    
    item_info = item_instance["items"][item]
    item_info["time_scanned"] = item_instance["time_scanned"].isoformat()
    
    css_path = os.path.join(current_app.root_path, "templates", "terminal", "mini.css")
    anta_path = os.path.join(current_app.root_path, "templates", "terminal", "anta.b64")
    
    with open(css_path, "r") as f:
        tailwind_css = f.read()
        
    with open(anta_path, "r") as f:
        anta_base64 = base64.b64decode(f.read())
    
    # Render the HTML template with item_info
    html = await render_template("terminal/item_preview.html", item=item_info, tailwind_css=tailwind_css, anta_base64=anta_base64)

    # Generate a unique filename for the temporary image
    temp_filename = f"{uuid.uuid4()}.html"
    temp_filepath = os.path.join(TEMP_DIR, temp_filename)
    with open(temp_filepath, 'w') as f:
        f.write(html)

    try:
        
        browser = await launch(
            headless=True,
            executablePath="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        
        page = await browser.newPage()
        await page.goto(f"file://{temp_filepath}", waitUntil="load", timeout=10_000)
        
        await page.waitForSelector("body", timeout=5000)
        
        await page.setViewport({
            "width": 1050,
            "height": 1000  # Temp height, just to let the page layout correctly
        })
        
        bounding_box = await page.evaluate('''() => {
            const el = document.querySelector("#screenshot-root");
            const rect = el.getBoundingClientRect();
            return {
                width: Math.ceil(rect.width),
                height: Math.ceil(rect.height)
            };
        }''')

        await page.setViewport({
            "width": 1050,
            "height": bounding_box["height"]
        })
        
        image_bytes = await page.screenshot(full_page=False)
        await browser.close()
        
        os.remove(temp_filepath)  # Remove the temporary HTML file

        # Send the file as a response

        return await send_file(
            BytesIO(image_bytes), 
            mimetype="image/png", 
            as_attachment=False, 
            attachment_filename=f"{item}.png"
        )
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500