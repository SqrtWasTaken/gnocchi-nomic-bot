import os
import re
import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from reactionmenu import ViewMenu, ViewButton

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

async def send_long_embeds(title, msg, interaction, max_length):
    if len(msg) > max_length:
        next_msg = msg[0:last_space_index(msg[0:max_length])]
        remaining = len(msg) - len(next_msg)
        await interaction.response.send_message(embed=discord.Embed(title=title, description=next_msg, color=0xf5c12f))
        while remaining > 0:
            if remaining > max_length:
                next_msg = msg[len(msg)-remaining:last_space_index(msg[0:len(msg)-remaining+max_length])]
                remaining -= len(next_msg)
                await interaction.channel.send(embed=discord.Embed(title=title, description=next_msg, color=0xf5c12f))
            else:
                await interaction.channel.send(embed=discord.Embed(title=title, description=msg[len(msg)-remaining:], color=0xf5c12f))
                break
    else:
        await interaction.response.send_message(embed=discord.Embed(title=title, description=msg, color=0xf5c12f))

async def send_menu(title, msg, interaction, max_length):
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)

    remaining = len(msg)
    while remaining > 0:
        if remaining > max_length:
            next_msg = msg[len(msg)-remaining:last_space_index(msg[0:len(msg)-remaining+max_length])]
            remaining -= len(next_msg)
            menu.add_page(discord.Embed(title=title, description=next_msg, color=0xf5c12f))
        else:
            menu.add_page(discord.Embed(title=title, description=msg[len(msg)-remaining:], color=0xf5c12f))
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
`/find_text [text]` - Look up rules containing a string. Ignores all alphanumeric characters.''', 
color=0xf5c12f))


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
async def find_text(interaction: discord.Interaction, text: str):
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

        #embedVar = discord.Embed(title="Results", description=desc, color=0xf5c12f)

        # msg = 'Rules containing `' + text.lower() + '`: ' + ', '.join(found_rules)
        # if len(msg) > 2000:
        #     await interaction.response.send_message('what\'s the point of using this to find ONE exact rule? YOUR message is TOO LONG\nanyway your results are: ' + ', '.join(found_rules))
        await interaction.response.send_message(embed=discord.Embed(title="Results", description=desc, color=0xf5c12f))

# ====================


bot.run(NOMIC_TOKEN)