import sys
import asyncio, aiohttp, logging, time, string, random, copy, json, asyncpg, re
from aiohttp import ClientSession
from datetime import datetime, date

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

import time
from datetime import datetime, date, timedelta

from cogs.const import *
from cogs.classes import *
from config.settings import settings



def unix_time():
    return int(datetime.utcnow().timestamp())

def get_lvl(xp: int):
    lvl = 0
    i = 1
    if xp > 0:
        while xp >= (i * (i + 1) * 5):
            lvl += 1
            i += 1
    return lvl

def starred_name(user):
    return "**{}**".format(user.name.replace('*', '\\*'))

def starred_dname(user):
    return "**{}**".format(user.display_name.replace('*', '\\*'))

def tagged_name(user):
    return "{0.name}#{0.discriminator}".format(user)

def tagged_name_id(user):
    return "{0.name}#{0.discriminator} [{0.id}]".format(user)

def tagged_dname(user):
    return "{0.display_name}#{0.discriminator}".format(user)

def tagged_gname(guild):
    return "{0.name} | {0.id}".format(guild)

def beauty_icon(url, default="webp"):
    url = str(url)
    urls = url.rsplit(".", maxsplit=1)
    code = urls[0]
    code = code.rsplit("/", maxsplit=1)
    if code[1].startswith("a_"):
        return code[0]+"/"+code[1]+".gif"
    if not default:
        return code[0]+"/"+code[1] + "." + urls[1].split("/", maxsplit=1)[0].split("?", maxsplit=1)[0]
    return code[0] + "/" + code[1] + "." + str(default)

def clear_name(name):
    return name.replace("\\", "\\\\").replace("\"", "\\\"").replace("\'", "\\\'")

def clear_icon(url):
    try:
        code = url.rsplit(".", maxsplit=1)
        code = code[0] + "." + code[1].split("/", maxsplit=1)[0].split("?", maxsplit=1)[0]
        return code
    except:
        return None

def split_int(value, char = "."):
    char = str(char)
    value = str(value)
    pattern = "([0-9]{3})"
    value = value[::-1]
    value = re.sub(pattern, r"\1"+char, value)
    value = value[::-1]
    value = value.lstrip(char)
    return value

def format_seconds(t, is_left=False, no_text: str="now"):
    t = int(t)
    d = t//86400
    h = (t%86400)//3600
    m = (t//60)%60
    s = t%60
    left = ""
    if d > 1:
        left = left + str(d) + " days "
    elif d > 0:
        left = left + str(d) + " day "
    else:
        if h > 1:
            left = left + str(h) + " hours "
        elif h > 0:
            left = left + str(h) + " hour "
        if m > 1:
            left = left + str(m) + " minutes "
        elif m > 0:
            left = left + str(m) + " minute "
        else:
            if s > 1:
                left = left + str(s) + " seconds "
            elif s > 0:
                left = left + str(s) + " seconds "
            else:
                return no_text
    if is_left:
        left = left + "left"
    return left


def welcomer_format(member, data, text: str=None):
    guild = member.guild
    if not text:
        text = data["welcome_text"]
    return text.format(
        name=member.name,
        mention=member.mention,
        guild=guild.name,
        server=guild.name,
        count=guild.member_count,
        member_id=member.id,
        display_name=member.display_name,
        guild_id=guild.id,
        emoji=data["emoji"],
        prefix=data["prefix"],
        timely=data["timely_award"],
        work=data["work_award"],
        private_voice=f"<@&{data['create_voice_id']}>" if data['create_voice_id'] else "-"
    )[:2000]


def get_embed(value):
    em = discord.Embed.Empty
    try:
        ret = json.loads(value)
        if ret and isinstance(ret, dict):
            text = ret.pop("text", None)

            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', str(ret.get("image", "")))
            if urls:
                ret["image"] = {"url": urls[0]}
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', str(ret.get("thumbnail", "")))
            if urls:
                ret["thumbnail"] = {"url": urls[0]}

            if ret:
                em = discord.Embed.from_dict(ret)
        else:
            text = value
    except:
        text = value[:2000]
        em = None
    return text, em


def is_admin(user):
    if user.guild_permissions.administrator:
        return True
    if user.guild.owner.id == user.id:
        return True
    return False

def seconds_to_args(t):
    t = int(t)
    d = t//86400
    h = (t%86400)//3600
    m = (t//60)%60
    s = t%60
    return d, h, m, s

async def context_init(ctx, cmd: str=None):
    nctx = ctx
    nctx.channel = nctx.message.channel
    nctx.author = nctx.message.author
    nctx.guild_id = nctx.message.guild.id
    nctx.const = await nctx.bot.get_cached_guild(nctx.message.guild)
    nctx.badges = await nctx.bot.get_badges(nctx.author)
    if not nctx.const or (cmd and not nctx.const["is_"+cmd]):
        await nctx.bot.true_send_error(ctx=ctx, channel=nctx.channel, error="global_not_available")
        return None

    nctx.lang = nctx.const["locale"]
    emoji = nctx.const["emoji"]
    emoji = re.sub(r'\D', '', emoji)
    if not emoji:
        emoji = nctx.const["emoji"]
    else:
        emoji = nctx.bot.get_emoji(int(emoji))
        if not emoji:
            emoji = "🍪"
        emoji = str(emoji)
    nctx.emoji = emoji

    nctx.embed = discord.Embed(colour=int(nctx.const["em_color"], 16) + 512)

    if nctx.const["is_nitro"]:
        nctx.is_nitro = True
    else:
        nctx.is_nitro = False

    return nctx
