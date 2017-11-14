import asyncio
import logging
import re
from datetime import datetime
from json.decoder import JSONDecodeError
from os import environ

import discord
import requests

from . import apiai, auditing, fa, orchestrators, picarto, skills
from .serverconfig import ConfigDatabase

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class GlyphBot(discord.Client):

    def __init__(self):
        self.auditor = auditing.Auditor(self)
        self.apiai = apiai.AIProcessor(client_access_token=environ.get("APIAI_TOKEN"))
        self.configdb = ConfigDatabase(environ.get("DATABASE_URL"))
        self.messaging = orchestrators.MessagingOrchestrator(self, log)
        self.total_members = lambda: sum(1 for _ in self.get_all_members())
        self.total_servers = lambda: len(self.servers)
        self.ready = False
        self.incompletes = []
        self.skill_commander = skills.SkillCommander()
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

    async def on_ready(self):
        log.info("Logged in as {} ({})".format(self.user.name, self.user.id))
        await self.change_presence(game=discord.Game(name="Armax Arsenal Arena"))
        farm_servers = []
        for server in list(self.servers):
            total_members = len(server.members)
            total_bots = len(list(filter(lambda member: member.bot, server.members)))
            total_humans = total_members - total_bots
            percentage_bots = round(total_bots/total_members*100, 2)
            if percentage_bots > 80 and total_members > 15:
                farm_servers.append(server)
                log.info("{}: Left server! Was {}% likely to be a bot farm with {} members, "
                         "{} humans and {} bots!".format(
                            server.name, percentage_bots, total_members, total_humans, total_bots))
                await asyncio.sleep(2)  # Wait because of rate limiting
                await self.leave_server(server)
        log.info("Left {} bot farm server(s).".format(len(farm_servers)))
        self.configdb.load_all()
        log.info("Loaded {} configurations from the database.".format(len(self.configdb.configs)))
        await self.update_server_count()
        log.info("Connected to {} server(s) with {} members.".format(self.total_servers(), self.total_members()))
        self.ready = True

    async def get_self_member(self, channel):
        try:
            member = discord.utils.get(channel.server.members, id=self.user.id)
            if member is None:
                member = self.user
        except AttributeError:
            member = self.user
        return member

    async def on_message(self, message):
        if not self.ready:
            return
        message = orchestrators.EnhancedMessage(self, message)
        # Don't talk to yourself
        if message.author == self.user or message.author.bot:
            return
        server = message.server
        config = self.configdb.get(server)
        # Check for spoilery words
        if config["spoilers"]["keywords"]:
            spoilers_channel = config["spoilers"]["safe_channel"]
            spoilers_keywords = set(map(lambda x: x.lower(), config["spoilers"]["keywords"]))
            split_message = set(map(str.lower, re.findall(r"[\w']+", message.clean_content)))
            if spoilers_keywords.intersection(split_message) and not (message.channel.name == spoilers_channel):
                await self.messaging.add_reaction(message, "\u26A0")  # React with a warning emoji
        # FA QuickView
        r = fa.Submission.regex
        if r.search(message.clean_content) and config["quickview"]["fa"]["enabled"]:
            links = r.findall(message.clean_content)
            for link in links:
                link_type = link[4]
                link_id = link[5]
                if link_type == "view":
                    try:
                        submission = fa.Submission(id=link_id)
                        embed = submission.get_embed(thumbnail=config["quickview"]["fa"]["thumbnail"])
                        await message.reply(embed=embed)
                    except ValueError:
                        pass
            return
        # Picarto QuickView
        r = picarto.Channel.regex
        if r.search(message.clean_content) and config["quickview"]["picarto"]["enabled"]:
            links = r.findall(message.clean_content)
            for link in links:
                link_name = link[4]
                try:
                    channel = picarto.Channel(name=link_name)
                    embed = channel.get_embed()
                    await message.reply(embed=embed)
                except ValueError:
                    pass
            return
        # Check if the message should be replied to
        if self.user in message.mentions or message.channel.is_private or message.author in self.incompletes:
            # Check cooldowns
            try:
                def cooldown(prop):
                    return self.cooldowns.get(message.author).get(prop)
                if cooldown("time") > datetime.utcnow():
                    if not cooldown("warned"):
                        self.cooldowns.update(
                            {message.author: {"time": cooldown("time"), "warned": True}})
                        remaining = (cooldown("time") - datetime.now()).seconds % 60
                        await message.reply("You are being ratelimited {}! Wait {} seconds.".format(
                            message.author.mention, remaining))
                    return
            except (KeyError, TypeError, AttributeError):
                pass
            # Get the member of the bot so the mention can be removed from the message
            member = await self.get_self_member(message.channel)
            # Check it the mention is at the beginning of the message and don't reply if not
            if not message.clean_content.startswith("@{}".format(member.display_name)) \
                    and not (message.channel.is_private or message.author in self.incompletes):
                return
            # Start by typing to indicate processing a successful message
            await self.messaging.send_typing(message)
            # Remove the mention from the message so it can be processed right
            clean_message = re.sub("@{}".format(member.display_name), "", message.clean_content).strip()
            if not clean_message:  # If there's no message
                await message.reply("You have to say something.")
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
                await message.reply("Sorry, it appears api.ai is currently unavailable.\n Please try again later.")
                return
            # Do the action given by api.ai
            # if ai.action_incomplete:
            #     self.incompletes.add(message.author)
            # else:
            #     self.cooldowns.update(
            #         {message.author: {"time": datetime.utcnow() + timedelta(seconds=4), "warned": False}})
            #     try:
            #         self.incompletes.remove(message.author)
            #     except KeyError:
            #         pass
            await self.skill_commander.process(message, ai, config)

    async def on_member_join(self, member):
        if not self.ready:
            return
        server = member.server
        config = self.configdb.get(server)
        if config["auditing"]["joins"]:
            await self.auditor.audit(server, auditing.MEMBER_JOIN, self.auditor.get_user_info(member), user=member)

    async def on_member_remove(self, member):
        if not self.ready:
            return
        server = member.server
        config = self.configdb.get(server)
        if config["auditing"]["leaves"]:
            await self.auditor.audit(server, auditing.MEMBER_LEAVE, self.auditor.get_user_info(member), user=member)

    async def on_reaction_add(self, reaction, user):
        if not self.ready:
            return
        server = reaction.message.server
        config = self.configdb.get(server)
        message = reaction.message
        if config["auditing"]["reactions"]:
            await self.auditor.audit(server, auditing.REACTION_ADD,
                                     "{} added reaction {} to {}".format(user.mention,
                                                                         reaction.emoji,
                                                                         reaction.message.content),
                                     user=user)

    async def on_reaction_remove(self, reaction, user):
        if not self.ready:
            return
        server = reaction.message.server
        config = self.configdb.get(server)
        if config["auditing"]["reactions"]:
            await self.auditor.audit(server, auditing.REACTION_REMOVE,
                                     "{} removed reaction {} from {}".format(user.mention,
                                                                             reaction.emoji, reaction.message.content),
                                     user=user)

    async def on_message_delete(self, message):
        if not self.ready:
            return
        if message.id in self.messaging.ledger:
            data = self.messaging.ledger.get(message.id)
            self.messaging.ledger.pop(message.id)
            channel = self.get_channel(id=data[0])
            msg = await self.get_message(channel=channel, id=data[1])
            await self.messaging.add_reaction(msg, "\u274C")
            await asyncio.sleep(1)
            await self.messaging.delete(msg)

    async def on_server_join(self, server):
        if not self.ready:
            return
        log.info("{}: Added to server.".format(server))
        await self.update_server_count()

    async def on_server_remove(self, server):
        if not self.ready:
            return
        self.configdb.delete(server.id)
        log.info("{}: Removed from server.".format(server))
        await self.update_server_count()


if __name__ == '__main__':
    bot = GlyphBot()
    bot.run(environ.get("DISCORD_TOKEN"))
