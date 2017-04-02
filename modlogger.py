import discord
import time


class Type(object):

    def __init__(self, message, color):
        self.message = message
        self.color = color


MEMBER_JOIN = Type("Member Joined", 0x41E254)
MEMBER_LEAVE = Type("Member Left", 0xBA3737)
MESSAGE_DELETE = Type("Message Deleted", 0xBA3737)
REACTION_ADD = Type("Reaction Added", 0x41E254)
REACTION_REMOVE = Type("Reaction Removed", 0xBA3737)
STATUS = Type("Bot Status", 0x929392)


class Logger(object):

    def __init__(self, client, log_channel):
        if not isinstance(client, discord.Client):
            raise ValueError("client must be an instance of class discord.Client")
        self.bot = client
        self.log_channel_name = log_channel

    async def log(self, server, type, message, *, user=None):
        if not isinstance(server, discord.Server):
            raise ValueError("server must be an instance of class discord.Server")
        if not isinstance(type, Type):
            raise ValueError("type must be an instance of class modlogger.Type")
        for channel in server.channels:
            if channel.name == self.log_channel_name:
                embed = discord.Embed(title=type.message,
                                      description=message,
                                      color=type.color)
                embed.set_footer(text=time.strftime("%Y-%m-%d %H:%M:%S"))
                if user is not None:
                    embed.set_author(name=user.name, icon_url=user.avatar_url)
                await self.bot.safe_send_message(channel, embed=embed)
