import discord
from discord.ext import commands
import configparser
import sqlite3
import asyncio
import requests as rq
from datetime import datetime

config = configparser.ConfigParser()
config.read('config.ini')

DB = None
DIFFICULTIES = [0x6AA84F, 0x4A86EF, 0xE69137, 0xB10000, 0x674EA7]

intents = discord.Intents.all()
client = commands.Bot(command_prefix = 'rpg!', intents=intents)

guild_ids = int(config['DiscordBot']['guild_id'])
channel_id = int(config['DiscordBot']['channel_id'])
admin_role_id = int(config['DiscordBot']['admin_role_id'])
guild = None
channel = None

base_uri = config['DiscordApp']['base_uri']
api_uri = base_uri + config['DiscordApp']['api_uri']

@client.event
async def on_ready():
    print("Connected as:")
    print(f"{client.user.name}#{client.user.discriminator}")
    print(client.user.id)
    print("-----------------")
    # await client.change_presence(activity=discord.Game(name=''))

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(":x: Member not found.")
    else:
        raise error

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
    
@client.command(aliases=['profil', 'me'])
async def profile(ctx, member:discord.Member = None):
    if member is None: member = ctx.message.author
    user = rq.get(f"{api_uri}/get_user?id={member.id}").json()
    if len(user) == 0:
        await ctx.send(f":x: `{member.display_name}` is not registered.")
        return
    
    embed = discord.Embed(title=f"Profil de {user.get('firstname')} {user.get('lastname')} [{user.get('promotion_year')}]",
                          url=f"{base_uri}/profile/{user.get('id_user')}")
    embed.set_thumbnail(url=str(member.avatar_url))
    content  = f":bar_chart: __Score total : **{user.get('score')}pts**__\n"
    content += f":medal: Classement général : **#{user.get('global_rank')}**\n"
    content += f":military_medal: Classement [{user.get('promotion_year')}] : **#{user.get('year_rank')}**"
    embed.description = content
    
    ach  = f":green_circle: {user.get('count_easy')} / "
    ach += f":blue_circle: {user.get('count_normal')} / "
    ach += f":orange_circle: {user.get('count_hard')} / "
    ach += f":red_circle: {user.get('count_hardcore')} / "
    ach += f":purple_circle: {user.get('count_impossible')}"
    embed.add_field(name=f"Achievements complétés : {len(user.get('completed_achievements'))}", value=ach)
    
    embed.set_footer(text = "A rejoint le")
    embed.timestamp = datetime.strptime(user.get('join_date'), "%Y-%m-%d %H:%M:%S")
    
    await ctx.send(embed=embed)

@client.command(aliases=['classement', 'top', 'lead'])
async def leaderboard(ctx, year=None):
    leaderboard = rq.get(f"{api_uri}/get_leaderboard{f'?year={year}' if year is not None else ''}").json()
    if len(leaderboard) == 0:
        await ctx.send(f":x: `{year}` is not a valid year.")
        return
    
    emoji = [':first_place:', ':second_place:', ':third_place:']
    last = -1
    
    if leaderboard.get('year') == 0:
        embed = discord.Embed(title=":trophy: Classement général", url=f"{base_uri}/leaderboard")
    else:
        embed = discord.Embed(title=f":trophy: Classement promo {leaderboard.get('year')}", url=f"{base_uri}/leaderboard/{year}")
    content = ""
    for i, user in enumerate(leaderboard.get('users')[:20]):
        score = user.get('score')
        if score != last:
            ind = emoji[i] if i < len(emoji) else f"{i+1} "
        content += f"{ind}: **{user.get('name')}** ({score}pts)\n"
        last = score
    if content == "": content = "*Aucun participant n'a été trouvé !*"
    embed.description = content
    
    await ctx.send(embed=embed)


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
        DB.row_factory = sqlite3.Row
    return DB

def embed_event(event):
    user = rq.get(f"{api_uri}/get_user?id={event['id_user']}").json()
    ach  = rq.get(f"{api_uri}/get_achievement?id={event['id_achievement']}").json()
    embed = discord.Embed(title=ach.get('name'), color=DIFFICULTIES[ach.get('difficulty')-1])
    embed.set_author(
        name=f"par {user.get('firstname')} {user.get('lastname')}",
        url=f"{base_uri}/profile/{user.get('id_user')}",
        icon_url=guild.get_member(user.get('id_user')).avatar_url
    )
    embed.description = ach.get('lore')
    embed.set_footer(text = "Réalisé le")
    embed.timestamp = datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
    
    return embed

async def background_task():
    global guild, channel
    
    await client.wait_until_ready()
    guild = client.get_guild(guild_ids)
    channel = guild.get_channel(channel_id)
    db = get_db()
    
    while not client.is_closed():
        events = db.execute("SELECT * FROM event ORDER BY id_event").fetchall()
        for event in events:
            db.execute("DELETE FROM event WHERE id_event = ?", (event['id_event'],))
            db.commit()
            await channel.send(embed=embed_event(event))
            await asyncio.sleep(2)
        await asyncio.sleep(30)


client.loop.create_task(background_task())
client.run(str(config['DiscordBot']['token']))