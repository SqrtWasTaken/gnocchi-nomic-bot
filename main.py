
import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from pymongo import MongoClient, errors
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

if TOKEN is None:
    raise ValueError("Discord bot TOKEN environment variable not set.")


# MongoDB connection globals
mongo_client = None
db = None

async def mongo_connect_loop():
    global mongo_client, db
    delay = 10
    while True:
        try:
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            mongo_client.server_info()  # Force connection check
            db = mongo_client["Nomic"]
            print("Connected to MongoDB.")
            return
        except Exception as e:
            print(f"Could not connect to MongoDB: {e}. Retrying in {delay}s...")
            db = None
            await asyncio.sleep(delay)
            delay = min(delay * 2, 600)  # Cap at 10 minutes

async def mongo_reconnect_watcher():
    global db
    while True:
        if db is None:
            await mongo_connect_loop()
        await asyncio.sleep(5)

# Bot intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)



# Sync slash commands and start mongo watcher when bot is ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user}")
    bot.loop.create_task(mongo_reconnect_watcher())



# join
@bot.tree.command(name="join_inactive", description="Join the Inactive Players List.")
async def join(interaction: discord.Interaction):
    user_id = interaction.user.id

    if db is None:
        await interaction.response.send_message("Database is currently unavailable. Please try again later.", ephemeral=True)
        return
    try:
        # Check if already in DB
        if db["inactive_list"].find_one({"user_id": user_id}):
            await interaction.response.send_message(f"You are already on the Inactive Players List!", ephemeral=True)
            return

        # Add to DB
        db["inactive_list"].insert_one({"user_id": user_id})
        await interaction.response.send_message(f"<@{user_id}> joined the Inactive Players List. 💤", ephemeral=True)
    except errors.PyMongoError as e:
        await interaction.response.send_message(f"The database is doing weird things, pls ping me (sqrt)\nError message: {str(e)}", ephemeral=True)



# leave
@bot.tree.command(name="leave_inactive", description="Leave the Inactive Players List.")
async def leave(interaction: discord.Interaction):
    user_id = interaction.user.id

    if db is None:
        await interaction.response.send_message("Database is currently unavailable. Please try again later.", ephemeral=True)
        return
    try:
        # Check if not in DB
        if not db["inactive_list"].find_one({"user_id": user_id}):
            await interaction.response.send_message(f"You are not on the Inactive Players List!", ephemeral=True)
            return

        # Remove from DB
        db["inactive_list"].delete_one({"user_id": user_id})
        await interaction.response.send_message(f"<@{user_id}> left the Inactive Players List.", ephemeral=True)
    except errors.PyMongoError as e:
        await interaction.response.send_message(f"The database is doing weird things, pls ping me (sqrt)\nError message: {str(e)}", ephemeral=True)

bot.run(TOKEN)