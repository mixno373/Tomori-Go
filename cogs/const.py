import os, sys
import asyncio
import logging
import re

import discord

from datetime import datetime, date, timedelta

from PIL import Image, ImageChops, ImageFont, ImageDraw, ImageSequence, ImageFilter, GifImagePlugin
from PIL.GifImagePlugin import getheader, getdata
from functools import partial
from io import BytesIO

from config.settings import settings




logger = logging.getLogger('tomori')
logger.setLevel(logging.DEBUG)
now = datetime.utcnow()
logname = 'logs/log{}_{}.log'.format(now.day, now.month)
try:
    os.mkdir("logs")
except:
    pass
try:
    f = open(logname, 'r')
except:
    f = open(logname, 'w')
    f.close()
finally:
    handler = logging.FileHandler(
        filename=logname,
        encoding='utf-8',
        mode='a')
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(relativeCreated)6d %(threadName)s\n%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


webhook_cd_pattern = r"<@[0-9]+>, command is on cooldown. Wait [0-9]+(.[0-9]+)? seconds"


COOLDOWNS = {
    "cache": 600,
    "day": 60*60*24,
    "hour": 60*60,
    "half-hour": 60*30
}

CHANNELS = {
    "guild_events": 549684642928656399
}

prefix_list = [
    "!"
]

badges_obj = {
    "staff": Image.open("cogs/stat/badges/staff.png").convert("RGBA"),
    "partner": Image.open("cogs/stat/badges/partner.png").convert("RGBA"),
    "hypesquad": Image.open("cogs/stat/badges/hypesquad.png").convert("RGBA"),
    "bug_hunter": Image.open("cogs/stat/badges/bug_hunter.png").convert("RGBA"),
    "nitro": Image.open("cogs/stat/badges/nitro.png").convert("RGBA"),
    "boost": Image.open("cogs/stat/badges/boost.png").convert("RGBA"),
    "early": Image.open("cogs/stat/badges/early.png").convert("RGBA"),
    "verified": Image.open("cogs/stat/badges/verified.png").convert("RGBA"),
    "youtube": Image.open("cogs/stat/badges/youtube.png").convert("RGBA"),
    "twitch": Image.open("cogs/stat/badges/twitch.png").convert("RGBA")
}

badges_list = [
    "staff",
    "partner",
    "hypesquad",
    "bug_hunter",
    "nitro",
    "boost",
    "early",
    "verified",
    "youtube",
    "twitch"
]

achievements_list = [
    "oldman",
    "lucker",
    "minami"
]

SHORT_LOCALES = {
    "en": "english",
    "ru": "russian",
    "ua": "ukrainian",
    "id": "indonesian",
    "ge": "german"
}

COLORS = {
    'error': 0x5714AD,
    'idk': 0xFAD6A5,
    'hidden': 0x36393F,
    'ban': 0xF10118,
    'unban': 0xF10118,
    'kick': 0xF10118
}

ERRORS = {
    "default": discord.Embed(
                        title="Unknown Exception",
                        description="I don't know what broken. Ask my developers, please ^_^",
                        color=COLORS["idk"]
                    ),
    "wh_forbidden": discord.Embed(
                        title="Webhook Forbidden",
                        description="Add access to manage webhooks, please ^_^",
                        color=COLORS["error"]
                    ),
    "send_forbidden": discord.Embed(
                        title="Message Forbidden",
                        description="Add access to send messages, please ^_^",
                        color=COLORS["error"]
                    ),
    "cm_not_available": discord.Embed(
                        title="Command Error",
                        description="That command isn't available for, sorry ^_^",
                        color=COLORS["error"]
                    ),
    "cm_bot_mentioned": discord.Embed(
                        title="Command Error",
                        description="Bots aren't your friends, sorry ^_^\nChoose someone else",
                        color=COLORS["error"]
                    ),
    "urban_not_found": discord.Embed(
                        title="Urban Dictionary",
                        description="Definitions didn't find, sorry ^_^\n",
                        color=COLORS["idk"]
                    ),
    "sql_bad_query": discord.Embed(
                        title="PostgreSQL",
                        description="Bad SQL query, :(",
                        color=COLORS["idk"]
                    ),
    "sql_no_response": discord.Embed(
                        title="PostgreSQL",
                        description="There's nothing to return",
                        color=COLORS["idk"]
                    ),
    "badges_cant_update": discord.Embed(
                        title="Set Badges",
                        description="I can't update them...",
                        color=COLORS["idk"]
                    ),
    "voice_cant_delete": discord.Embed(
                        title="Private Voices",
                        description="I can't delete voice {voice}.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "voice_cant_create": discord.Embed(
                        title="Private Voices",
                        description="I can't create a voice for you.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "voice_cant_move": discord.Embed(
                        title="Private Voices",
                        description="I can't move you in your voice.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "cant_update_user_roles": discord.Embed(
                        title="Roles",
                        description="I can't update roles for {who}.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "wh_cant_execute": discord.Embed(
                        title="Webhook",
                        description="I can't execute that webhook.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "createvoice_cant_create": discord.Embed(
                        title="Private Voices",
                        description="I can't create private voices for you.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "cant_fetch_message": discord.Embed(
                        title="Find Message",
                        description="I can't find that message here.. It's forbidden for me :(",
                        color=COLORS["error"]
                    ),
    "message_not_found": discord.Embed(
                        title="Find Message",
                        description="That message didn't find, sorry ^_^",
                        color=COLORS["idk"]
                    ),
    "role_isnt_in_list": discord.Embed(
                        title="Role",
                        description="That role isn't in list.. ^_^",
                        color=COLORS["idk"]
                    ),
    "clear_cant_delete": discord.Embed(
                        title="Clear Messages",
                        description="I can't delete messages here.. It's forbidden for me :(",
                        color=COLORS["error"]
                    )
}


lvlup_image_url = "https://discord.band/images/lvlup.png"


guilds_without_follow_us = [
    502913055559254036,
    433350258941100032,
    485400595235340303,
    455121989825331200,
    458947364137467906
]

guilds_without_more_info_in_help = [
    502913055559254036
]

COMMANDS_LIST = {
    "admin": [
                "say|say",
                "webhook|say",
                "clear|clear",
                "kick|kick",
                "ban|ban",
                "unban|ban",
                "gift|gift",
                "take|take"
              ],
    "economy": [
                "timely|timely",
                "work|work",
                "br|br",
                # "slots|-",
                "give|give",
                "shop|shop"
               ],
    "fun": [
                "kiss|kiss",
                "hug|hug",
                "punch|punch",
                "highfive|five",
                "wink|wink",
                "fuck|fuck",
                "drink|drink",
                "bite|bite",
                "lick|lick",
                "pat|pat",
                "slap|slap",
                "poke|poke"
            ],
    "stats": [
                "$|cash",
                "top|top",
                "money|top",
                "voice|top",
                "me|me"
             ],
    "other": [
                "help|-",
                "ping|ping",
                "avatar|avatar",
                "roll|roll",
                "server|server",
                "invite|invite",
                "about|about",
                "when|when",
                "urban|ud"
             ]
}

ACTIVITIES = {
    "hug": {
        "tenor": "hug",
        "cmd": "hug"
    },
    "kiss": {
        "tenor": "kiss",
        "cmd": "kiss"
    },
    "wink": {
        "tenor": "wink",
        "cmd": "wink"
    },
    "punch": {
        "tenor": "punch",
        "cmd": "punch"
    },
    "drink": {
        "tenor": "drink",
        "cmd": "drink"
    },
    "five": {
        "tenor": "high-five",
        "cmd": "five"
    },
    "high-five": {
        "tenor": "high-five",
        "cmd": "five"
    },
    "fuck": {
        "tenor": "fuck you",
        "cmd": "fuck"
    },
    "bite": {
        "tenor": "bite",
        "cmd": "bite"
    },
    "lick": {
        "tenor": "lick",
        "cmd": "lick"
    },
    "pat": {
        "tenor": "pat",
        "cmd": "pat"
    },
    "slap": {
        "tenor": "slap",
        "cmd": "slap"
    },
    "poke": {
        "tenor": "poke",
        "cmd": "poke"
    }
}


WORK_TYPES = {
    "default": {
        "exp": 1,
        "chance": 100
    },
    "worker": {
        "exp": 1.1,
        "chance": 80
    },
    "student": {
        "exp": 0.3,
        "chance": 30
    },
    "freelance": {
        "exp": 0.5,
        "chance": 50
    },
    "developer": {
        "exp": 2,
        "chance": 20
    }
}


tomori_links = '\
[Vote](https://discordbots.org/bot/491605739635212298/vote "for Tomori") \
[Donate](https://discord.band/donate "Donate") \
[YouTube](https://www.youtube.com/channel/UCxqg3WZws6KxftnC-MdrIpw "Tomori Project\'s channel") \
[Telegram](https://t.me/TomoriDiscord "Our telegram channel") \
[Website](https://discord.band "Our website") \
[VK](https://vk.com/tomori_discord "Our group on vk.com")'



cached_voice_joins = {}





mask_welcome = Image.new('L', (1002, 1002), 0)
draws = ImageDraw.Draw(mask_welcome)
draws.ellipse((471, 5) + (531, 35), fill=255)
draws.ellipse((471, 967) + (531, 997), fill=255)
draws.ellipse((5, 471) + (35, 531), fill=255)
draws.ellipse((967, 471) + (997, 531), fill=255)
draws.polygon([(531, 15), (471, 15), (15, 471), (15, 531), (471, 987), (531, 987), (987, 531), (987, 471)], fill=255)
mask_welcome = mask_welcome.resize((343, 343), Image.ANTIALIAS)
