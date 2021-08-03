import discord
from discord.ext import commands
import configparser
import sqlite3

config = configparser.ConfigParser()
config.read('config.ini')

DB = None

intents = discord.Intents.all()
client = commands.Bot(command_prefix = 'rpg!', intents=intents)

guild_ids = [int(config['DiscordBot']['guild_id'])]
channel_id = int(config['DiscordBot']['channel_id'])
admin_role_id = int(config['DiscordBot']['admin_role_id'])
guild = None

@client.event
async def on_ready():
    global guild
    print("Connected as : ")
    print(f"{client.user.name}#{client.user.discriminator}")
    print(client.user.id)
    print("-----------------")
    guild = client.get_guild(guild_ids[0])
    # await client.change_presence(activity=discord.Game(name=''))
    
@client.event
async def on_member_update(before, after):
    if len(before.roles) <= len(after.roles) and before.display_name == after.display_name: return
    db = get_db()
    if db.execute("SELECT * FROM discord_user WHERE id_user = ?", (after.id,)).fetchone() is not None: return
    try: m_id, fn, ln, year, av = get_user_info(after)
    except ValueError: return
    db.execute("INSERT INTO discord_user VALUES (?, ?, ?, ?, ?)", (m_id, fn, ln, year, av,))


@client.command(aliases=['syncro'])
async def sync(ctx, member:discord.Member = None):
    if not is_admin(ctx.message.author): return
    db = get_db()
    
    if member is not None:
        try: m_id, fn, ln, year, av = get_user_info(member)
        except ValueError: 
            await ctx.send(":x: Couldn't gather member information.")
            return
        if db.execute("SELECT * FROM discord_user WHERE id_user = ?", (member.id,)).fetchone() is not None: 
            db.execute("UPDATE discord_user SET firstname = ?, lastname = ?, year = ?, avatar = ? WHERE id_user = ?",
                       (fn, ln, year, m_id, av,))
        else: 
            db.execute("INSERT INTO discord_user VALUES (?, ?, ?, ?, ?)", (m_id, fn, ln, year, av,))
        db.commit()
        await ctx.send(f":white_check_mark: Successfully synchronized `{fn} {ln} [{year}]`.")
        return
    
    db.execute("DELETE FROM discord_user")
    count = 0
    for m in guild.members:
        try: m_id, fn, ln, year, av = get_user_info(m)
        except ValueError: continue
        db.execute("INSERT INTO discord_user (id_user, firstname, lastname, year, avatar) VALUES (?, ?, ?, ?, ?)",
                   (m_id, fn, ln, year, av,))
        count += 1
    db.commit()
    
    if count == 0: await ctx.send(":x: Something went wrong, `0` member synchronized.")
    else: await ctx.send(f":white_check_mark: Successfully synchronized `{count}` member{'s' if count > 1 else ''}.")
            
    
def get_user_info(member):
    nick = member.nick
    if nick is None: raise ValueError("Bad User") # not renamed
    name = nick.split(" - ")[0].split(" ")
    firstname, lastname = ' '.join(name[:-1]), name[-1]
    
    roles = member.roles
    r_name = ""
    for role in roles:
        r_name = role.name
        if "Promo" in r_name: break
    else: raise ValueError("Bad User") # no promo roles
    year = int("20" + r_name[-5:].split("-")[0])
    
    return member.id, firstname, lastname, year, str(member.avatar_url_as(static_format='png', size=256))

def is_admin(user):
    return admin_role_id in [r.id for r in user.roles]
    
def get_db():
    global DB
    if DB is None:
        DB = sqlite3.connect(
            'instance/database.sqlite',
            detect_types = sqlite3.PARSE_DECLTYPES
        )
    return DB


client.run(str(config['DiscordBot']['token']))