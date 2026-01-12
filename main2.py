import os
import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Database setup
dirname = os.path.dirname(__file__)
data_file = os.path.join(dirname, 'rules.db')

# conn = sqlite3.connect(data_file)
# cursor = conn.cursor()

# # cursor.execute('''
# #     CREATE TABLE IF NOT EXISTS data (
# #         id INTEGER PRIMARY KEY AUTOINCREMENT,
# #         number INTEGER,
# #         text TEXT
# #     )
# # ''')

# # sample_data = [
# #     (205,'''An adopted rule change takes full effect at the moment of the completion of the vote that adopted it.''',1),
# #     (206,'''When a proposed rule change is defeated, the player who proposed it loses 10 points.''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),
# #     (1,'''text''',1),

# # ]

# # cursor.executemany('INSERT INTO data (number, text) VALUES (?, ?)', sample_data)

# conn.commit()
# conn.close()

# Load token
load_dotenv()
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise ValueError("Discord bot TOKEN environment variable not set.")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user}")

# rule lookup
@bot.tree.command(name="rule", description="Look up a rule.")
async def rule(interaction: discord.Interaction, number: int):
    conn = sqlite3.connect(data_file)
    cursor = conn.cursor()

    cursor.execute('SELECT text, mutable FROM data WHERE number=?', (number,))
    row = cursor.fetchone()

    if row is None:
        await interaction.response.send_message("Excuse me. It does not exist.")
    else:
        if row[1]:
            text = 'Mutable'
        else:
            text = 'Immutable'
        await interaction.response.send_message("**" + text + ' Rule ' + str(number) + "**\n\n" + row[0])

    conn.close()

bot.run(TOKEN)