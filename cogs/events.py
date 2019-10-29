import sys
import asyncio, aiohttp, logging, time, string, random, copy, json, asyncpg, requests, re
from aiohttp import ClientSession
from datetime import datetime, date

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

import time
from datetime import datetime, date, timedelta

from PIL import Image, ImageChops, ImageFont, ImageDraw, ImageSequence, ImageFilter, GifImagePlugin
from PIL.GifImagePlugin import getheader, getdata
from functools import partial
from io import BytesIO, BufferedIOBase

from cogs.util import *
from cogs.const import *
from cogs.classes import *
from config.settings import settings



class Events(commands.Cog):


    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.get_cached_guild(guild)
        channel = self.bot.get_channel(CHANNELS["guild_events"])
        em = discord.Embed(color=COLORS["hidden"])
        em.title = "🔵 New guild join"
        em.add_field(
            name="Members",
            value=str(guild.member_count),
            inline=True
        )
        em.set_footer(
            text=tagged_name_id(guild.owner),
            icon_url=str(guild.owner.avatar_url)
        )
        kwargs = {
            "username": tagged_gname(guild),
            "avatar_url": str(guild.icon_url),
            "nitro": True
        }
        await self.bot.true_send(channel=channel, embed=em, **kwargs)


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        channel = self.bot.get_channel(CHANNELS["guild_events"])
        em = discord.Embed(color=COLORS["hidden"])
        em.title = "🔴 Guild removed"
        em.add_field(
            name="Members",
            value=str(guild.member_count),
            inline=True
        )
        em.set_footer(
            text=tagged_name_id(guild.owner),
            icon_url=str(guild.owner.avatar_url)
        )
        kwargs = {
            "username": tagged_gname(guild),
            "avatar_url": str(guild.icon_url),
            "nitro": True
        }
        await self.bot.true_send(channel=channel, embed=em, **kwargs)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        bot = self.bot
        guild = member.guild
        data = await bot.get_cached_guild(guild)


        roles = []
        reason = None
        # Выдача сохраненных ролей
        if data["is_save_roles_on_leave"]:
            roles_data = await bot.db.select("*", "mods", where={
                "type": "saved_roles",
                "name": str(member.id),
                "guild_id": guild.id
            })
            if roles_data:
                for role_id in roles_data["arguments"]:
                    role = guild.get_role(int(role_id))
                    if role and not (role.is_default() or role.managed):
                        roles.append(role)
                        reason = "Roles backup"
        # Выдача автороли
        if data["autorole"]:
            role = guild.get_role(data["autorole"])
            if role and not (role.is_default() or role.managed):
                roles.append(role)
                if reason:
                    reason = f"{reason} | Autorole"
                else:
                    reason = "Autorole"
        # Конкретно выдача всех ролей, которые собрали выше
        # данному юзеру (если он есть)
        if roles:
            try:
                await member.add_roles(*roles, reason=reason)
            except discord.Forbidden:
                logger.info(f"on_member_join->add_roles: Forbidden to add roles - {guild.name} [{guild.id}]")
            except Exception as e:
                logger.info(f"on_member_join->add_roles: Unknown exception ({e}) - {guild.name} [{guild.id}]")

        # Welcomer
        if data["welcome_channel"]:
            channel = bot.get_channel(data["welcome_channel"])
            if channel:

                content = None
                if data["welcome_text"]:
                    content = welcomer_format(member, data)

                async with channel.typing():
                    try:
                        color = json.loads(data["welcome_text_color"])
                        color = (color[0], color[1], color[2])
                    except:
                        color = (0, 0, 0)

                    back = Image.open("cogs/stat/backgrounds/welcome/{}.png".format(data["welcome_back"]))
                    draw = ImageDraw.Draw(back)
                    under = Image.open("cogs/stat/backgrounds/welcome/under_{}.png".format(data["welcome_under"]))

                    text_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", 50)
                    text_name = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", 50)

                    text_welcome = u"{}".format("WELCOME")
                    welcome_size = 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)
                    while font_name.getsize(text_welcome)[0] < 500:
                        welcome_size += 1
                        font_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)
                        if welcome_size == 71:
                            break
                    welcome_size -= 1
                    font_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)

                    text_name = u"{}".format(tagged_name(member))
                    name_size = 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)
                    while font_name.getsize(text_name)[0] < 500:
                        name_size += 1
                        font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)
                        if name_size == 36:
                            break
                    name_size -= 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)

                    ava_url = str(member.avatar_url)
                    response = requests.get(ava_url)
                    avatar = Image.open(BytesIO(response.content))
                    avatar = avatar.resize((343, 343)).convert("RGB")
                    avatar.putalpha(mask_welcome)
                    back.paste(under, (0, 0), under)
                    back.paste(avatar, (29, 29), avatar)


                    kernel = [
                        0, 1, 2, 1, 0,
                        1, 2, 4, 2, 1,
                        2, 4, 8, 4, 1,
                        1, 2, 4, 2, 1,
                        0, 1, 2, 1, 0
                    ]
                    kernelsum = sum(kernel)
                    myfilter = ImageFilter.Kernel((5, 5), kernel, scale = 0.3 * kernelsum)
                    halo = Image.new('RGBA', back.size, (0, 0, 0, 0))
                    if data["welcome_is_text"]:
                        ImageDraw.Draw(halo).text(
                            (435, 120),
                            text_welcome,
                            (0, 0, 0),
                            font=font_welcome
                        )
                        ImageDraw.Draw(halo).text(
                            (435, 230),
                            text_name,
                            (0, 0, 0),
                            font=font_name
                        )
                    blurred_halo = halo.filter(myfilter)
                    if data["welcome_is_text"]:
                        ImageDraw.Draw(blurred_halo).text(
                            (435, 120),
                            text_welcome,
                            color,
                            font=font_welcome
                        )
                        ImageDraw.Draw(blurred_halo).text(
                            (435, 230),
                            text_name,
                            color,
                            font=font_name
                        )
                    back = Image.composite(back, blurred_halo, ImageChops.invert(blurred_halo))
                    draw = ImageDraw.Draw(back)

                    fp = BytesIO()
                    back.save(fp, "PNG")
                    fp.seek(0)
                    await bot.true_send(
                        channel=channel,
                        content=content,
                        file=discord.File(fp, f"welcome_{member.id}.png"),
                        nitro=data["is_nitro"],
                        username=data["nitro_name"] if data["nitro_name"] else None,
                        avatar_url=data["nitro_avatar"] if data["nitro_avatar"] else None
                    )
                    return


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        bot = self.bot
        guild = member.guild
        data = await bot.get_cached_guild(guild)

        # Сохранение ролей
        if data["is_save_roles_on_leave"]:
            roles = []
            for role in member.roles:
                if not (role.is_default() or role.managed):
                    roles.append(str(role.id))
            await bot.db.insert_update({
                "type": "saved_roles",
                "name": str(member.id),
                "guild_id": guild.id,
                "arguments": roles
            }, "mods", constraint="uniq_type")

        # Welcomer
        if data["welcome_channel"]:
            channel = bot.get_channel(data["welcome_channel"])
            if channel:

                content = None
                if data["welcome_leave_text"]:
                    content = welcomer_format(member, data, text=data["welcome_leave_text"])

                async with channel.typing():
                    try:
                        color = json.loads(data["welcome_text_color"])
                        color = (color[0], color[1], color[2])
                    except:
                        color = (0, 0, 0)

                    back = Image.open("cogs/stat/backgrounds/welcome/{}.png".format(data["welcome_back"]))
                    draw = ImageDraw.Draw(back)
                    under = Image.open("cogs/stat/backgrounds/welcome/under_{}.png".format(data["welcome_under"]))

                    text_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", 50)
                    text_name = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", 50)

                    text_welcome = u"{}".format("GOODBYE")
                    welcome_size = 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)
                    while font_name.getsize(text_welcome)[0] < 500:
                        welcome_size += 1
                        font_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)
                        if welcome_size == 71:
                            break
                    welcome_size -= 1
                    font_welcome = ImageFont.truetype("cogs/stat/ProximaNova-Bold.otf", welcome_size)

                    text_name = u"{}".format(tagged_name(member))
                    name_size = 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)
                    while font_name.getsize(text_name)[0] < 500:
                        name_size += 1
                        font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)
                        if name_size == 36:
                            break
                    name_size -= 1
                    font_name = ImageFont.truetype("cogs/stat/ProximaNova-Regular.ttf", name_size)

                    ava_url = str(member.avatar_url)
                    response = requests.get(ava_url)
                    avatar = Image.open(BytesIO(response.content))
                    avatar = avatar.resize((343, 343)).convert("RGB")
                    avatar.putalpha(mask_welcome)
                    back.paste(under, (0, 0), under)
                    back.paste(avatar, (29, 29), avatar)


                    kernel = [
                        0, 1, 2, 1, 0,
                        1, 2, 4, 2, 1,
                        2, 4, 8, 4, 1,
                        1, 2, 4, 2, 1,
                        0, 1, 2, 1, 0
                    ]
                    kernelsum = sum(kernel)
                    myfilter = ImageFilter.Kernel((5, 5), kernel, scale = 0.3 * kernelsum)
                    halo = Image.new('RGBA', back.size, (0, 0, 0, 0))
                    if data["welcome_is_text"]:
                        ImageDraw.Draw(halo).text(
                            (435, 120),
                            text_welcome,
                            (0, 0, 0),
                            font=font_welcome
                        )
                        ImageDraw.Draw(halo).text(
                            (435, 230),
                            text_name,
                            (0, 0, 0),
                            font=font_name
                        )
                    blurred_halo = halo.filter(myfilter)
                    if data["welcome_is_text"]:
                        ImageDraw.Draw(blurred_halo).text(
                            (435, 120),
                            text_welcome,
                            color,
                            font=font_welcome
                        )
                        ImageDraw.Draw(blurred_halo).text(
                            (435, 230),
                            text_name,
                            color,
                            font=font_name
                        )
                    back = Image.composite(back, blurred_halo, ImageChops.invert(blurred_halo))
                    draw = ImageDraw.Draw(back)

                    fp = BytesIO()
                    back.save(fp, "PNG")
                    fp.seek(0)
                    await bot.true_send(
                        channel=channel,
                        content=content,
                        file=discord.File(fp, f"welcome_{member.id}.png"),
                        nitro=data["is_nitro"],
                        username=data["nitro_name"] if data["nitro_name"] else None,
                        avatar_url=data["nitro_avatar"] if data["nitro_avatar"] else None
                    )


    async def check_empty_voice(self, member, channel, data):
        if not (channel.category and channel.category_id == data["create_voice_category"] and channel.id != data["create_voice_id"] and len(channel.members) == 0):
            return
        try:
            await channel.delete(reason="Tomori Private Voices")
        except discord.Forbidden:
            await self.bot.channel_send_error(channel=member, error="voice_cant_delete", voice=channel.name)
        except Exception as e:
            logger.info(f"check_empty_voice: Unknown exception ({e})")


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        bot = self.bot
        guild = member.guild
        data = await bot.get_cached_guild(guild)

        if member.bot:
            if before.channel:
                await self.check_empty_voice(member, before.channel, data)
            return


        if before.channel:
            await self.check_empty_voice(member, before.channel, data)
            # Прибавить время за выход из войса тогда, когда юзер вышел и не ушел в другой войс
            if not after.channel:
                cache_id = f"{guild.id}-{member.id}"
                join_time = cached_voice_joins.pop(cache_id, 0)
                if join_time > 0:
                    voice_time = unix_time() - join_time
                    user_data = await bot.db.insert_update({
                        "name": member.name,
                        "id": member.id,
                        "guild": guild.id,
                        "discriminator": member.discriminator,
                        "voice_seconds": {voice_time: "+"}
                    }, "users", constraint="unic_profile")
                    n_v = int(user_data["voice_seconds"] / data["voice_seconds_to_award"])
                    l_v = int((user_data["voice_seconds"] - voice_time) / data["voice_seconds_to_award"])
                    diff = n_v - l_v
                    if diff > 0:
                        money = diff * data["voice_award_money"]
                        xp = diff * data["voice_award_xp"]
                        if money > 0 or xp > 0:
                            user_data = await bot.db.update({
                                "cash": {money: "+"},
                                "xp": {xp: "+"},
                            }, "users", where={"id": member.id, "guild": guild.id})
                            try:
                                other = self.bot.get_cog('Other')
                                await other.check_lvlup(member, user_data["xp"]-xp, user_data["xp"], data=data)
                            except Exception as e:
                                logger.info(f"on_voice_state_update->other.check_lvlup: Unknown exception ({e}) - {guild.name} [{guild.id}]")


        if after.channel:
            if not before.channel:
                cache_id = f"{guild.id}-{member.id}"
                cached_voice_joins[cache_id] = unix_time()
            # Создание приватки
            if after.channel.category and after.channel.category_id == data["create_voice_category"] and after.channel.id == data["create_voice_id"]:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite.from_pair(
                        discord.Permissions(permissions=data["create_voice_everyone_permissions"]),
                        discord.Permissions(permissions=0)
                    ),
                    member: discord.PermissionOverwrite.from_pair(
                        discord.Permissions(permissions=data["create_voice_owner_permissions"]),
                        discord.Permissions(permissions=0)
                    )
                }
                try:
                    private_channel = await guild.create_voice_channel(
                        name=member.name,
                        category=after.channel.category,
                        overwrites=overwrites,
                        user_limit=data["create_voice_user_limit"],
                        reason="Tomori Private Voices"
                    )
                except discord.Forbidden:
                    await self.bot.channel_send_error(channel=member, error="voice_cant_create")
                    return
                except Exception as e:
                    logger.info(f"on_voice_state_update->create_voice_channel: Unknown exception ({e}) - {guild.name} [{guild.id}]")
                    return
                try:
                    await member.edit(
                        voice_channel=private_channel,
                        reason="Tomori Private Voices"
                    )
                except discord.Forbidden:
                    await self.bot.channel_send_error(channel=member, error="voice_cant_move")
                    await self.check_empty_voice(member, private_channel, data)
                except Exception as e:
                    logger.info(f"on_voice_state_update->member.edit: Unknown exception ({e}) - {guild.name} [{guild.id}] | {member.name} [{member.id}]")
                    await self.check_empty_voice(member, private_channel, data)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        bot = self.bot
        emoji = str(payload.emoji).replace("<a:", "<:")
        message_id = payload.message_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        guild = bot.get_guild(guild_id)
        if not guild: return
        user = guild.get_member(user_id)
        if not user: return

        data = await bot.db.select_all("*", "mods", where={"guild_id": message_id, "type": "reaction"})
        roles = []
        is_unique = any(row["condition"] == 'unique' for row in data)
        for role in user.roles:
            is_in_data = any((row["arguments"] and str(role.id) in row["arguments"]) for row in data)
            if is_unique and is_in_data:
                continue
            roles.append(role)
        is_new_role = False
        random_roles = []
        is_random = False
        for row in data:
            if not row["name"] == emoji or not row["arguments"]:
                continue
            is_random = True if row["condition"] == "random" else False
            for role_id in row["arguments"]:
                try:
                    role = guild.get_role(int(role_id))
                    if role and not (role in roles or role in random_roles):
                        is_new_role = True
                        if is_random:
                            random_roles.append(role)
                        else:
                            roles.append(role)
                except:
                    pass
        if is_random:
            roles.append(random.choice(random_roles))
        if is_new_role:
            try:
                await user.edit(roles=roles, reason="Tomori Custom Reaction Add")
            except discord.Forbidden:
                await self.bot.channel_send_error(channel=member, error="cant_update_user_roles", who=member.mention)
            except Exception as e:
                logger.info(f"on_reaction_add: Unknown exception ({e}) - {guild.name} [{guild.id}] Roles: {', '.join(roles)}")


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        bot = self.bot
        emoji = str(payload.emoji).replace("<a:", "<:")
        message_id = payload.message_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        guild = bot.get_guild(guild_id)
        if not guild: return
        user = guild.get_member(user_id)
        if not user: return

        data = await bot.db.select("*", "mods", where={"guild_id": message_id, "type": "reaction", "name": emoji})
        roles = user.roles
        if data and data["arguments"]:
            for role_id in data["arguments"]:
                try:
                    role = guild.get_role(int(role_id))
                    if role and role in roles:
                        roles.pop(roles.index(role))
                except:
                    pass
        if roles != user.roles:
            try:
                await user.edit(roles=roles, reason="Tomori Custom Reaction Remove")
            except discord.Forbidden:
                await self.bot.channel_send_error(channel=member, error="cant_update_user_roles", who=member.mention)
            except Exception as e:
                logger.info(f"on_reaction_remove: Unknown exception ({e}) - {guild.name} [{guild.id}] Roles: {', '.join(roles)}")




def setup(bot):
    bot.add_cog(Events(bot))
