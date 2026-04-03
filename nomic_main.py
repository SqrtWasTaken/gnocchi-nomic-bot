import os
import re
import discord
import sqlite3
import math
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from reactionmenu.views_menu import ViewMenu
from reactionmenu.buttons import ViewButton
import random
import logging
import typing

logging.basicConfig(level=logging.INFO)

import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Database setup
dirname = os.path.dirname(__file__)
data_file = os.path.join(dirname, 'data.db')

with sqlite3.connect(data_file) as conn:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER,
            text TEXT,
            mutable INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            discord_id INTEGER UNIQUE,
            name TEXT UNIQUE,
            score INTEGER NOT NULL DEFAULT 0
        )
        """
    )

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
    ping.start()


# logging

log_channel = 1486887458997272676

@tasks.loop(minutes=10)
async def ping():
    channel = bot.get_channel(log_channel)
    await channel.send('ping') # type: ignore


# ======Functions======

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
`/find_text [text] [hidden]` - Look up rules containing a string. Ignores all alphanumeric characters. Hidden (default=False) sends the message ephemerally.
`/challenge [n]` - Look up point values for multiplayer challenges.
`/stalin` - Execute step 1 of Stalin's algorithm.''', 
color=wheat_color))


# rule lookup
@bot.tree.command(name="rule", description="Look up a rule.")
@app_commands.describe(number='ordinal number of rule', 
                       max_length='Max chars in embeds, up to 4096. Enter 0 to send the whole rule')
async def rule(interaction: discord.Interaction, number: int, max_length: int=4096):
    conn = sqlite3.connect(data_file)
    cursor = conn.cursor()

    cursor.execute('SELECT text, mutable FROM rules WHERE number=?', (number,))
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
    cursor.execute('SELECT number, text FROM rules')
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


# random rule selector for tsardom
@bot.tree.command(name="stalin", description="Pick a random rule to be DESTROYED.")
async def stalin(interaction: discord.Interaction):
    conn = sqlite3.connect(data_file)
    cursor = conn.cursor()
    cursor.execute('SELECT number, text FROM rules')
    rows = cursor.fetchall()
    conn.close()

    rows.sort(key=lambda x: x[0]) # sort by number

    # roll
    roll = random.randint(0, len(rows)-1) # remember to add 1
    selected_rule = rows[roll]

    desc = 'Roll result (d' + str(len(rows)) + '): `' + str(roll+1) + '`\nSelected rule: `' + str(selected_rule[0]) + '`'
    # display roll result, selected rule
    await interaction.response.send_message(embed = discord.Embed(title="Time for the Purge.", description=desc, color=wheat_color))

# ====================


# Scores (by pyz18)
# ================== HELPERS ==================

def default_score():
    """90% of the average score of all players, rounded down"""
    with sqlite3.connect(data_file) as conn:
        cur = conn.cursor()
        cur.execute("SELECT AVG(score) FROM scores")
        avg_score = cur.fetchone()[0] or 0
        return int(avg_score * 0.9)


def add_score(score: int, discord_id: int | None = None, name: str | None = None):
    key_column = "discord_id" if discord_id is not None else "name"
    key_value = discord_id if discord_id is not None else name

    if key_value is None:
        raise ValueError("Either discord_id or name must be provided")

    with sqlite3.connect(data_file) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"INSERT INTO scores ({key_column}, score) VALUES (?, ?)",
                (key_value, score),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def update_score(delta: int, discord_id: int | None = None, name: str | None = None):
    key_column = "discord_id" if discord_id is not None else "name"
    key_value = discord_id if discord_id is not None else name

    if key_value is None:
        raise ValueError("Either discord_id or name must be provided")

    with sqlite3.connect(data_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE scores SET score = score + ?
            WHERE {key_column} = ?
            RETURNING score - ?, score
            """,
            (delta, key_value, delta),
        )
        row = cursor.fetchone()
        if row is None:
            return None, None
        before_score, after_score = row

        conn.commit()
        return before_score, after_score


def remove_score(discord_id: int | None = None, name: str | None = None):
    key_column = "discord_id" if discord_id is not None else "name"
    key_value = discord_id if discord_id is not None else name

    if key_value is None:
        raise ValueError("Either discord_id or name must be provided")

    with sqlite3.connect(data_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM scores WHERE {key_column} = ?",
            (key_value,),
        )
        conn.commit()
        return cursor.rowcount > 0  # Return True if a row was deleted


def get_scores(limit, offset):
    with sqlite3.connect(data_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT discord_id, name, score FROM scores
            ORDER BY score DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return cursor.fetchall()


def is_user(guild: discord.Guild | None, name: str):
    if guild is None:
        return
    target_lower = name.lower()
    return discord.utils.find(
        lambda m: target_lower in [m.display_name.lower(), m.name.lower()],
        guild.members,
    )


def player_info(
    guild: discord.Guild | None, member: discord.Member | None, name: str | None
):
    if member:
        return member.id, member.display_name
    if not name or not guild:
        return

    if member := is_user(guild, name):
        return member.id, member.display_name
    return None, name[:256].strip()


# ================== COMMANDS ==================

@bot.tree.command(description="Add a new player to the score database.")
@app_commands.describe(
    member="Discord user to add (mention or username).",
    name="Non-Discord player name to add (ignored if member is provided).",
)
async def add(
    interaction: discord.Interaction,
    member: discord.Member | None = None,
    name: str | None = None,
):
    if not (info := player_info(interaction.guild, member, name)):
        await interaction.response.send_message(
            "You must provide either a member or a name to add.",
            ephemeral=True,
        )
        return

    discord_id, name = info

    t = "Doug" if discord_id is None else "User"
    starting_score = default_score()
    if add_score(starting_score, discord_id, name):
        await interaction.response.send_message(
            f"{t} {name} was added with {starting_score} points!"
        )
    else:
        await interaction.response.send_message(
            f"{t} {name} was not added! They may already exist.",
            ephemeral=True,
        )


@bot.tree.command(description="Update or view a player's score.")
@app_commands.describe(
    member="Discord user to update (mention or username). Command user by default.",
    name="Non-Discord player name to update (ignored if member is provided).",
    delta="Amount to change the score by (default 0 to just view score).",
)
async def update(
    interaction: discord.Interaction,
    member: discord.Member | None = None,
    name: str | None = None,
    delta: int = 0,
):
    if not (info := player_info(interaction.guild, member, name)):
        discord_id = interaction.user.id
        name = interaction.user.display_name
    else:
        discord_id, name = info

    t = "Doug" if discord_id is None else "User"
    before_score, after_score = update_score(delta, discord_id, name)
    if before_score is None:
        await interaction.response.send_message(
            f"{t} {name} does not exist. Please add them first.",
            ephemeral=True,
        )
    elif delta == 0:
        await interaction.response.send_message(f"{t} {name}'s score: {before_score}")
    else:
        await interaction.response.send_message(
            f"{t} {name}'s score: {before_score} -> {after_score}"
        )


@bot.tree.command(description="Remove a player from the score database.")
@app_commands.describe(
    member="Discord user to remove (mention or username).",
    name="Non-Discord player name to remove (ignored if member is provided).",
)
async def remove(
    interaction: discord.Interaction,
    member: discord.Member | None = None,
    name: str | None = None,
):
    if not (info := player_info(interaction.guild, member, name)):
        await interaction.response.send_message(
            "You must provide either a member or a name to remove.",
            ephemeral=True,
        )
        return

    discord_id, name = info

    t = "Doug" if discord_id is None else "User"
    if remove_score(discord_id, name):
        await interaction.response.send_message(f"{t} {name} was removed!")
    else:
        await interaction.response.send_message(
            f"{t} {name} does not exist.", ephemeral=True
        )


@bot.tree.command(description="View the top players on the leaderboard.")
@app_commands.describe(
    number="Number of players to show on the leaderboard (default/max 25).",
    start="Place to start the leaderboard from (default 1).",
)
async def leaderboard(
    interaction: discord.Interaction, number: int = 25, start: int = 1
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True,
        )
        return

    top_scores = get_scores(limit=min(number, 25), offset=max(start - 1, 0))

    embed = discord.Embed(title="Leaderboard", color=discord.Color.blue())

    for i, (discord_id, name, score) in enumerate(top_scores, start=start):
        if discord_id is not None:
            user = guild.get_member(discord_id)
            display_name = user.display_name if user else f"User {discord_id}"
        else:
            display_name = name

        t = "Doug" if discord_id is None else "User"

        embed.add_field(
            name=f"{i}. {t} {display_name}", value=f"Score: {score}", inline=False
        )

    await interaction.response.send_message(embed=embed)


bot.run(NOMIC_TOKEN)