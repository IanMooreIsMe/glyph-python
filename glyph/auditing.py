import discord
import time


class AuditType(object):

    def __init__(self, message, color):
        self.title = message
        self.color = color


MEMBER_JOIN = AuditType("Member Joined", 0x41E254)
MEMBER_LEAVE = AuditType("Member Left", 0xBA3737)
MESSAGE_DELETE = AuditType("Message Deleted", 0xBA3737)
REACTION_ADD = AuditType("Reaction Added", 0x41E254)
REACTION_REMOVE = AuditType("Reaction Removed", 0xBA3737)
STATUS = AuditType("Bot Status", 0x929392)


class Logger(object):

    def __init__(self, client):
        if not isinstance(client, discord.Client):
            raise ValueError("client must be an instance of class discord.Client")
        self.bot = client

    async def log(self, server, audit, message, *, user):
        if user is None:
            user = self.bot
        log_channel = "log"
        if not isinstance(server, discord.Server):
            raise ValueError("server must be an instance of class discord.Server")
        if not isinstance(audit, AuditType):
            raise ValueError("type must be an instance of class modlogger.Type")
        for channel in server.channels:
            if channel.name == log_channel:
                embed = discord.Embed(title=str(user),
                                      description=message,
                                      color=audit.color)
                embed.set_footer(text=time.strftime("On %Y-%m-%d at %H:%M:%S"))
                if user is not None:
                    embed.set_author(name=audit.title, icon_url=user.avatar_url)
                await self.bot.safe_send_message(channel, embed=embed)
