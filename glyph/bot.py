import asyncio
import logging
import re
from datetime import datetime
from json.decoder import JSONDecodeError
from os import environ, getpid

import discord
import humanize
import psutil
import requests

from . import apiai
from . import auditing
from . import fa
from . import picarto
from . import serverconfig
from . import skills
from .haste import HasteBin

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class GlyphBot(discord.Client):

    def __init__(self):
        self.auditor = auditing.Auditor(self)
        self.apiai = apiai.AIProcessor(client_access_token=environ.get("APIAI_TOKEN"))
        self.langBot = apiai.AIProcessor(client_access_token="1f342872c2d64e54ae303078576531b1")  # client
        self.configs = {None: serverconfig.Config()}  # Set up for DMs
        self.farm_servers = []
        self.removable_messages = []
        self.total_members = lambda: sum(1 for i in self.get_all_members())
        self.total_servers = lambda: len(self.servers)
        super().__init__()

    async def update_server_count(self):
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
        elif embed is not None and removable and not expire_time:
            if embed.footer.text is not discord.Embed.Empty:
                embed.set_footer(text="React \u274C to remove | {}".format(embed.footer.text))
            else:
                embed.set_footer(text="React \u274C to remove")
        msg = None
        try:
            msg = await self.send_message(destination, content, embed=embed)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.delete_message(msg)
            elif msg and removable:
                self.removable_messages.append(msg.id)
        except discord.Forbidden:
            log.warning("{} - {}: Cannot send message, no permission?".format(destination.server, destination.name))
        except discord.NotFound:
            log.warning("{} - {}: Cannot send message, invalid channel?".format(destination.server, destination.name))

        return msg

    async def safe_edit_message(self, message, new=None, *,
                                embed=None, expire_time=0, clear_reactions=False, removable=False):
        if message is None:
            return
        elif embed is not None and removable and not expire_time:
            if embed.footer.text is not discord.Embed.Empty:
                embed.set_footer(text="React \u274C to remove | {}".format(embed.footer.text))
            else:
                embed.set_footer(text="React \u274C to remove")
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
                await self.delete_message(msg)
            elif msg and removable:
                self.removable_messages.append(msg.id)
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

    async def safe_purge_from(self, channel, *, limit=100, check=None, before=None, after=None, around=None):
        dels = None
        try:
            dels = await self.purge_from(channel, limit=limit, check=check, before=before, after=after, around=around)
        except discord.Forbidden:
            log.warning("{} - {}: Cannot purge messages, no permission?".format(channel.server, channel.name))
        except discord.NotFound:
            log.warning("{} - {}: Cannot purge messages, invalid channel?".format(channel.server, channel.name))

        return dels

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
            await self.add_roles(member, *roles)
            return True
        except discord.Forbidden:
            log.warning("{}: Cannot add roles, no permission?".format(member.server))
            return False

    async def safe_remove_roles(self, member, *roles):
        try:
            await self.remove_roles(member, *roles)
            return True
        except discord.Forbidden:
            log.warning("{}: Cannot remove roles, no permission?".format(member.server))
            return False

    async def skill_status(self, message):
        def status_embed(ping):
            process = psutil.Process(getpid())
            last_restart_timedelta = datetime.now() - datetime.fromtimestamp(process.create_time())
            last_restart = humanize.naturaltime(last_restart_timedelta)
            servers = humanize.intcomma(self.total_servers())
            members = humanize.intcomma(self.total_members())
            messages = len(self.messages)
            memory = psutil.virtual_memory()
            memory_total = humanize.naturalsize(memory.total)
            memory_used = humanize.naturalsize(memory.used)
            memory_percent = memory.percent
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent()
            disk_total = humanize.naturalsize(psutil.disk_usage("/").total)
            disk_used = humanize.naturalsize(psutil.disk_usage("/").used)
            disk_percent = psutil.disk_usage("/").percent
            uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            embed = discord.Embed(title="Glyph Status", timestamp=datetime.utcfromtimestamp(process.create_time()))
            embed.add_field(name="Discord Info",
                            value="**Ping** {} ms\n**Servers** {}\n**Members** {}\n"
                                  "**Messages** {}".format(ping, servers, members, messages))
            embed.add_field(name="Stack Info",
                            value="**Memory** {}/{} ({}%)\n**CPU** {}-cores at {}% utilization\n"
                                  "**Disk** {}/{} ({}%)\n**Uptime** {} days".format(
                                memory_used, memory_total, memory_percent, cpu_count, cpu_percent,
                                disk_used, disk_total, disk_percent, uptime.days))
            embed.set_footer(text="Last restarted {}".format(last_restart))
            return embed
        start = datetime.now().microsecond
        msg = await self.safe_send_message(message.channel, embed=status_embed("?"))
        diff = int((datetime.now().microsecond - start)/1000)
        await self.safe_edit_message(msg, embed=status_embed(diff))

    async def skill_help(self, message):
        embed = discord.Embed(
            title="Glyph Help",
            description=self.get_config_message("help", message.author, message.server),
            colour=0x4286F4)
        await self.safe_send_message(message.channel, embed=embed)

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
        for server in list(self.servers):
            self.configs.update({server: serverconfig.Config(server)})
            total_members = len(server.members)
            total_bots = len(list(filter(lambda member: member.bot, server.members)))
            total_humans = total_members - total_bots
            percentage_bots = round(total_bots/total_members*100, 2)
            if percentage_bots > 80 and total_members > 15:
                self.farm_servers.append(server)
                log.info("{}: Left server! Was {}% likely to be a bot farm with {} members, "
                         "{} humans and {} bots!".format(
                            server.name, percentage_bots, total_members, total_humans, total_bots))
                await asyncio.sleep(2)  # Wait because of rate limiting
                await self.leave_server(server)
        log.info("Left {} bot farm server(s).".format(len(self.farm_servers)))
        await self.update_server_count()
        log.info("Connected to {} server(s) with {} members.".format(self.total_servers(), self.total_members()))

    async def on_message(self, message):
        # Don't talk to yourself
        if message.author == self.user or message.author.bot:
            return
        server = message.server
        config = self.configs.get(server, False)
        if not config:
            self.configs.update({server: serverconfig.Config(server)})
            config = self.configs.get(server)
        # Submit data to langBot
        if config.getboolean("langBot", "enabled"):
            try:
                self.langBot.query(message.clean_content, message.author.id)
            except (JSONDecodeError, KeyError):
                pass
        # Check for spoilery words
        if config.getboolean("spoilers", "enabled"):
            spoilers_channel = config.get("spoilers", "channel")
            spoilers_keywords = set(config.getlist("spoilers", "keywords"))
            split_message = set(map(str.lower, re.findall(r"[\w']+", message.clean_content)))
            if spoilers_keywords.intersection(split_message) and not (message.channel.name == spoilers_channel):
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
            return
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
            return
        # Check if the message should be replied to
        if self.user in message.mentions or message.channel.is_private:
            # Get the member of the bot so the mention can be removed from the message
            try:
                member = discord.utils.get(message.server.members, id=self.user.id)
                if member is None:
                    member = self.user
            except AttributeError:
                member = self.user
            # Check it the mention is at the beginning of the message and don't reply if not
            if not message.clean_content.startswith("@{}".format(member.display_name)) and not message.channel.is_private:
                return
            # Start by typing to indicate processing a successful message
            await self.safe_send_typing(message.channel)
            # Remove the mention from the message so it can be processed right
            clean_message = re.sub("@{}".format(member.display_name), "", message.clean_content).strip()
            if not clean_message:  # If there's no message
                await self.safe_send_message(message.channel, "You have to say something.")
                return
            # Remove self from the list of mentions in the message
            clean_mentions = message.mentions
            try:
                clean_mentions.remove(member)
            except ValueError:
                pass
            # Ask api.ai how to handle the message
            try:
                ai = self.apiai.query(clean_message, message.author.id)
            except JSONDecodeError:  # api.ai is down
                await self.safe_send_message(message.channel, "Sorry, it appears api.ai is currently unavailable.\n"
                                                              "Please try again later.")
                return
            # Do the action given by api.ai
            action = ai.get_action_depth(0)
            if "ignore" in str(ai.contexts) and not ai.get_action_depth(1) == "insult":  # If ignoring the user
                await self.safe_send_message(message.channel,
                                             "No {}, I'm done helping you for now.".format(message.author.mention))
            elif action == "skill" and not ai.action_incomplete:  # If not ignoring the user and no follow up intent
                skill = ai.get_action_depth(1)
                subskill = ai.get_action_depth(2)
                if skill == "wiki":
                    query = ai.get_parameter("search_query")
                    wiki = config.get("wiki", "wiki")
                    await skills.wiki(self, message, query=query, wiki=wiki)
                elif skill == "help":
                    await self.skill_help(message)
                elif skill == "role":
                    allowed_roles = config.getlist("roles", "allowed")
                    if subskill == "set":
                        desired_role = ai.get_parameter("role")
                        try:
                            target_user = clean_mentions[0]
                        except IndexError:
                            target_user = message.author
                        await skills.change_role(self, message, target_user, desired_role, allowed_roles)
                    elif subskill == "list":
                        await skills.list_roles(self, message, allowed_roles)
                elif skill == "status":
                    await self.skill_status(message)
                elif skill == "reddit":
                    multireddit = ai.get_parameter("multireddit")
                    await skills.RedditSkill(self).send_image(message, multireddit=multireddit)
                elif skill == "time":
                    timezone = ai.get_parameter("timezone")
                    embed = skills.get_time_embed(timezone)
                    await self.safe_send_message(message.channel, embed=embed)
                elif skill == "moderation":
                    if subskill == "kick":
                        try:
                            target_user = clean_mentions[0]
                        except IndexError:
                            await self.safe_send_message(message.channel, "Sorry, can't find a user to kick.")
                            return
                        await self.skill_kick(message, target_user)
                    elif subskill == "purge":
                        await skills.purge(self, message, ai.get_parameter("text_time"))
            else:
                await self.safe_send_message(message.channel, ai.response)

    async def on_member_join(self, member):
        server = member.server
        config = self.configs.get(server)
        if config.getboolean("auditing", "joins"):
            await self.auditor.audit(server, auditing.MEMBER_JOIN, self.auditor.get_user_info(member), user=member)
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
            await self.auditor.audit(server, auditing.MEMBER_LEAVE, self.auditor.get_user_info(member), user=member)
        # invite = self.create_invite(member.server).url
        # await self.safe_send_message(member, "Did you leave {} by accident?
        #                                       Here's a reinvite: {}".format(member.server, invite))

    async def on_reaction_add(self, reaction, user):
        server = reaction.message.server
        config = self.configs.get(server)
        message = reaction.message
        if config.getboolean("auditing", "reactions"):
            await self.auditor.audit(server, auditing.REACTION_ADD,
                                     "{} added reaction {} to {}".format(user.mention,
                                                                         reaction.emoji,
                                                                         reaction.message.content),
                                     user=user)
        if message.id in self.removable_messages and reaction.emoji == "\u274C":
            embed = discord.Embed(description="<:xmark:314349398824058880> Removed!", color=0xFF0000)
            await self.safe_edit_message(message, embed=embed, expire_time=5, clear_reactions=True)
            self.removable_messages.remove(message.id)
        # removable = False
        # is_fa_quickview = False
        # if not reaction.message.author == self.user:
        #     return
        # try:
        #     removable = ("React \u274C to delete this." in str(message.embeds[0]))
        #     is_fa_quickview = ("React \U0001F48C to receive full size image in a DM." in str(message.embeds[0]))
        # except IndexError:
        #     pass
        # if reaction.emoji == "\u274C" and removable:
        #     embed = discord.Embed(description=":x: Removed!", color=0xFF0000)
        #     await self.safe_edit_message(reaction.message, embed=embed, expire_time=5, clear_reactions=True)
        # elif reaction.emoji == "\U0001F48C" and is_fa_quickview:
        #     try:
        #         embed = message.embeds[0]
        #         submission = fa.Submission(url=embed['url'])
        #         embed = discord.Embed(title=submission.title, url=submission.link, colour=submission.color)
        #         embed.set_footer(text="React \u274C to delete this.")
        #         embed.set_image(url=submission.download)
        #         await self.safe_send_message(user, embed=embed)
        #     except ValueError:
        #         await self.safe_send_message(user, "Sorry, I failed to get the full sized image for you.")

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
        await self.update_server_count()

    async def on_server_remove(self, server):
        if server in self.farm_servers:
            return
        self.configs.pop(server)
        log.info("{}: Removed from server.".format(server))
        await self.update_server_count()

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
            # diff = difflib.unified_diff(before.topic.splitlines(1), after.topic.splitlines(1))
            # diff_string = "".join(diff)
            embed = discord.Embed(title="Configuration Updated", timestamp=datetime.utcnow(), color=color)
            embed.add_field(name="Parsing Status", value=config.parsing_status)
            embed.add_field(name="Previous", value=HasteBin(before.topic).post())
            # embed.add_field(name="Changes", value=diff_string) TODO: Make more understandable
            embed.set_footer(text="Configuration")
            await self.safe_send_message(after, embed=embed)
            log.info("{}: Configuration updated.".format(server))

if __name__ == '__main__':
    bot = GlyphBot()
    bot.run(environ.get("DISCORD_TOKEN"))
