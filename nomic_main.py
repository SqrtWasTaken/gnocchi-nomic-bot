import os
import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Database setup
dirname = os.path.dirname(__file__)
data_file = os.path.join(dirname, 'rules.db')

# Load token
load_dotenv()
NOMIC_TOKEN = os.getenv("NOMIC_TOKEN")

if NOMIC_TOKEN is None:
    raise ValueError("Discord bot NOMIC_TOKEN environment variable not set.")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user}")

# for sending long messages
def last_space_index(text):
    if text.rfind(' ') == -1:
        return len(text)
    else:
        return text.rfind(' ')

async def send_long_message(msg, interaction):
    if len(msg) > 2000:
        next_msg = msg[0:last_space_index(msg[0:2000])]
        remaining = len(msg) - len(next_msg)
        await interaction.response.send_message(next_msg)
        while remaining > 0:
            if remaining > 2000:
                next_msg = msg[len(msg)-remaining:last_space_index(msg[0:len(msg)-remaining+2000])]
                remaining -= len(next_msg)
                await interaction.channel.send(next_msg)
            else:
                await interaction.channel.send(msg[len(msg)-remaining:])
                break
    else:
        await interaction.response.send_message(msg)


# ======COMMANDS======
# help
@bot.tree.command(name="help", description="View commands.")
async def help(interaction: discord.Interaction):
    embedVar = discord.Embed(title="Help", description='''`/rule [number]` - Look up a rule.''', color=0xf5c12f)
    await interaction.response.send_message(embed=embedVar)


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
        await send_long_message("**" + text + ' Rule ' + str(number) + "**\n\n" + row[0], interaction)

    conn.close()
# ====================


bot.run(NOMIC_TOKEN)