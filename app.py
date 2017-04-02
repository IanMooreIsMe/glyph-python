import asyncio
import configparser
import re
from os import environ
import logging

import discord
import praw
import wikia

from wit import Wit
import fa
import modlogger
from countdown import Countdown

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class Glyph(discord.Client):

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.discord_game = self.config.get("discord", "game")
        self.wikia_wiki = self.config.get("wikia", "wiki")
        self.spoilers_channel = self.config.get("spoilers", "channel")
        self.spoilers_keywords = self.config.get("spoilers", "keywords").split(",")
        self.fa_quickview_enabled = self.config.getboolean("FA QuickView", "enabled")
        self.fa_quickview_thumbnail = self.config.getboolean("FA QuickView", "thumbnail")
        self.wit = Wit(access_token=environ.get("WIT_TOKEN"))
        self.reddit = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                                  client_secret=environ.get("REDDIT_SECRET"),
                                  user_agent=environ.get("REDDIT_USER_AGENT"))
        super().__init__()

    async def safe_send_message(self, destination, content=None, *, embed=None, expire_time=0):
        if content is None and embed is None:
            log.error("A message needs to have content!")
            return None
        msg = None
        try:
            msg = await self.send_message(destination, content, embed=embed)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.delete_message(msg)
        except discord.Forbidden:
            log.warning("{}: Cannot send message, no permission".format(destination.name))
        except discord.NotFound:
            log.warning("{}: Cannot send message, invalid channel?".format(destination.name))

        return msg

    async def safe_edit_message(self, message, new=None, *, embed=None, expire_time=0, clear_reactions=False):
        msg = None
        if clear_reactions:
            try:
                await self.clear_reactions(message)
            except discord.Forbidden:
                pass
        try:
            msg = await self.edit_message(message, new, embed=embed)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.safe_delete_message(msg)
        except discord.NotFound:
            log.warning("Cannot edit message \"{}\", message not found".format(message.clean_content))

        return msg

    async def safe_delete_message(self, message):
        try:
            return await self.delete_message(message)
        except discord.Forbidden:
            log.warning("Cannot delete message \"{}\", no permission".format(message.clean_content))
        except discord.NotFound:
            log.warning("Cannot delete message \"{}\", invalid channel?".format(message.clean_content))

    async def cmd_wiki(self, message, query):
        if query is None:
            await self.safe_send_message(message.channel, "Sorry, I couldn't find a search query in your message.",
                                         expire_time=5)
            return
        try:
            search = wikia.search(self.wikia_wiki, query)
            page = wikia.page(self.wikia_wiki, search[0])
            url = page.url.replace(" ", "_")
            await self.safe_send_message(message.channel, url)
        except (ValueError, wikia.wikia.WikiaError):
            await self.safe_send_message(message.channel,
                                         "Sorry, I have no information for your search query `{}`.".format(query),
                                         expire_time=5)

    async def cmd_role(self, message, desired_role):
        if message.channel.is_private:
            await self.safe_send_message(message.channel, "You must be in a server to set your role.")
            return
        if desired_role is None:
            await self.safe_send_message(message.channel,
                                         "Sorry, I can not seem to find a desired role in your message.")
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
            await self.safe_send_message(message.channel, "Sorry, but you can't be `{}`.\n"
                                                          "Available roles are: {}".format(desired_role,
                                                                                           friendly_available_roles))
            return
        await self.remove_roles(message.author, *available_roles)
        await asyncio.sleep(.2)
        await self.add_roles(message.author, new_role)
        role_change_message = "{} you are now a `{}`!".format(message.author.mention, new_role.name)
        role_change_embed = discord.Embed(
            title="Poof!", description=role_change_message, colour=0x42F465)
        role_change_embed.set_thumbnail(url=message.author.avatar_url)
        await self.safe_send_message(message.channel, "", embed=role_change_embed)

    async def cmd_help(self, user):
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
        await self.safe_send_message(user, embed=help_title_embed)
        await self.safe_send_message(user, embed=help_wiki_embed)
        await self.safe_send_message(user, embed=help_role_embed)
        await self.safe_send_message(user, embed=help_meme_embed)
        await self.safe_send_message(user, embed=help_cute_embed)
        await self.safe_send_message(user, embed=help_status_embed)

    async def on_ready(self):
        log.info("Logged in as {} ({})".format(self.user.name, self.user.id))
        await self.change_presence(game=discord.Game(name=self.discord_game))
        for server in self.servers:
            log.info("{}: Connected to server.".format(server))
            if self.config.getboolean("countdown", "enabled"):
                date = self.config.get("countdown", "date")
                icon = self.config.get("countdown", "icon")
                font = self.config.get("countdown", "font")
                size = self.config.getint("countdown", "size")
                color = self.config.get("countdown", "color")
                suffix = self.config.get("countdown", "suffix")
                prefix = self.config.get("countdown", "prefix")

                countdown = Countdown(self, server, date, icon, font, size, color, suffix, prefix)
                log.info(await countdown.update())

    async def on_message(self, message):
        if message.author == self.user:
            return
        # Check for spoilery words
        if any(word in message.clean_content.lower() for word in self.spoilers_keywords) and not (
                    message.channel.name == self.spoilers_channel):
            await self.add_reaction(message, "\u26A0")
            return
        # If FA link
        far = fa.Submission.regex
        if far.search(message.clean_content) and self.fa_quickview_enabled:
            links = far.findall(message.clean_content)
            for link in links:
                link_type = link[4]
                link_id = link[5]
                if link_type == "view":
                    try:
                        submission = fa.Submission(id=link_id)
                        embed = submission.get_embed(thumbnail=bool(self.fa_quickview_thumbnail))
                        await self.safe_send_message(message.channel, embed=embed)
                    except ValueError:
                        pass
            return
        # Check if the message should be replied to
        if (self.user in message.mentions) or (str(message.channel.type) == "private"):
            await self.send_typing(message.channel)
            clean_message = re.sub("@{}".format(self.user.display_name), "", message.clean_content)

            try:
                wit_resp = self.wit.message(clean_message)
                wit_intent = wit_resp["entities"]["intent"][0]["value"]
            except KeyError:
                await self.safe_send_message(message.channel,
                                             "Sorry, I don't understand.\n"
                                             "If you need help, say `@{} help`.".format(self.user.display_name))
                return
            try:
                parameter = wit_resp["entities"]["wikipedia_search_query"][0]["value"]
            except KeyError:
                parameter = None

            if wit_intent == "wiki":
                await self.cmd_wiki(message, parameter)
            elif wit_intent == "help":
                await self.cmd_help(message.author)
            elif wit_intent == "role":
                await self.cmd_role(message, parameter)
            elif wit_intent == "status":
                await self.safe_send_message(message.channel, ":ok_hand:")
            else:
                try:
                    multireddit = self.config.get("reddit", wit_intent)
                    while True:
                        try:
                            submission = self.reddit.subreddit(multireddit).random()
                        except TypeError:
                            continue
                        if ".png" in submission.url:
                            break
                    embed = discord.Embed(
                        title=submission.title,
                        url=submission.shortlink)
                    embed.set_footer(text="React \u274C to delete this.")
                    embed.set_image(url=submission.url)
                    await self.safe_send_message(message.channel, embed=embed)
                except praw.exceptions.ClientException:
                    log.error("Wit Intent \"{}\" does nothing!".format(wit_intent))

    async def on_member_join(self, member):
        if self.config.getboolean("modlog", "joins"):
            await modlog.log(member.server, modlogger.MEMBER_JOIN,
                             "{} joined the server.".format(member.name), user=member)
        server = member.server
        await self.safe_send_message(member, "Hello {}!\n"
                                             "I am Glyph, an info bot for Discord.\n"
                                             "I see you just joined *{}*, and would like to welcome you and let you know the rules.\n"
                                             "**Be kind.\nKeep channels on topic, and spoilers in #ark.\nHave fun.**\n"  # TODO Config
                                             "If you want to learn more about what I can do, say `help`!\n".format(member.name, server.name))
        for channel in server.channels:
            if channel.is_default:
                await self.safe_send_message(channel, "Welcome {}!".format(member.mention))

    async def on_member_remove(self, member):
        if self.config.getboolean("modlog", "leaves"):
            await modlog.log(member.server, modlogger.MEMBER_LEAVE,
                             "{} left the server.".format(member.name), user=member)
        # TODO: Find a way to send people invites when they aren't on a server with the bot
        invite = self.create_invite(member.server)
        await self.safe_send_message(member, "Did you leave {} by accident? Here's a reinvite: {}".format(member.server,
                                                                                                          invite))

    async def on_reaction_add(self, reaction, user):
        if self.config.getboolean("modlog", "reactions"):
            await modlog.log(reaction.message.server, modlogger.REACTION_ADD,
                             "Added reaction {} to {}".format(reaction.emoji, reaction.message.content), user=user)
        message = reaction.message
        removable = False
        is_fa_quickview = False
        if not reaction.message.author == self.user:
            return
        try:
            removable = ("React \u274C to delete this." in str(message.embeds[0]))
            is_fa_quickview = ("React \U0001F48C to receive full size image in a DM." in str(message.embeds[0]))
        except IndexError:
            pass
        if reaction.emoji == "\u274C" and removable:
            embed = discord.Embed(description=":x: Removed!", color=0xFF0000)
            await self.edit_message(reaction.message, embed=embed, expire_time=5, clear_reactions=True)
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
                await self.safe_send_message(user, embed=embed)
            except ValueError:
                await self.safe_send_message(user, "Sorry, I failed to get the full sized image for you.")

    async def on_reaction_remove(self, reaction, user):
        if self.config.getboolean("modlog", "reactions"):
            await modlog.log(reaction.message.server, modlogger.REACTION_REMOVE,
                             "Removed reaction {} from {}".format(reaction.emoji, reaction.message.content), user=user)

bot = Glyph()
modlog = modlogger.Logger(bot, "log")
bot.run(environ.get("DISCORD_TOKEN"))
