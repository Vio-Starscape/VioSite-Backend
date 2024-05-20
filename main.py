import os
import logging
from quart import Quart
from quart_cors import cors
from dotenv import load_dotenv
from database import motor

from blueprint.authentication import authentication
from blueprint.scrapers import scrapers_bp
from blueprint.terminal import terminal_bp

load_dotenv(override=True)

logger = logging.getLogger(__name__)

app = Quart(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["OWNER_API_KEY"] = os.getenv("OWNER_API_KEY")

app.config["DISCORD_BASE_URL"] = "https://discord.com/api/v10"
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")

app.config["MONGO_URI"] = os.getenv("MONGO_URI")

app = cors(
    app,
    allow_origin=os.getenv("ALLOW_ORIGIN") or "http://localhost:3000",
    allow_credentials=True,
    allow_headers=[
        "Authorization",
        "Content-Type",
        "x-api-key",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials"
        ]
    )
motor.init_app(app)

app.register_blueprint(authentication, url_prefix="/api/auth")
app.register_blueprint(scrapers_bp, url_prefix="/api/scrapers")
app.register_blueprint(terminal_bp, url_prefix="/api/terminal")

if __name__ == "__main__":
    app.run(debug=True)