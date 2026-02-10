import os
import re
import discord
import sqlite3
import math
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from reactionmenu.views_menu import ViewMenu
from reactionmenu.buttons import ViewButton

import logging

logging.basicConfig(level=logging.INFO)

import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

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

wheat_color = 0xf5c12f

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot logged in as {bot.user}")

# for sending long messages
def last_space_index(text):
    if text.rfind(' ') == -1:
        return len(text) - 1
    else:
        return text.rfind(' ')

async def send_long_embeds(title, msg, interaction, max_length):
    if len(msg) > max_length:
        next_msg = msg[0:last_space_index(msg[0:max_length])]
        remaining = len(msg) - len(next_msg)
        await interaction.response.send_message(embed=discord.Embed(title=title, description=next_msg, color=wheat_color))
        while remaining > 0:
            if remaining > max_length:
                next_msg = msg[len(msg)-remaining:(len(msg)-remaining + last_space_index(msg[len(msg)-remaining:len(msg)-remaining+max_length])+1)] # this works. trust.
                remaining -= len(next_msg)
                await interaction.channel.send(embed=discord.Embed(title=title, description=next_msg, color=wheat_color))
            else:
                await interaction.channel.send(embed=discord.Embed(title=title, description=msg[len(msg)-remaining:], color=wheat_color))
                break
    else:
        await interaction.response.send_message(embed=discord.Embed(title=title, description=msg, color=wheat_color))

async def send_menu(title, msg, interaction, max_length):
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)

    remaining = len(msg)
    while remaining > 0:
        if remaining > max_length:
            next_msg = msg[len(msg)-remaining:(len(msg)-remaining + last_space_index(msg[len(msg)-remaining:len(msg)-remaining+max_length])+1)]
            remaining -= len(next_msg)
            menu.add_page(discord.Embed(title=title, description=next_msg, color=wheat_color))
        else:
            menu.add_page(discord.Embed(title=title, description=msg[len(msg)-remaining:], color=wheat_color))
            break
    
    menu.add_button(ViewButton.back())
    menu.add_button(ViewButton.next())
    
    await menu.start()

# ======COMMANDS======
# help
@bot.tree.command(name="help", description="View commands.")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="Help", 
                            description='''`/rule [number] [max_length]` - Look up a rule. Enter 0 to send the whole rule across multiple messages, or a number between 1-4096 to send a single embed with pagination.
`/find_text [text]` - Look up rules containing a string. Ignores all alphanumeric characters.
`/challenge [n]` - Look up point values for multiplayer challenges.''', 
color=wheat_color))


# rule lookup
@bot.tree.command(name="rule", description="Look up a rule.")
@app_commands.describe(number='ordinal number of rule', 
                       max_length='Max chars in embeds, up to 4096. Enter 0 to send the whole rule')
async def rule(interaction: discord.Interaction, number: int, max_length: int=4096):
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

        if max_length == 0:
            await send_long_embeds(text+' Rule ' + str(number), row[0], interaction, 4096)
        else:
            if max_length > 0 and max_length <= 4096:
                await send_menu(text+' Rule ' + str(number), row[0], interaction, max_length)
            else:
                await interaction.response.send_message('Please enter a number between 0 and 4096', ephemeral=True)

    conn.close()


# find rule
@bot.tree.command(name="find_text", description="Find rules containing a string.")
@app_commands.describe(text='Text to be searched for', hidden='Send as an ephemeral message')
async def find_text(interaction: discord.Interaction, text: str, hidden: bool=False):
    conn = sqlite3.connect(data_file)
    cursor = conn.cursor()
    cursor.execute('SELECT number, text FROM data')
    rows = cursor.fetchall()
    conn.close()

    found_rules = []
    for row in rows:
        if re.sub(r'[^a-zA-Z0-9]+', '', text.lower()) in re.sub(r'[^a-zA-Z0-9]+', '', row[1].lower()):
            found_rules.append((row[0], ' '.join(row[1].split(' ')[0:min(5, len(row[1].split(' ')))])))
    found_rules.sort(key=lambda tup: tup[0])

    if len(found_rules) == 0:
        await interaction.response.send_message('Excuse me. It does not exist.')
    else:
        desc = 'Rules containing `' + text.lower() + '`:\n'
        for rule in found_rules:
            desc += '\n' + str(rule[0]) + ': ' + rule[1] + '...'

        await interaction.response.send_message(embed=discord.Embed(title="Results", description=desc, color=wheat_color), ephemeral=hidden)


# challenge point calculator
@bot.tree.command(name="challenge", description="Look up challenge points for n players.")
@app_commands.describe(players='Number of players in the challenge')
async def challenge(interaction: discord.Interaction, players: int):
    if players <= 1:
        await interaction.response.send_message('You need to challenge at least 2 players!')
    elif players % 2 == 0:
        i = max(1, math.ceil(10 / (players-1)))
        points = [str(i*d) for d in range(-players+1, players, 2)]
        msg = ', '.join(points)
        if len(msg) > 2000:
            await interaction.response.send_message('why is bro trying to challenge the whole world')
        else:
            await interaction.response.send_message(', '.join(points))
    else:
        i = max(1, math.ceil(20 / (players-1)))        
        points = [str(i*d) for d in range(-(players-1)//2, (players+1)//2)]
        msg = ', '.join(points)
        if len(msg) > 2000:
            await interaction.response.send_message('why is bro trying to challenge the whole world')
        else:
            await interaction.response.send_message(', '.join(points))

# ====================


bot.run(NOMIC_TOKEN)