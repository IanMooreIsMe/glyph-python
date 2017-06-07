import asyncio
import logging
import re
from datetime import datetime
from os import environ

import discord
import praw
import requests
import wikia

from . import apiai
from . import auditing
from . import fa
from . import picarto
from . import serverconfig

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class GlyphBot(discord.Client):

    def __init__(self):
        self.auditor = auditing.Auditor(self)
        self.apiai = apiai.AIProcessor(client_access_token=environ.get("APIAI_TOKEN"))
        self.configs = {None: serverconfig.Config()}  # Set up for DMs
        self.reddit = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                                  client_secret=environ.get("REDDIT_SECRET"),
                                  user_agent=environ.get("REDDIT_USER_AGENT"))
        super().__init__()

    def update_server_count(self):
        count = len(self.servers)
        # Discord Bot List
        url = "https://discordbots.org/api/bots/{}/stats".format(self.user.id)
        header = {"Content-Type": "application/json", "Authorization": environ.get("DISCORDBOTLIST_TOKEN")}
        data = {"server_count": count}
        req = requests.post(url, json=data, headers=header)
        if req.status_code == 200:
            log.info("Updated Discord Bot List count with {} servers!".format(count))
        else:
            log.warning("Failed to update Discord Bot List server count with error code {}!".format(req.status_code))
        # Discord Bots
        url = "https://bots.discord.pw/api/bots/{}/stats".format(self.user.id)
        header = {"Content-Type": "application/json", "Authorization": environ.get("DISCORDBOTS_TOKEN")}
        data = {"server_count": count}
        req = requests.post(url, json=data, headers=header)
        if req.status_code == 200:
            log.info("Updated Discord Bots count with {} servers!".format(count))
        else:
            log.warning("Failed to update Discord Bots server count with error code {}!".format(req.status_code))

    def get_config_message(self, file, user=None, server=None):
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

    async def safe_kick(self, member):
        kick = None
        try:
            kick = await self.kick(member)
        except discord.Forbidden:
            log.warning("{}: Cannot kick member, no permission?".format(member.server))
        except discord.HTTPException:
            log.warning("{}: Cannot kick member, kicking failed?".format(member.server))
        return kick

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

    async def skill_wiki(self, message, *, wiki=None, query=None):
        if wiki is None:
            await self.safe_send_message(message.channel, "Sorry, no valid wiki is set.", expire_time=5)
            return
        if query is None:
            await self.safe_send_message(message.channel, "Sorry, I couldn't find a search query.", expire_time=5)
            return
        try:
            search = wikia.search(wiki, query)
            page = wikia.page(wiki, search[0])
            url = page.url.replace(" ", "_")
            embed = discord.Embed(title=page.title, url=url, description=page.summary)
            try:
                embed.set_thumbnail(url=page.images[0])
            except (IndexError, AttributeError):
                pass
            await self.safe_send_message(message.channel, embed=embed, removable=True)
        except (ValueError, wikia.wikia.WikiaError):
            await self.safe_send_message(message.channel,
                                         "Sorry, I have no information for your search query `{}`.".format(query),
                                         expire_time=5)

    async def skill_change_role(self, message, *, target_user=None, desired_role=None):
        if message.channel.is_private:  # You can't set a role, if you're not in a server
            await self.safe_send_message(message.channel, "You must be in a server to set a role.")
            return
        try:
            # TODO: Finish rewriting for loops with discord.utils equivalents
            target_user = discord.utils.get(message.server.members, name=target_user)
            if target_user is None:
                await self.safe_send_message(message.channel,
                                             "Sorry, I can't seem to find {} in this server.".format(target_user))
                return
            if not message.author.permissions_in(message.channel).manage_roles:
                await self.safe_send_message(message.channel,
                                             "You don't have permission to set {}'s role.".format(target_user.name))
                return
        except KeyError:
            target_user = message.author
        if desired_role is None:
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

    async def skill_status(self, message):
        start = datetime.now().microsecond
        msg = await self.safe_send_message(message.channel,
                                           ":ok_hand: ? ms ping in {} servers!".format(len(self.servers)))
        diff = int((datetime.now().microsecond - start)/1000)
        await self.safe_edit_message(msg, ":ok_hand: {} ms ping in {} servers!".format(diff, len(self.servers)))

    async def skill_reddit(self, message, *, multireddit=None):
        if multireddit is None:
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
                        and submission.score > 10:
                    break
            embed = discord.Embed(title=submission.title, url=submission.shortlink)
            embed.set_image(url=submission.url)
            await self.safe_send_message(message.channel, embed=embed, removable=True)
        except praw.exceptions.ClientException:
            await self.safe_send_message(message.channel, "Sorry, I had an issue communicating with Reddit.")

    async def skill_help(self, message):
        help_embed = discord.Embed(
            title="Glyph Help",
            description=self.get_config_message("help", message.author, message.server),
            colour=0x4286F4)
        await self.safe_send_message(message.author, embed=help_embed)
        if message.channel.type is not discord.ChannelType.private:
            await self.safe_send_message(message.channel, "Sending you a PM now.", expire_time=5)

    async def skill_kick(self, message, wit, *, member=None):
        if message.channel.is_private:
            await self.safe_send_message(message.channel, "You have to be in a server to kick someone.")
            return
        elif not message.author.server_permissions.kick_members:
            await self.safe_send_message(message.channel, "You don't have permission to do kick people.")
            return
        # Get the user
        if member is None:
            try:
                member = discord.utils.get(message.server.members, name=wit["entities"]["user"][0]["value"])
            except KeyError:
                await self.safe_send_message(message.channel, "Sorry, I couldn't find a user to kick.")
                return
        # Kick the user
        kick = await self.safe_kick(member)
        if kick:
            await self.safe_send_message(message.channel, ":ok_hand: ***{} has been kicked!***".format(member.mention))

    async def on_ready(self):
        log.info("Logged in as {} ({})".format(self.user.name, self.user.id))
        await self.change_presence(game=discord.Game(name="Armax Arsenal Arena"))
        self.update_server_count()
        for server in self.servers:
            self.configs.update({server: serverconfig.Config(server)})
            log.info("{}: Connected to server.".format(server))

    async def on_message(self, message):
        # Don't talk to yourself
        if message.author == self.user or message.author.bot:
            return
        server = message.server
        config = self.configs.get(server)

        # Check for spoilery words
        if config.getboolean("spoilers", "enabled"):
            spoilers_channel = config.get("spoilers", "channel")
            spoilers_keywords = config.get("spoilers", "keywords").split(",")
            if any(word in message.clean_content.lower() for word in spoilers_keywords) \
                    and not (message.channel.name == spoilers_channel):
                await self.add_reaction(message, "\u26A0")  # React with a warning emoji
        # FA QuickView
        r = fa.Submission.regex
        if r.search(message.clean_content) and config.getboolean("FA QuickView", "enabled"):
            links = r.findall(message.clean_content)
            for link in links:
                link_type = link[4]
                link_id = link[5]
                if link_type == "view":
                    try:
                        submission = fa.Submission(id=link_id)
                        embed = submission.get_embed(thumbnail=config.getboolean("FA QuickView", "thumbnail"))
                        await self.safe_send_message(message.channel, embed=embed, removable=True)
                    except ValueError:
                        pass
        # Picarto QuickView
        r = picarto.Channel.regex
        if r.search(message.clean_content) and config.getboolean("Picarto QuickView", "enabled"):
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
                and message.clean_content:  # Make sure message isn't empty
            await self.safe_send_typing(message.channel)
            try:
                member = discord.utils.get(message.server.members, id=self.user.id)
                if member is None:
                    member = self.user
            except AttributeError:
                member = self.user
            clean_message = re.sub("@{}".format(member.display_name), "", message.clean_content)

            ai = None
            try:
                ai = self.apiai.query(clean_message, message.author.id)
            except KeyError:
                pass

            action = ai.action[0]
            if action == "skill":
                skill = ai.action[1]
                if skill == "wiki":
                    query = ai.get_parameter("search_query")
                    wiki = config.get("wiki", "wiki")
                    await self.skill_wiki(message, query=query, wiki=wiki)
                elif skill == "help":
                    await self.skill_help(message)
                elif skill == "role":
                    subskill = ai.action[2]
                    if subskill == "set":
                        desired_role = ai.get_parameter("role")
                        target_user = ai.get_parameter("user", fallback=message.author.name)
                        await self.skill_change_role(message, desired_role=desired_role, target_user=target_user)
                elif skill == "status":
                    await self.skill_status(message)
                elif skill == "reddit":
                    multireddit = ai.get_parameter("multireddit")
                    await self.skill_reddit(message, multireddit=multireddit)
                # elif skill == "moderation":
                #   if subskill == "kick":
                #     await self.skill_kick(message, wit)
            else:
                await self.safe_send_message(message.channel, ai.response)

    async def on_member_join(self, member):
        server = member.server
        config = self.configs.get(server)
        if config.getboolean("auditing", "joins"):
            await self.auditor.audit(server, auditing.MEMBER_JOIN,
                                     "{} joined the server.".format(member.mention), user=member)
        if config.getboolean("welcome", "announce_in_server"):
            await self.safe_send_message(server.default_channel, "Welcome {}!".format(member.mention))
        # if welcomed:
        #     text = self.get_config_message("welcome", member, server)
        #     welcome_embed = discord.Embed(
        #         title="Welcome to {}!".format(server.name),
        #         description=text,
        #         colour=0x4286F4)
        #     await self.safe_send_message(member, embed=welcome_embed)

    async def on_member_remove(self, member):
        server = member.server
        config = self.configs.get(server)
        if config.getboolean("auditing", "leaves"):
            await self.auditor.audit(member.server, auditing.MEMBER_LEAVE,
                                 "{} left the server.".format(member.mention), user=member)
        # invite = self.create_invite(member.server).url
        # await self.safe_send_message(member, "Did you leave {} by accident?
        #                                       Here's a reinvite: {}".format(member.server, invite))

    async def on_reaction_add(self, reaction, user):
        server = reaction.message.server
        config = self.configs.get(server)
        if config.getboolean("auditing", "reactions"):
            await self.auditor.audit(server, auditing.REACTION_ADD,
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
        server = reaction.message.server
        config = self.configs.get(server)
        if config.getboolean("auditing", "reactions"):
            await self.auditor.audit(server, auditing.REACTION_REMOVE,
                                     "{} removed reaction {} from {}".format(user.mention,
                                                                             reaction.emoji, reaction.message.content),
                                     user=user)

    async def on_server_join(self, server):
        self.configs.update({server: serverconfig.Config(server)})
        log.info("{}: Added to server.".format(server))
        self.update_server_count()

    async def on_server_remove(self, server):
        self.configs.pop(server)
        log.info("{}: Removed from server.".format(server))
        self.update_server_count()

    async def on_channel_create(self, channel):
        if channel.name == "glyph":
            embed = discord.Embed(title="Glyph Channel",
                                  description="Congratulations on creating the `glyph` channel!\n"
                                              "This will be used to configure me.\n"
                                              "Click [here](https://glyph-discord.readthedocs.io/"
                                              "en/latest/configuration.html) to get started.")
            await self.safe_send_message(channel, embed=embed)
            log.info("{}: Glyph channel created.".format(channel.server))

    async def on_channel_update(self, before, after):
        server = after.server
        if after.name == "glyph" and not before.topic == after.topic:
            self.configs.update({server: serverconfig.Config(server)})
            config = self.configs.get(server)
            color = 0xFF0000  # Red
            if config.parsing_status == "Okay":
                color = 0x00FF00  # Green
            embed = discord.Embed(title="Configuration Parsing Status",
                                  description=config.parsing_status,
                                  timestamp=datetime.now(), color=color)

            await self.safe_send_message(after, embed=embed)
            log.info("{}: Configuration updated.".format(server))

if __name__ == '__main__':
    bot = GlyphBot()
    bot.run(environ.get("DISCORD_TOKEN"))
