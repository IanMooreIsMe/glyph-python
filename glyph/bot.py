import asyncio
import configparser
import logging
import random
import re
from os import environ

import discord
import praw
import requests
import wikia
from wit import Wit

from . import auditing
from . import fa
from . import picarto
from .countdown import Countdown

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class GlyphBot(discord.Client):

    def __init__(self):
        self.audit = auditing.Logger(self)
        self.config = configparser.ConfigParser()
        self.config.read("./config/config.ini")
        self.wit = Wit(access_token=environ.get("WIT_TOKEN"))
        self.reddit = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                                  client_secret=environ.get("REDDIT_SECRET"),
                                  user_agent=environ.get("REDDIT_USER_AGENT"))
        super().__init__()

    def update_server_count(self):
        count = len(self.servers)
        url = "https://discordbots.org/api/bots/{}/stats".format(self.user.id)
        header = {'Authorization': environ.get("DISCORDBOTLIST_TOKEN")}
        data = {'server_count': count}
        req = requests.post(url, data=data, headers=header)
        if req.status_code == 200:
            log.info("Updated count with {} servers!".format(count))
        else:
            log.warning("Failed to update server count with error code {}!".format(req.status_code))

    def get_config_message(self, file, user, server):
        if isinstance(user, discord.User):
            user = user.name
        else:
            user = "you"
        if isinstance(server, discord.Server):
            server = server.name
        else:
            server = "the server"
        with open("./config/{}.txt".format(file), "r") as file:
            text = file.read()
            text = text.replace("{BOTNAME}", self.user.name)
            text = text.replace("{USER}", user)
            text = text.replace("{SERVER}", server)
        return text

    async def safe_send_typing(self, destination):
        if destination is None:
            log.error("Send typing needs a destination!")
            return None
        try:
            await self.send_typing(destination)
        except discord.Forbidden:
            log.warning("{} - {}: Cannot send typing, no permission?".format(destination.server, destination.name))
        except discord.NotFound:
            log.warning("{} - {}: Cannot send typing, invalid channel?".format(destination.server, destination.name))

    async def safe_send_message(self, destination, content=None, *, embed=None, expire_time=0, removable=False):
        if content is None and embed is None:
            log.error("A message needs to have content!")
            return None
        elif embed is not None and removable:
            embed.set_footer(text="React \u274C to delete this.")
        msg = None
        try:
            msg = await self.send_message(destination, content, embed=embed)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.delete_message(msg)
        except discord.Forbidden:
            log.warning("{} - {}: Cannot send message, no permission?".format(destination.server, destination.name))
        except discord.NotFound:
            log.warning("{} - {}: Cannot send message, invalid channel?".format(destination.server, destination.name))

        return msg

    async def safe_edit_message(self, message, new=None, *,
                                embed=None, expire_time=0, clear_reactions=False, removable=False):
        if embed is not None and removable:
            embed.set_footer(text="React \u274C to delete this.")
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
            log.warning("Cannot delete message \"{}\", no permission?".format(message.clean_content))
        except discord.NotFound:
            log.warning("Cannot delete message \"{}\", invalid channel?".format(message.clean_content))

    async def safe_add_roles(self, member, *roles):
        try:
            return await self.add_roles(member, *roles)
        except discord.Forbidden:
            log.warning("Cannot add roles, no permission?")

    async def safe_remove_roles(self, member, *roles):
        try:
            return await self.remove_roles(member, *roles)
        except discord.Forbidden:
            log.warning("Cannot remove roles, no permission?")

    async def cmd_wiki(self, message, wit, *, wiki=None, query=None):
        if wit is not None:
            try:
                wiki = wit["entities"]["command"][0]["metadata"]
            except KeyError:
                await self.safe_send_message(message.channel, "Sorry, wiki search is not correctly set up.")
                return
            try:
                query = wit["entities"]["wikipedia_search_query"][0]["value"]
            except KeyError:
                await self.safe_send_message(message.channel, "Sorry, I couldn't find a search query.", expire_time=5)
                return
        try:
            search = wikia.search(wiki, query)
            page = wikia.page(wiki, search[0])
            url = page.url.replace(" ", "_")
            embed = discord.Embed(title=page.title, url=url, description=page.summary)
            try:
                embed.set_thumbnail(url=page.images[0])
            except IndexError:
                pass
            await self.safe_send_message(message.channel, embed=embed, removable=True)
        except (ValueError, wikia.wikia.WikiaError):
            await self.safe_send_message(message.channel,
                                         "Sorry, I have no information for your search query `{}`.".format(query),
                                         expire_time=5)

    async def cmd_change_role(self, message, wit=None, *, target_user=None, desired_role=None):
        if message.channel.is_private:  # You can't set a role, if you're not in a server
            await self.safe_send_message(message.channel, "You must be in a server to set a role.")
            return
        if wit is not None:  # Get all the values needed to assign people roles
            try:
                # TODO: Finish rewriting for loops with discord.utils equivalents
                target_user = discord.utils.get(message.server.members, name=wit["entities"]["user"][0]["value"])
                for user in message.server.members:
                    if user.name in wit["entities"]["user"][0]["value"]:
                        target_user = user
                        break
                else:
                    await self.safe_send_message(message.channel,
                                                 "Sorry, I can't seem to find {} in this server.".format(
                                                     wit["entities"]["user"][0]["value"]))
                    return
                if not message.author.permissions_in(message.channel).manage_roles:
                    await self.safe_send_message(message.channel,
                                                 "You don't have permission to set {}'s role.".format(target_user.name))
                    return
            except KeyError:
                target_user = message.author
            try:
                desired_role = wit["entities"]["role"][0]["value"]
            except KeyError:
                await self.safe_send_message(message.channel,
                                             "Sorry, I can not seem to find a desired role in your message.")
                return
        # TODO: Check permissions and improve safe remove and add permissions
        available_roles = []
        new_role = None
        for role in message.server.roles:  # Make a list of roles the user has permission for and save the one they want
            if not role.permissions.manage_roles and role.permissions.send_messages and not role.is_everyone:
                available_roles.append(role)
                if desired_role == role.name.lower():
                    new_role = role
        if new_role is None:
            friendly_available_roles = ""
            for role in available_roles:
                friendly_available_roles += ("`{}` ".format(role.name))
            await self.safe_send_message(message.channel, "Sorry, but you can't be `{}`.\n"
                                                          "Available roles are: {}".format(desired_role,
                                                                                           friendly_available_roles))
            return
        await self.safe_remove_roles(target_user, *available_roles)  # Remove all old roles
        await asyncio.sleep(.2)  # Wait because of rate limiting
        await self.safe_add_roles(target_user, new_role)  # Add the new role
        role_change_message = "{} you are now a {}!".format(target_user.mention, new_role.mention)
        role_change_embed = discord.Embed(
            title="Poof!", description=role_change_message, colour=0x42F465)
        role_change_embed.set_thumbnail(url=target_user.avatar_url)
        await self.safe_send_message(message.channel, "", embed=role_change_embed)

    async def cmd_reddit(self, message, wit, *, multireddit=None):
        if wit is not None:
            try:
                multireddit = wit["entities"]["multireddit"][0]["metadata"]
            except KeyError:
                await self.safe_send_message(message.channel, "I think you wanted an image from Reddit, "
                                                              "but I'm not sure of what. Sorry.")
                return
        try:
            while True:  # Get an image that can be embedded
                try:
                    submission = self.reddit.subreddit(multireddit).random()
                except TypeError:
                    continue
                if any(extension in submission.url for extension in [".png", ".jpg", ".jpeg", ".gif"]) \
                        and submission.score > self.config.getint("Reddit", "score_threshold"):
                    break
            embed = discord.Embed(title=submission.title, url=submission.shortlink)
            embed.set_image(url=submission.url)
            await self.safe_send_message(message.channel, embed=embed, removable=True)
        except praw.exceptions.ClientException:
            await self.safe_send_message(message.channel, "Sorry, I had an issue communicating with Reddit.")

    async def cmd_help(self, message):
        help_embed = discord.Embed(
            title="Glyph Help",
            description=self.get_config_message("help", message.author, message.server),
            colour=0x4286F4)
        await self.safe_send_message(message.author, embed=help_embed)
        if message.channel.type is not discord.ChannelType.private:
            await self.safe_send_message(message.channel, "Sending you a PM now.", expire_time=5)

    async def on_ready(self):
        log.info("Logged in as {} ({})".format(self.user.name, self.user.id))
        await self.change_presence(game=discord.Game(name=self.config.get("discord", "game")))
        self.update_server_count()
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
        # Don't talk to yourself
        if message.author == self.user or message.author.bot:
            return
        # Check for spoilery words
        # spoilers_channel = self.config.get("spoilers", "channel")
        # spoilers_keywords = self.config.get("spoilers", "keywords").split(",")
        # if any(word in message.clean_content.lower() for word in spoilers_keywords) and not (
        #            message.channel.name == spoilers_channel):
        #    await self.add_reaction(message, "\u26A0")
        # FA QuickView
        r = fa.Submission.regex
        if r.search(message.clean_content) and self.config.getboolean("FA QuickView", "enabled"):
            links = r.findall(message.clean_content)
            for link in links:
                link_type = link[4]
                link_id = link[5]
                if link_type == "view":
                    try:
                        submission = fa.Submission(id=link_id)
                        embed = submission.get_embed(thumbnail=self.config.getboolean("FA QuickView", "thumbnail"))
                        await self.safe_send_message(message.channel, embed=embed, removable=True)
                    except ValueError:
                        pass
        # Picarto QuickView
        r = picarto.Channel.regex
        if r.search(message.clean_content) and self.config.getboolean("Picarto QuickView", "enabled"):
            links = r.findall(message.clean_content)
            for link in links:
                link_name = link[4]
                try:
                    channel = picarto.Channel(name=link_name)
                    embed = channel.get_embed()
                    await self.safe_send_message(message.channel, embed=embed, removable=True)
                except ValueError:
                    pass
        # Check if the message should be replied to
        if (self.user in message.mentions or message.channel.type is discord.ChannelType.private) \
                and message.clean_content:  # Mae sure message isn't empty
            await self.safe_send_typing(message.channel)
            clean_message = re.sub("@{}".format(self.user.display_name), "", message.clean_content)

            wit = None
            command = None
            try:
                wit = self.wit.message(clean_message)
                command = wit["entities"]["command"][0]["value"]
            except KeyError:
                pass

            if command == "wiki":
                await self.cmd_wiki(message, wit)
            elif command == "help":
                await self.cmd_help(message)
            elif command == "role":
                await self.cmd_change_role(message, wit)
            elif command == "status":
                await self.safe_send_message(message.channel, ":ok_hand:")
            elif command == "reddit":
                await self.cmd_reddit(message, wit)
            else:
                response = "I feel like I should know what to say, but haven't learned yet, try asking me again later."
                if wit is not None:
                    try:
                        canned_responses = wit["entities"]["canned_response"][0]["metadata"].split("\n")
                        response = random.choice(canned_responses)
                    except KeyError:
                        help_command = "help"
                        if message.channel.type is not discord.ChannelType.private:
                            help_command = "@{} help".format(self.user.display_name)
                        await self.safe_send_message(message.channel,
                                                     "Sorry, I don't understand (yet).\n"
                                                     "If you need help, say `{}`.".format(help_command))
                        return
                await self.safe_send_message(message.channel, response)

    async def on_member_join(self, member):
        server = member.server
        if server.id in self.config.get("ignore", "servers").split(","):  # Ignore servers
            return
        if self.config.getboolean("modlog", "joins"):
            await self.audit.log(member.server, auditing.MEMBER_JOIN,
                                 "{} joined the server.".format(member.mention), user=member)  # Mod log
        welcomed = await self.safe_send_message(server.default_channel, "Welcome {}!".format(member.mention))
        if welcomed:
            text = self.get_config_message("welcome", member, server)
            welcome_embed = discord.Embed(
                title="Welcome to {}!".format(server.name),
                description=text,
                colour=0x4286F4)
            await self.safe_send_message(member, embed=welcome_embed)

    async def on_member_remove(self, member):
        server = member.server
        if server.id in self.config.get("ignore", "servers").split(","):  # Ignore servers
            return
        if self.config.getboolean("modlog", "leaves"):
            await self.audit.log(member.server, auditing.MEMBER_LEAVE,
                                 "{} left the server.".format(member.mention), user=member)
        # invite = self.create_invite(member.server).url
        # await self.safe_send_message(member, "Did you leave {} by accident?
        #                                       Here's a reinvite: {}".format(member.server, invite))

    async def on_reaction_add(self, reaction, user):
        if self.config.getboolean("modlog", "reactions"):
            await self.audit.log(reaction.message.server, auditing.REACTION_ADD,
                                 "{} added reaction {} to {}".format(user.mention,
                                                                     reaction.emoji, reaction.message.content),
                                 user=user)
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
            await self.safe_edit_message(reaction.message, embed=embed, expire_time=5, clear_reactions=True)
        elif reaction.emoji == "\U0001F48C" and is_fa_quickview:
            try:
                embed = message.embeds[0]
                submission = fa.Submission(url=embed['url'])
                embed = discord.Embed(title=submission.title, url=submission.link, colour=submission.color)
                embed.set_footer(text="React \u274C to delete this.")
                embed.set_image(url=submission.download)
                await self.safe_send_message(user, embed=embed)
            except ValueError:
                await self.safe_send_message(user, "Sorry, I failed to get the full sized image for you.")

    async def on_reaction_remove(self, reaction, user):
        if self.config.getboolean("modlog", "reactions"):
            await self.audit.log(reaction.message.server, auditing.REACTION_REMOVE,
                                 "{} removed reaction {} from {}".format(user.mention,
                                                                         reaction.emoji, reaction.message.content),
                                 user=user)

    async def on_server_join(self, server):
        log.info("{}: Added to server.".format(server))

    async def on_server_remove(self, server):
        log.info("{}: Removed from server.".format(server))

if __name__ == '__main__':
    bot = GlyphBot()
    bot.run(environ.get("DISCORD_TOKEN"))
