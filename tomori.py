import sys
import asyncio, aiohttp, logging, time, string, random, copy, json, asyncpg
import re
from aiohttp import ClientSession
from datetime import datetime, date

from aiocache import cached, Cache

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

import time
from datetime import datetime, date, timedelta

import threading

import tenorpy

from cogs.util import *
from cogs.const import *
from cogs.classes import *
from config.settings import settings



__name__ = "Tomori"
__author__ = "Pineapple Cookie"
__version__ = "5.3.2 Go"

SHARD_COUNT = 4


class Tomori(commands.AutoShardedBot):


    def __init__(self, **kwargs):
        super().__init__(
            command_prefix="!",
            case_insensitive=True,
            shard_count=SHARD_COUNT,
            cache_auth=False,
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name="trying to launch (^_^)"
            )
        )

        self.db = PostgresqlDatabase(dsn=f'postgres://{settings["base_user"]}:{settings["base_password"]}@localhost:5432/anime')
        self.odb = PostgresqlDatabase(dsn=f'postgres://{settings["base_user"]}:{settings["base_password"]}@localhost:5432/tomori')
        self.launch_time = datetime.utcnow()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.t_name = __name__
        self.t_version = __version__
        self.tenor = tenorpy.Tenor()
        self.commands_activity = {}
        self.cache = {
            "guilds": Cache(namespace="guilds"),
            "badges": Cache(namespace="badges"),
            "tenor": Cache(namespace="tenor")
        }


    async def _init_database(self):
        await self.db.connect()
        self._locale = await self._init_locale()


    async def _init_locale(self):
        locale = {}
        columnNames = await self.db.select_all("column_name", "information_schema.columns", where={"table_name": "locale"})
        columns = ""
        for column in columnNames:
            columns += "{}, ".format(column[0])
        fromBase = await self.db.select_all(columns[:-2], "locale")
        _locales = columnNames
        for name, *columns in fromBase:
            for index, column in enumerate(columns):
                if not columnNames[index+1][0] in locale.keys():
                    locale[columnNames[index+1][0]] = {}
                locale[columnNames[index+1][0]].setdefault(name, column)
        return locale


    def get_locale(self, lang, key):
        lang = lang.lower()
        key = key.lower()
        text = self._locale.get(lang, {key: "Error! Language not found"}).get(key)
        if not text:
            text = self._locale.get("english", {key: "Error! Language not found"}).get(key)
        return text

    @cached(ttl=60, namespace="guilds")
    async def get_cached_guild(self, guild):
        dat = await self.db.update({"icon_url": str(guild.icon_url)}, "guilds", where={"id": guild.id})
        if not dat:
            lang = "english"
            if guild.region == discord.VoiceRegion.russia:
                lang = "russian"
            dat = await self.db.insert({
                "id": guild.id,
                "name": guild.name,
                "icon_url": str(guild.icon_url),
                "locale": lang
            }, "guilds")
        return dat

    @cached(ttl=60, namespace="badges")
    async def get_badges(self, user):
        if isinstance(user, int):
            id = user
        elif isinstance(user, str):
            id = int(user)
        else:
            id = user.id
        badges = await self.db.select("arguments", "mods", where={"type": "badges", "name":str(id)})
        if badges:
            badges = badges["arguments"]
        else:
            badges = []
        badges = Badges(badges)
        return badges

    async def check_any_badges(self, user, _badges):
        badges = await self.get_badges(user)
        badges = badges.get_badges()
        if isinstance(_badges, list):
            for badge in _badges:
                if badge.lower() in badges:
                    return True
            return False
        else:
            return True if str(_badges).lower() in badges else False

    async def check_badges(self, user, _badges):
        badges = await self.get_badges(user)
        badges = badges.get_badges()
        if isinstance(_badges, list):
            for badge in _badges:
                if not badge.lower() in badges:
                    return False
            return True
        else:
            return True if str(_badges).lower() in badges else False

    @cached(ttl=300, namespace="tenor")
    async def get_tenor_list(self, name: str):
        return self.tenor.randomlist(name)

    async def get_tenor_gif(self, name: str):
        gifs = await self.get_tenor_list(name)
        return random.choice(gifs)


    async def add_follow_links(self, ctx, embed):
        embed.add_field(
            name=self.get_locale(ctx.lang, "global_follow_us"),
            value=tomori_links,
            inline=False
        )
        return embed


    async def statuses(self):
        while not self.is_closed():

            guilds_count = len(self.guilds)
            users_count = 0
            try:
                for guild in self.guilds:
                    users_count += guild.member_count
            except:
                pass

            def _beauty(count):
                if int(count/1000000) > 0:
                    count = str(int(count/1000000))+"M"
                elif int(count/1000) > 0:
                    count = str(int(count/1000))+"K"
                return count

            users_count = _beauty(users_count)
            guilds_count = guilds_count
            await self.change_presence(activity=discord.Streaming(name=f"Servers: {guilds_count} | Users: {users_count} | Shards: {self.shard_count}", url="https://www.twitch.tv/tomori_bot"))

            await asyncio.sleep(600)


    async def reset_badges(self):
        while not self.is_closed():
            data = await self.db.fetch(f"SELECT * FROM mods WHERE type='reset_badges' AND condition::bigint < {unix_time()} AND condition::bigint > 10")
            for row in data:
                remove_badges = Badges(row["arguments"])
                user_id = int(row["name"])
                badges = await self.get_badges(user_id)
                badges = badges.get_badges()
                new_badges = []
                for badge in badges:
                    if not badge in remove_badges.get_badges():
                        new_badges.append(badge)
                tasks = []
                if new_badges:
                    tasks.append(self.db.update({"arguments": new_badges}, "mods", where={"id": row["id"]}))
                else:
                    tasks.append(self.db.execute(f"DELETE FROM mods WHERE type = 'badges' and name = '{user_id}'"))
                tasks.append(self.db.execute(f"DELETE FROM mods WHERE id = {row['id']}"))
                await asyncio.wait(tasks)
            await self.cache["badges"].clear()

            data = await self.db.fetch(f"SELECT * FROM mods WHERE type='reset_guild_badges' AND condition::bigint < {unix_time()} AND condition::bigint > 10")
            for row in data:
                guild_id = row["guild_id"]
                rm_args = {}
                for arg in row["arguments"]:
                    rm_args[f"is_{arg.lower()}"] = False
                tasks = []
                if rm_args:
                    tasks.append(self.db.update(rm_args, "guilds", where={"id": guild_id}))
                tasks.append(self.db.execute(f"DELETE FROM mods WHERE id = {row['id']}"))
                await asyncio.wait(tasks)

            await asyncio.sleep(COOLDOWNS["hour"])


    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print("Started in "+str(datetime.utcnow() - self.launch_time))
        print('------')
        self.loop.create_task(self.statuses())
        self.loop.create_task(self.reset_badges())
        # self.loop.create_task(mutting())
        # self.loop.create_task(spaming())


    async def on_command_error(self, ctx, error):
        ctx = await context_init(ctx)
        if not ctx: return
        if isinstance(error, commands.CommandOnCooldown):
            await self.true_send(ctx=ctx, content="{who}, command is on cooldown. Wait {seconds} seconds".format(
                    who=ctx.author.mention,
                    seconds=round(error.retry_after, 2)
                ),
                delete_after=5
            )
        elif isinstance(error, commands.BadArgument):
            await self.true_send_error(ctx=ctx, channel=ctx.channel, error="incorrect_argument", arg=error.args[0])
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.true_send_error(ctx=ctx, channel=ctx.channel, error="missed_argument", arg=error.param.name)


    def add_command_activity(self, name):
        name = name.lower()
        count = self.commands_activity.get(name, 0)
        self.commands_activity[name] = count + 1


    async def on_command(self, ctx):
        self.add_command_activity(ctx.invoked_with)


    async def on_command_completion(self, ctx):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.info(f"on_command: Unknown exception ({e}) - {ctx.channel.guild.name} [{ctx.channel.guild.id}]")


    async def handle_command(self, message):
        const = await self.get_cached_guild(message.guild)
        await self.db.pool.execute(f"""INSERT INTO users(
            id,
            guild,
            discriminator,
            xp,
            last_xp,
            messages,
            cash,
            name,
            avatar_url
        ) VALUES(
            {message.author.id},
            {message.guild.id},
            '{message.author.discriminator}',
            {const['xp_award']},
            {unix_time()},
            1,
            {const['message_award']},
            E'{self.db.clear(message.author.name)}',
            E'{self.db.clear(str(message.author.avatar_url_as(static_format='png')))}'
        ) ON CONFLICT ON CONSTRAINT unic_profile DO UPDATE SET
            discriminator='{message.author.discriminator}',
            avatar_url=E'{self.db.clear(str(message.author.avatar_url_as(format='png')))}',
            xp=users.xp+{const['xp_award']},
            last_xp={unix_time()},
            messages=users.messages + 1,
            cash=users.cash+{const['message_award']}
        WHERE
            users.id={message.author.id} AND
            users.guild={message.guild.id} AND
            users.last_xp<={unix_time()}-{const['xp_cd']};""")
        if message.content.startswith(const["prefix"]) or message.content.lower() == "!help":
            message.content = message.content.replace(const["prefix"], "!", 1)
            await self.process_commands(message)


    async def on_message(self, message):
        if message.author.discriminator == "0000":
            if message.content:
                if re.match(webhook_cd_pattern, message.content):
                    await asyncio.sleep(5)
                    await message.delete()
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        await self.handle_command(message)


    async def true_send(self, *args, **kwargs):
        try:
            channel = kwargs.pop("channel")
        except:
            channel = None
        try:
            ctx = kwargs.pop("ctx")
        except:
            ctx = None
        if not channel and ctx:
            channel = ctx.channel
        assert channel, "true_send: Channel is null"
        try:
            nitro = kwargs.pop("nitro")
        except:
            nitro = None
        error = kwargs.pop("error", None)
        msg = None

        if (nitro or (ctx and ctx.is_nitro)) and not (isinstance(channel, discord.User) or isinstance(channel, discord.Member)):
            try:
                webhooks = await channel.webhooks()
                if not webhooks:
                    webhooks = [await channel.create_webhook(
                        name='Tomori Nitro Webhook',
                        avatar=await self.user.avatar_url_as(format="png").read()
                    )]

                name = self.user.display_name
                url = str(self.user.avatar_url_as(format="png", size=512))

                if ctx:
                    const = ctx.const
                    if const["nitro_name"]:
                        name = const["nitro_name"]
                    if const["nitro_avatar"]:
                        url = const["nitro_avatar"]

                if not kwargs.get("username", None):
                    kwargs["username"] = name
                if not kwargs.get("avatar_url", None):
                    kwargs["avatar_url"] = url

                new_kwargs = {}
                keys = [
                    "content",
                    "tts",
                    "embed",
                    "embeds",
                    "file",
                    "files",
                    "nonce",
                    "username",
                    "avatar_url"
                ]
                for key in keys:
                    if kwargs.get(key, None) != None:
                        new_kwargs[key] = kwargs.get(key)
                msg = await webhooks[0].send(**new_kwargs)
                return
            except discord.Forbidden:
                if error != False:
                    logger.info(f"true_send: Tomori Nitro doesnt allow by server owner - {ctx.channel.guild.name} [{ctx.channel.guild.id}]")
                    msg = await self.true_send_error(ctx=ctx, error="wh_forbidden")
                else:
                    raise e
            except Exception as e:
                if error != False:
                    logger.info(f"true_send: Unknown exception at webhooks ({e}) - {ctx.channel.guild.name} [{ctx.channel.guild.id}]")
                    msg = await self.true_send_error(ctx=ctx)
                else:
                    raise e
                return

        try:
            new_kwargs = {}
            keys = [
                "content",
                "tts",
                "embed",
                "file",
                "files",
                "nonce",
                "delete_after"
            ]
            for key in keys:
                if kwargs.get(key, None) != None:
                    new_kwargs[key] = kwargs.get(key)
            msg = await channel.send(**new_kwargs)
        except discord.Forbidden:
            pass
            #
            #  TODO Тут идет игнор команд в чатах, где бот видит сообщения, а отвечать не может (Это фича)
            #
            # await self.true_send_error(ctx=ctx, error="send_forbidden")
            # print(f"true_send: Tomori Nitro doesnt allow by server owner - {channel.guild.name} [{channel.guild.id}]")
        except Exception as e:
            if error != False:
                logger.info(f"true_send: Unknown exception ({e}) - {channel.guild.name} [{channel.guild.id}]")
                msg = await self.true_send_error(ctx=ctx)
            else:
                raise e
        return msg



    async def true_send_error(self, *args, **kwargs):
        ctx = kwargs.pop("ctx")
        assert ctx, "true_send_error: Context is null"
        try:
            author = ctx.author
        except Exception as e:
            logger.info(f"true_send_error: Unknown exception at get author ({e})")
        assert author, "true_send_error: Author is null"

        def format_error(text):
            return text.format(
                user=kwargs.get("user", ctx.author.mention),
                who=kwargs.get("who", ctx.author.mention),
                author=kwargs.get("who", ctx.author.mention),
                bot=kwargs.get("bot", self.user.mention),
                guild=kwargs.get("guild", ctx.guild.name),
                name=kwargs.get("name", ""),
                arg=kwargs.get("arg", ""),
                emoji=ctx.const["emoji"],
                voice=kwargs.get("voice", ""),
                number=kwargs.get("number", ""),
                role=kwargs.get("role", "")
            )

        code = kwargs.get("error", "default")
        embed = copy.deepcopy(ERRORS.get(code, None))
        if not embed:
            error_text = self._locale.get(ctx.lang, {code: "Error! Language not found"}).get(code, None)
            if error_text:
                embed = discord.Embed(
                                        title="Tomori Exception",
                                        description=error_text,
                                        color=COLORS["error"]
                                    )
            else:
                embed = ERRORS.get("default")
        embed.title = format_error(embed.title)
        embed.description = format_error(embed.description)
        channel = kwargs.get("channel", author)
        return await channel.send(embed=embed, delete_after=60)

    async def channel_send_error(self, *args, **kwargs):
        channel = kwargs.pop("channel")
        assert channel, "true_send_error: Channel is null"

        def format_error(text):
            return text.format(
                user=kwargs.get("user", ""),
                who=kwargs.get("who", ""),
                author=kwargs.get("who", ""),
                bot=kwargs.get("bot", ""),
                guild=kwargs.get("guild", ""),
                name=kwargs.get("name", ""),
                arg=kwargs.get("arg", ""),
                emoji=kwargs.get("emoji", ""),
                voice=kwargs.get("voice", ""),
                number=kwargs.get("number", ""),
                role=kwargs.get("role", "")
            )

        code = kwargs.get("error", "default")
        lang = kwargs.get("lang", "english")
        embed = copy.deepcopy(ERRORS.get(code, None))
        if not embed:
            error_text = self._locale.get(lang, {code: "Error! Language not found"}).get(code, None)
            if error_text:
                embed = discord.Embed(
                                        title="Tomori Exception",
                                        description=error_text,
                                        color=COLORS["error"]
                                    )
            else:
                embed = ERRORS.get("default")
        embed.title = format_error(embed.title)
        embed.description = format_error(embed.description)
        return await channel.send(embed=embed, delete_after=60)


    def run(self, token):
        self.loop.run_until_complete(self._init_database())
        self.remove_command("help")
        for extension in settings["extensions"]:
            try:
                self.load_extension(extension)
            except Exception as e:
                logger.info(f"[x] Can't load Cog because: {e}")
        # quart_app.client = self
        # self.quart_thread = threading.Thread(target=quart_app.run, args=["54.37.18.227", 8080], kwargs={
        #     "debug": False,
        #     "use_reloader": True
        # })
        # self.quart_thread.start()
        super().run(token)


tomori = Tomori()
tomori.run(settings["token"])
