from _datetime import datetime

import discord
import humanize

from . import serverconfig


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


class Auditor(object):

    def __init__(self, client):
        if not isinstance(client, discord.Client):
            raise ValueError("client must be an instance of class discord.Client")
        self.bot = client

    async def audit(self, server, audit_type, message, *, user):
        if not isinstance(server, discord.Server):
            raise ValueError("server must be an instance of class discord.Server")
        if not isinstance(audit_type, AuditType):
            raise ValueError("type must be an instance of class auditing.AuditType")
        config = serverconfig.Config(server)  # TODO: Use dictionary
        log_channel = discord.utils.get(server.channels, name=config.get("auditing", "channel"))
        if log_channel is not None:
            embed = discord.Embed(title=audit_type.title, description=message,
                                  color=audit_type.color, timestamp=datetime.utcnow())
            embed.set_footer(text="Auditing")
            if user is not None:
                embed.set_thumbnail(url=user.avatar_url)
            await self.bot.safe_send_message(log_channel, embed=embed)
        else:
            glyph_channel = discord.utils.get(server.channels, name="glyph")
            if glyph_channel is not None:
                await self.bot.safe_send_message(glyph_channel,
                                                 "**Config Error**\n```"
                                                 "Auditing channel '{}' not found!```".format(config.get("auditing",
                                                                                                         "channel")))

    @staticmethod
    def get_user_info(member):
        created_at_delta = datetime.utcnow() - member.created_at
        created_at_humanized = humanize.naturaltime(created_at_delta)
        return "**User** {}\n**ID** {}\n**Mention** {}\n**Created** {}\n**Bot** {}".format(
            member, member.id, member.mention, created_at_humanized, member.bot)
