import asyncio
import configparser
import json
import re
from datetime import datetime
from io import BytesIO
from os import environ

import discord
import praw
import requests
import wikia
from PIL import Image, ImageFont, ImageDraw
from prawcore import PrawcoreException
from wit import Wit

description = "A Discord bot based on Glyph from Mass Effect"

bot = discord.Client()

config = configparser.ConfigParser()
config.read("config.ini")
discord_game = config.get("discord", "game")
discord_token = environ.get("DISCORD_TOKEN")
wikia_wiki = config.get("wikia", "wiki")
wit_token = environ.get("WIT_TOKEN")
reddit_client_id = environ.get("REDDIT_CLIENT_ID")
reddit_client_secret = environ.get("REDDIT_SECRET")
reddit_user_agent = environ.get("REDDIT_USER_AGENT")
spoilers_channel = config.get("spoilers", "channel")
spoilers_keywords = config.get("spoilers", "keywords").split(",")
countdown_enabled = config.get("countdown", "enabled")
fa_quickview_enabled = config.get("FA QuickView", "enabled")
fa_quickview_thumbnail = config.get("FA QuickView", "thumbnail")

w = Wit(access_token=wit_token)
r = praw.Reddit(client_id=reddit_client_id, client_secret=reddit_client_secret, user_agent=reddit_user_agent)


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
        endday = datetime.strptime(date, "%Y-%m-%d").date()
        diff = endday - today
        text = str(diff.days)
        img = Image.open(icon)
        W, H = img.size

        draw = ImageDraw.Draw(img)
        large_font = ImageFont.truetype(font, size)
        small_font = ImageFont.truetype(font, int(.500 * size))
        pw, ph = small_font.getsize(prefix)
        tw, th = large_font.getsize(text)
        sw, sh = small_font.getsize(suffix)
        x, y = (W - (pw + tw + sw)) / 2, (H - th - 15) / 2
        draw.text((x - tw, y + int(.5 * th)), prefix, (r, g, b), font=small_font)
        draw.text((x, y), text, (r, g, b), font=large_font)
        draw.text((x + tw, y + int(.5 * th)), suffix, (r, g, b), font=small_font)

        with BytesIO() as data:
            img.save(data, format="PNG")
            for server in bot.servers:
                try:
                    await bot.edit_server(server, icon=data.getvalue())
                    print("{}: Set icon to {} days!".format(server.name, text))
                except discord.Forbidden:
                    print("{}: Failed to set icon. Permission 'Manage Server' is required!".format(server.name))

async def send_message(destination, content=None, *, embed=None, expire_time=0):
    if content is None and embed is None:
        print("A message needs to have content!")
        return None
    msg = None
    try:
        msg = await bot.send_message(destination, content, embed=embed)

        if msg and expire_time:
            await asyncio.sleep(expire_time)
            await delete_message(msg)
    except discord.Forbidden:
        print("{}: Cannot send message, no permission".format(destination.name))
    except discord.NotFound:
        print("{}: Cannot send message, invalid channel?".format(destination.name))

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
        print("Cannot edit message \"{}\", message not found".format(message.clean_content))

    return msg

async def delete_message(message):
    try:
        return await bot.delete_message(message)
    except discord.Forbidden:
        print("Cannot delete message \"{}\", no permission".format(message.clean_content))
    except discord.NotFound:
        print("Cannot delete message \"{}\", invalid channel?".format(message.clean_content))

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
                    "(Please keep in mind that Glyph is an experimental bot, "
                    "and that all messages sent to it are checked by a human to see if it responded correctly, "
                    "including private messages.)",
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
    print("Logged in as {} ({})".format(bot.user.name, bot.user.id))
    print("------")
    await bot.change_presence(game=discord.Game(name=discord_game))
    for server in bot.servers:
        print("{}: Connected to server.".format(server))
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
    far = re.compile("((http[s]?):\/\/)?(www\.)?(furaffinity.net)\/(\w*)\/(\d{8})\/?", re.IGNORECASE)
    if far.search(message.clean_content) and fa_quickview_enabled == "true":
        links = far.findall(message.clean_content)
        for link in links:
            link_type = link[4]
            link_id = link[5]
            if link_type == "view":
                try:
                    get = requests.get("http://faexport.boothale.net/submission/{}.json".format(link_id)).text
                    submission_info = json.loads(get)
                    title = submission_info.get("title")
                    author = submission_info.get("name")
                    posted = submission_info.get("posted")
                    category = submission_info.get("category")
                    theme = submission_info.get("theme")
                    species = submission_info.get("species")
                    gender = submission_info.get("gender")
                    favorites = submission_info.get("favorites")
                    comments = submission_info.get("comments")
                    views = submission_info.get("views")
                    rating = submission_info.get("rating")
                    link = submission_info.get("link")
                    if rating == "General":
                        color = 0x10FF00
                    elif rating == "Mature":
                        color = 0x0026FF
                    else:  # rating=="Adult"
                        color = 0xFF0000
                    embed = discord.Embed(
                        title=title,
                        description="Posted by {} at {}\n"
                                    "{} > {} > {} > {} > {}\n"
                                    "Favorites: {} | Comments: {} | Views: {}".format(
                                        author, posted,
                                        rating, category, theme, species, gender,
                                        favorites, comments, views),
                                    url=link, colour=color)
                    embed.set_footer(text="React \u274C to delete this.")
                    if fa_quickview_thumbnail == "true":
                        download = submission_info.get("download")
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
            wit_resp = w.message(clean_message)
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
                submission = r.subreddit(multireddit).random()
                await send_message(message.channel, submission.url)
            except (praw.exceptions.ClientException, PrawcoreException.NotFound):
                print("Wit Intent \"{}\" does nothing!".format(wit_intent))


@bot.event
async def on_reaction_add(reaction, user):
    try:
        removable = ("React \u274C to delete this." in str(reaction.message.embeds[0]))
    except IndexError:
        removable = False
    if reaction.message.author == bot.user and reaction.emoji == "\u274C" and removable:
        embed = discord.Embed(description=":x: Removed!", colour=0xFF0000)
        await edit_message(reaction.message, embed=embed, expire_time=5, clear_reactions=True)


bot.run(discord_token)
