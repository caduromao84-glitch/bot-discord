import discord
from discord.ext import commands, tasks
import os
import json
import datetime as dt

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")
ROLE_NAME = "Aviso Horario"
CONFIG_FILE = "config.json"

POST_TIME = dt.time(hour=5, minute=0)     # 05:00
CHECK_TIME = dt.time(hour=17, minute=0)   # 17:00

OPCOES = {
    "🕑": "14:00",
    "🕒": "15:00",
    "🕓": "16:00",
    "🕔": "17:00",
    "🕕": "18:00",
    "🕖": "19:00",
    "🕗": "20:00",
    "🕘": "21:00",
    "🕙": "22:00",
}

# ================= BOT SETUP =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG FILE =================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

config = load_config()

# ================= EVENTS =================

@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user}")
    if not daily_post.is_running():
        daily_post.start()
    if not daily_check.is_running():
        daily_check.start()

# ================= COMANDO SETCANAL =================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setcanal(ctx):
    config["channel_id"] = ctx.channel.id
    save_config(config)
    await ctx.send(f"✅ Canal definido para votações: {ctx.channel.mention}")

# ================= TAREFA 05:00 =================

@tasks.loop(time=POST_TIME)
async def daily_post():
    channel_id = config.get("channel_id")
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    today = dt.date.today().isoformat()

    descricao = "\n".join([f"{emoji} = {hora}" for emoji, hora in OPCOES.items()])

    embed = discord.Embed(
        title="🗳️ Votação diária de horário",
        description=(
            f"{descricao}\n\n"
            "⏳ Tens até às **17:00** para votar."
        ),
        color=discord.Color.blurple()
    )

    msg = await channel.send(embed=embed)

    for emoji in OPCOES.keys():
        await msg.add_reaction(emoji)

    config["last_poll"] = {
        "date": today,
        "channel_id": channel_id,
        "message_id": msg.id
    }
    save_config(config)

# ================= TAREFA 17:00 =================

@tasks.loop(time=CHECK_TIME)
async def daily_check():
    last_poll = config.get("last_poll")
    if not last_poll:
        return

    today = dt.date.today().isoformat()
    if last_poll.get("date") != today:
        return

    channel = bot.get_channel(last_poll["channel_id"])
    if not channel:
        return

    try:
        msg = await channel.fetch_message(last_poll["message_id"])
    except:
        return

    guild = msg.guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)

    if not role:
        await channel.send("❌ Cargo 'Aviso Horario' não encontrado.")
        return

    votantes_ids = set()

    for reaction in msg.reactions:
        if str(reaction.emoji) in OPCOES:
            async for user in reaction.users():
                if not user.bot:
                    votantes_ids.add(user.id)

    membros = [m for m in guild.members if not m.bot]
    nao_votaram = [m for m in membros if m.id not in votantes_ids]

    count = 0
    for membro in nao_votaram:
        if role not in membro.roles:
            try:
                await membro.add_roles(role)
                count += 1
            except:
                pass

    if count > 0:
        await channel.send(
            f"⏰ Votação encerrada.\n"
            f"⚠️ {count} pessoa(s) não votaram e receberam o cargo **Aviso Horario**."
        )
    else:
        await channel.send("🎉 Toda a gente votou hoje!")

# ================= RUN =================

bot.run(TOKEN)
