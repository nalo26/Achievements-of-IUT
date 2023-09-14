import discord
from discord.ext import commands
import configparser
import psycopg2
import psycopg2.extras
import asyncio
import requests as rq
import datetime
from dateutil import parser

config = configparser.ConfigParser()
config.read('dev.config.ini')

HOST = config['Database']['host']
DATABASE = config['Database']['base']
USERNAME = config['Database']['user']
PASSWORD = config['Database']['pass']

DB = None
DIFFICULTIES = [0x6AA84F, 0x4A86EF, 0xE69137, 0xB10000, 0x674EA7]
SYMBOLS = [':green_square:', ':blue_square:', ':orange_square:', ':red_square:', ':purple_square:']

intents = discord.Intents.all()
client = commands.Bot(command_prefix = 'rpg!', intents=intents)

guild_ids = int(config['DiscordBot']['guild_id'])
channel_id = int(config['DiscordBot']['channel_id'])
admin_role_id = int(config['DiscordBot']['admin_role_id'])
ping_role_id = int(config['DiscordBot']['ping_role_id'])
guild = None
channel = None

base_url = config['DiscordApp']['base_url']
api_url = config['DiscordApp']['api_url']

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
    # connection, cursor = get_db()
    # cursor.execute("SELECT * FROM discord_user WHERE id_user = %s", (after.id,))
    # if cursor.fetchone() is not None: return
    # try: m_id, fn, ln, year, av = get_user_info(after)
    # except ValueError: return
    # cursor.execute("INSERT INTO discord_user VALUES (%s, %s, %s, %s, %s)", (m_id, fn, ln, year, av,))
    # connection.commit()
    sync(None, after, False)


@client.command()
async def roles(ctx):
    if not is_admin(ctx.message.author): return
    connection, cursor = get_db()
    role = ctx.guild.get_role(ping_role_id)
    
    cursor.execute("SELECT * FROM users")
    for u in cursor.fetchall():
        await ctx.guild.get_member(u['id_user']).add_roles(role)

@client.command(aliases=['syncro'])
async def sync(ctx, member:discord.Member = None, feedback = True):
    if not is_admin(ctx.message.author): return
    connection, cursor = get_db()
    
    if member is not None:
        try: m_id, fn, ln, year, av = get_user_info(member)
        except ValueError: 
            if feedback: await ctx.send(":x: Couldn't gather member information.")
            return
        cursor.execute("SELECT * FROM discord_user WHERE id_user = %s", (member.id,))
        if cursor.fetchone() is not None: 
            cursor.execute("UPDATE discord_user SET firstname = %s, lastname = %s, year = %s, avatar = %s WHERE id_user = %s",
                       (fn, ln, year, av, m_id,))
        else: 
            cursor.execute("INSERT INTO discord_user VALUES (%s, %s, %s, %s, %s)", (m_id, fn, ln, year, av,))
        connection.commit()
        if feedback: await ctx.send(f":white_check_mark: Successfully synchronized `{fn} {ln} [{year}]`.")
        return
    
    added, edited = 0, 0
    for m in guild.members:
        try: m_id, fn, ln, year, av = get_user_info(m)
        except ValueError: continue
        cursor.execute("SELECT * FROM discord_user WHERE id_user = %s", (m_id,))
        user = cursor.fetchone()
        if user is not None: 
            cursor.execute("UPDATE discord_user SET firstname = %s, lastname = %s, year = %s, avatar = %s WHERE id_user = %s",
                       (fn, ln, year, av, m_id,))
            edited += 1
        else:
            cursor.execute("INSERT INTO discord_user VALUES (%s, %s, %s, %s, %s)", (m_id, fn, ln, year, av,))
            added += 1
    connection.commit()
    if feedback:
        if added == edited == 0: await ctx.send(":x: Something went wrong, `0` member synchronized.")
        else: await ctx.send(f":white_check_mark: Successfully added `{added}` member(s) and edited `{edited}` member(s).")
    
@client.command(aliases=['profil', 'me'])
async def profile(ctx, member:discord.Member = None):
    if member is None: member = ctx.message.author
    user = rq.get(f"{api_url}/get_user?id={member.id}").json()
    if len(user) == 0:
        await ctx.send(f":x: `{member.display_name}` is not registered.")
        return
    
    embed = discord.Embed(title=f"Profil de {user.get('firstname')} {user.get('lastname')} [{user.get('promotion_year')}]",
                          url=f"{base_url}/profile/{user.get('id_user')}")
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
    #                                                           Sat, 18 Sep 2021 16:46:00 GMT
    embed.timestamp = parser.parse(user.get('join_date'))
    
    await ctx.send(embed=embed)

@client.command(aliases=['classement', 'top', 'lead'])
async def leaderboard(ctx, year=None):
    leaderboard = rq.get(f"{api_url}/get_leaderboard{f'?year={year}' if year is not None else ''}").json()
    if len(leaderboard) == 0:
        await ctx.send(f":x: `{year}` is not a valid year.")
        return
    
    emoji = [':first_place:', ':second_place:', ':third_place:']
    last = -1
    
    if leaderboard.get('year') == 0:
        embed = discord.Embed(title=":trophy: Classement général", url=f"{base_url}/leaderboard")
    else:
        embed = discord.Embed(title=f":trophy: Classement promo {leaderboard.get('year')}", url=f"{base_url}/leaderboard/{year}")
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
        connection = psycopg2.connect(
            host=HOST,
            database=DATABASE,
            user=USERNAME,
            password=PASSWORD
        )
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        DB = (connection, cursor)
    return DB

def embed_new_ach(event):
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM achievement WHERE id_achievement = %s", (event['id_achievement'],))
    ach = cursor.fetchone()
    ach_list = [ach]
    while ach['parent_id'] is not None:
        cursor.execute("SELECT * FROM achievement WHERE id_achievement = %s", (ach['parent_id'],))
        ach = cursor.fetchone()
        ach_list.append(ach)

    ach = ach_list[0]
    embed = discord.Embed(title=ach['name'], color=DIFFICULTIES[ach['difficulty']-1])
    desc = "*" + ach['lore'].replace('<br>', '\n') + "*\n\n"
    for i, a in enumerate(ach_list[::-1]):
        if i != 0: desc += f"{'─'*((i-1)*3)}└──"
        desc += SYMBOLS[a['difficulty']-1] + " "
        if i == len(ach_list)-1: desc += f"**{a['name']}** :new:"
        else: desc += a['name']
        desc += "\n"
    embed.description = desc
    embed.set_footer(text = "Créé le")
    embed.timestamp = event['event_time']

    return embed


def embed_save_score(event):
    user = rq.get(f"{api_url}/get_user?id={event['id_user']}").json()
    ach  = rq.get(f"{api_url}/get_achievement?id={event['id_achievement']}").json()
    embed = discord.Embed(title=ach.get('name'), color=DIFFICULTIES[ach.get('difficulty')-1])
    embed.set_author(
        name=f"par {user.get('firstname')} {user.get('lastname')}",
        url=f"{base_url}/profile/{user.get('id_user')}",
        icon_url=guild.get_member(user.get('id_user')).avatar_url
    )
    embed.description = ach.get('lore').replace('<br>', '\n')
    embed.set_footer(text = "Réalisé le")
    embed.timestamp = event['event_time']
    
    return embed

async def background_task():
    global guild, channel
    
    await client.wait_until_ready()
    guild = client.get_guild(guild_ids)
    channel = guild.get_channel(channel_id)
    connection, cursor = get_db()

    timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()
    cursor.execute(f"SET TIME ZONE {timezone};")

    while not client.is_closed():
        cursor.execute("SELECT * FROM event_new_ach ORDER BY id_event")
        events_new_ach = cursor.fetchall()
        for i, event in enumerate(events_new_ach):
            cursor.execute("DELETE FROM event_new_ach WHERE id_event = %s", (event['id_event'],))
            connection.commit()
            if i == 0:
                are_some = len(events_new_ach) > 1
                text = f"<@&{ping_role_id}> {len(events_new_ach)} "
                text += "nouveaux" if are_some else "nouvel"
                text += f" achievement{'s' if are_some else ''} "
                text += "sont" if are_some else "est"
                text += f" disponible{'s' if are_some else ''} ! :bell:"
                await channel.send(text, embed=embed_new_ach(event))
            else:
                await channel.send(embed=embed_new_ach(event))
            await asyncio.sleep(2)
        
        cursor.execute("SELECT * FROM event_save_score ORDER BY id_event")
        events_save_score = cursor.fetchall()
        for event in events_save_score:
            cursor.execute("DELETE FROM event_save_score WHERE id_event = %s", (event['id_event'],))
            connection.commit()
            await channel.send(embed=embed_save_score(event))
            await asyncio.sleep(2)

        await asyncio.sleep(28)


client.loop.create_task(background_task())
client.run(str(config['DiscordBot']['token']))