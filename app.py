import asyncio
import configparser
import json
import re
from datetime import datetime
from io import BytesIO
from os import environ
import logging

import discord
import praw
import requests
import wikia
from PIL import Image, ImageFont, ImageDraw
from prawcore import PrawcoreException
from wit import Wit
import fa

bot = discord.Client()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)

config = configparser.ConfigParser()
config.read("config.ini")
discord_game = config.get("discord", "game")
wikia_wiki = config.get("wikia", "wiki")
spoilers_channel = config.get("spoilers", "channel")
spoilers_keywords = config.get("spoilers", "keywords").split(",")
countdown_enabled = config.get("countdown", "enabled")
fa_quickview_enabled = config.get("FA QuickView", "enabled")
fa_quickview_thumbnail = config.get("FA QuickView", "thumbnail")

wit = Wit(access_token=environ.get("WIT_TOKEN"))
reddit = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                     client_secret=environ.get("REDDIT_SECRET"),
                     user_agent=environ.get("REDDIT_USER_AGENT"))


async def update_countdown():
    if countdown_enabled.lower() == "true":
        date = config.get("countdown", "date")
        icon = config.get("countdown", "icon")
        font = config.get("countdown", "font")
        size = int(config.get("countdown", "size"))
        r, g, b = [int(x) for x in config.get("countdown", "color").split(",")]
        suffix = config.get("countdown", "suffix")
        prefix = config.get("countdown", "prefix")
        today = datetime.utcnow().date()
        end_day = datetime.strptime(date, "%Y-%m-%d").date()
        diff = end_day - today
        text = str(diff.days)
        img = Image.open(icon)
        iw, ih = img.size

        draw = ImageDraw.Draw(img)
        large_font = ImageFont.truetype(font, size)
        small_font = ImageFont.truetype(font, int(.500 * size))
        pw, ph = small_font.getsize(prefix)
        tw, th = large_font.getsize(text)
        sw, sh = small_font.getsize(suffix)
        x, y = (iw - (pw + tw + sw)) / 2, (ih - th - 15) / 2
        draw.text((x - tw, y + int(.5 * th)), prefix, (r, g, b), font=small_font)
        draw.text((x, y), text, (r, g, b), font=large_font)
        draw.text((x + tw, y + int(.5 * th)), suffix, (r, g, b), font=small_font)

        with BytesIO() as data:
            img.save(data, format="PNG")
            for server in bot.servers:
                try:
                    await bot.edit_server(server, icon=data.getvalue())
                    log.info("{}: Set icon to {} days!".format(server.name, text))
                except discord.Forbidden:
                    log.warning("{}: Failed to set icon. Permission 'Manage Server' is required!".format(server.name))


async def send_message(destination, content=None, *, embed=None, expire_time=0):
    if content is None and embed is None:
        log.error("A message needs to have content!")
        return None
    msg = None
    try:
        msg = await bot.send_message(destination, content, embed=embed)

        if msg and expire_time:
            await asyncio.sleep(expire_time)
            await delete_message(msg)
    except discord.Forbidden:
        log.warning("{}: Cannot send message, no permission".format(destination.name))
    except discord.NotFound:
        log.warning("{}: Cannot send message, invalid channel?".format(destination.name))

    return msg


async def edit_message(message, new=None, *, embed=None, expire_time=0, clear_reactions=False):
    msg = None
    if clear_reactions:
        try:
            await bot.clear_reactions(message)
        except discord.Forbidden:
            pass
    try:
        msg = await bot.edit_message(message, new, embed=embed)

        if msg and expire_time:
            await asyncio.sleep(expire_time)
            await delete_message(msg)
    except discord.NotFound:
        log.warning("Cannot edit message \"{}\", message not found".format(message.clean_content))

    return msg


async def delete_message(message):
    try:
        return await bot.delete_message(message)
    except discord.Forbidden:
        log.warning("Cannot delete message \"{}\", no permission".format(message.clean_content))
    except discord.NotFound:
        log.warning("Cannot delete message \"{}\", invalid channel?".format(message.clean_content))


async def cmd_wiki(message, query):
    if query is None:
        await send_message(message.channel, "Sorry, I couldn't find a search query in your message.", expire_time=5)
        return
    try:
        search = wikia.search(wikia_wiki, query)
        page = wikia.page(wikia_wiki, search[0])
        url = page.url.replace(" ", "_")
        await send_message(message.channel, url)
    except (ValueError, wikia.wikia.WikiaError):
        await send_message(message.channel, "Sorry, I have no information for your search query `{}`.".format(query),
                           expire_time=5)


async def cmd_role(message, desired_role):
    if message.channel.is_private:
        await send_message(message.channel, "You must be in a server to set your role.")
        return
    if desired_role is None:
        await send_message(message.channel, "Sorry, I can not seem to find a desired role in your message.")
        return
    available_roles = []
    new_role = None
    for role in message.server.roles:
        if role.permissions.manage_roles or not role.permissions.send_messages or role.is_everyone:
            continue
        if desired_role.lower() == role.name.lower():
            new_role = role
        available_roles.append(role)
    if new_role is None:
        friendly_available_roles = ""
        for role in available_roles:
            friendly_available_roles += ("`{}` ".format(role.name))
        await send_message(message.channel, "Sorry, but you can't be `{}`.\nAvailable roles are: {}".format(
            desired_role, friendly_available_roles))
        return
    await bot.remove_roles(message.author, *available_roles)
    await asyncio.sleep(.2)
    await bot.add_roles(message.author, new_role)
    role_change_message = "{} you are now a `{}`!".format(message.author.mention, new_role.name)
    role_change_embed = discord.Embed(
        title="Poof!", description=role_change_message, colour=0x42F465)
    role_change_embed.set_thumbnail(url=message.author.avatar_url)
    await send_message(message.channel, "", embed=role_change_embed)


async def cmd_help(user):
    help_title_embed = discord.Embed(
        title="Glyph Usage Help",
        description="The Glyph Discord bot employs an experimental concept of not using traditional commands "
                    "and instead making everything chat based when mentioned with @Glyph or sent a DM. "
                    "Currently Glyph can do a few basic tasks which are listed below. "
                    "Please keep in mind that Glyph is an experimental bot, "
                    "and that all messages sent to it are checked by a human to see if it responded correctly, "
                    "including private messages.",
        colour=0x4286F4)
    help_wiki_embed = discord.Embed(
        title="Wiki Search",
        description="Ask Glyph a question such as \"Who is Commander Shepard?\" "
                    "and Glyph will reply with the wiki page for Commander Shepard.",
        colour=0xF4BF42)
    help_role_embed = discord.Embed(
        title="Role Setting",
        description="If you ever want to change your vanity role just say something like \"Set me as Geth\"",
        colour=0xF4BF42)
    help_meme_embed = discord.Embed(
        title="me irl",
        description="Glyph is also capable of displaying memes from r/me_irl "
                    "simply when you mention something such as \"crippling depression\" or \"me irl\".",
        colour=0xF4BF42)
    help_cute_embed = discord.Embed(
        title="Catto, Doggo, Snek",
        description="You can also ask Glyph to show a random picture of a catto, doggo, or snek "
                    "simply by saying something like \"Show me pictures of fancy sneks\".",
        colour=0xF4BF42)
    help_status_embed = discord.Embed(
        title="Status Checking",
        description="Afraid Glyph is broken or not working, "
                    "say something like \"ping\" or \"are you working?\" to verify.",
        colour=0xF4BF42)
    await send_message(user, embed=help_title_embed)
    await send_message(user, embed=help_wiki_embed)
    await send_message(user, embed=help_role_embed)
    await send_message(user, embed=help_meme_embed)
    await send_message(user, embed=help_cute_embed)
    await send_message(user, embed=help_status_embed)


@bot.event
async def on_ready():
    log.info("Logged in as {} ({})".format(bot.user.name, bot.user.id))
    await bot.change_presence(game=discord.Game(name=discord_game))
    for server in bot.servers:
        log.info("{}: Connected to server.".format(server))
    await update_countdown()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # Check for spoilery words
    if any(word in message.clean_content.lower() for word in spoilers_keywords) and not (
                message.channel.name == spoilers_channel):
        await bot.add_reaction(message, "\u26A0")
        return
    # If FA link
    far = fa.Submission.regex
    if far.search(message.clean_content) and fa_quickview_enabled == "true":
        links = far.findall(message.clean_content)
        for link in links:
            link_type = link[4]
            link_id = link[5]
            if link_type == "view":
                try:
                    submission = fa.Submission(id=link_id)
                    embed = discord.Embed(
                        title=submission.title,
                        description="Posted by {} at {}\n"
                                    "{} > {} > {} > {} > {}\n"
                                    "Favorites: {} | Comments: {} | Views: {}".format(
                                        submission.author, submission.posted,
                                        submission.rating, submission.category, submission.theme, submission.species, submission.gender,
                                        submission.favorites, submission.comments, submission.views),
                        url=submission.link, colour=submission.color)
                    embed.set_footer(text="React \u274C to delete this. "
                                          "React \U0001F48C to receive full size image in a DM.")
                    if fa_quickview_thumbnail == "true":
                        download = submission.download
                        embed.set_thumbnail(url=download)
                    await send_message(message.channel, embed=embed)
                except ValueError:
                    pass
        return
    # Check if the message should be replied to
    if (bot.user in message.mentions) or (str(message.channel.type) == "private"):
        await bot.send_typing(message.channel)
        clean_message = re.sub("@{}".format(bot.user.display_name), "", message.clean_content)

        try:
            wit_resp = wit.message(clean_message)
            wit_intent = wit_resp["entities"]["intent"][0]["value"]
        except KeyError:
            await send_message(message.channel, "Sorry, I don't understand.\n"
                                                "If you need help, say `@{} help`.".format(bot.user.display_name))
            return
        try:
            parameter = wit_resp["entities"]["wikipedia_search_query"][0]["value"]
        except KeyError:
            parameter = None

        if wit_intent == "wiki":
            await cmd_wiki(message, parameter)
        elif wit_intent == "help":
            await cmd_help(message.author)
        elif wit_intent == "role":
            await cmd_role(message, parameter)
        elif wit_intent == "status":
            await send_message(message.channel, ":ok_hand:")
        else:
            try:
                multireddit = config.get("reddit", wit_intent)
                submission = reddit.subreddit(multireddit).random()
                await send_message(message.channel, submission.url)
            except (praw.exceptions.ClientException, PrawcoreException.NotFound):
                log.error("Wit Intent \"{}\" does nothing!".format(wit_intent))


@bot.event
async def on_member_join(member):
    server = member.server
    await send_message(member, "Hello {}!\n"
                               "I am Glyph, an info bot for Discord.\n"
                               "I see you just joined *{}*, and would like to welcome you and let you know the rules.\n"
                               "**Be kind.\nKeep channels on topic, and spoilers in #ark.\nHave fun.**\n"  # TODO Config
                               "If you want to learn more about what I can do, say `help`!\n".format(member.name,
                                                                                                     server.name))
    for channel in server.channels:
        if channel.is_default:
            await send_message(channel, "Welcome {}!".format(member.mention))


@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    removable = False
    is_fa_quickview = False
    if not reaction.message.author == bot.user:
        return
    try:
        removable = ("React \u274C to delete this." in str(message.embeds[0]))
        is_fa_quickview = ("React \U0001F48C to receive full size image in a DM." in str(message.embeds[0]))
    except IndexError:
        pass
    if reaction.emoji == "\u274C" and removable:
        embed = discord.Embed(description=":x: Removed!", colour=0xFF0000)
        await edit_message(reaction.message, embed=embed, expire_time=5, clear_reactions=True)
    elif reaction.emoji == "\U0001F48C" and is_fa_quickview:
        # try:
        #     await bot.remove_reaction(message, "\U0001F48C️", user)
        # except discord.Forbidden or discord.HTTPException:
        #     pass
        try:
            embed = message.embeds[0]
            submission = fa.Submission(embed['url'])
            embed = discord.Embed(title=submission.title, url=submission.link, colour=submission.color)
            embed.set_footer(text="React \u274C to delete this.")
            embed.set_image(url=submission.download)
            await send_message(user, embed=embed)
        except ValueError:
            await send_message(user, "Sorry, I failed to get the full sized image for you.")


bot.run(environ.get("DISCORD_TOKEN"))
