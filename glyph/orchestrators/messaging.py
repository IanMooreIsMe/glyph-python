import asyncio

import discord


class MessagingOrchestrator:

    __slots__ = ["client", "log", "ledger", "cooldowns", "incompletes"]

    def __init__(self, client, logger):
        self.client = client
        self.log = logger
        self.ledger = {}
        self.cooldowns = {}
        self.incompletes = set()

    async def send_typing(self, message):
        destination = message.channel
        if destination is None:
            self.log.error("Send typing needs a destination!")
            return None
        try:
            await self.client.send_typing(destination)
        except discord.Forbidden:
            self.log.warning("{} - {}: Cannot send typing, no permission?".format(destination.server, destination.name))
        except discord.NotFound:
            self.log.warning("{} - {}: Cannot send typing, invalid channel?".format(destination.server, destination.name))
        except discord.HTTPException:
            self.log.warning("{} - {}: Cannot send typing, failed.".format(destination.server, destination.name))

    async def send(self, message, content=None, *, embed=None, expire_time=0, trigger=None):
        destination = message.channel

        if content is None and embed is None:
            self.log.error("A message needs to have content!")
            return None

        msg = None
        try:
            if message.channel.permissions_for(await self.client.get_self_member(destination)).embed_links:
                msg = await self.client.send_message(message.channel, content, embed=embed)
            elif embed is not None:
                try:
                    tabulated_description = embed.description.replace("\n", "\n\t")
                except AttributeError:
                    tabulated_description = None
                msg = await self.client.send_message(message.channel,
                                                     "**Title** \n\t{}\n**Description** \n\t{}\n**Images** \n\t{}\n\t{}"
                                                     "\n*No embed permission compatibility mode, "
                                                     "please grant embed permission*".format(embed.title,
                                                                                             tabulated_description,
                                                                                             embed.image.url,
                                                                                             embed.thumbnail.url))
            else:
                msg = await self.client.send_message(message.channel, content)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.delete(msg)

            if trigger is not None:
                self.ledger.update({trigger.id: EnhancedMessage(self.client, msg)})

        except discord.Forbidden:
            self.log.warning("{} - {}: Cannot send message, no permission?".format(destination.server, destination.name))
        except discord.NotFound:
            self.log.warning("{} - {}: Cannot send message, invalid channel?".format(destination.server, destination.name))
        except discord.HTTPException:
            self.log.warning("{} - {}: Cannot send message, failed.".format(destination.server, destination.name))

        return msg

    async def edit(self, message, new=None, *, embed=None, expire_time=0, clear_reactions=False):
        if message is None:
            return

        msg = None
        if clear_reactions:
            await self.clear_reactions(message)
        try:
            msg = await self.client.edit_message(message=message, new_content=new, embed=embed)

            if msg and expire_time:
                await asyncio.sleep(expire_time)
                await self.delete(msg)
        except discord.NotFound:
            self.log.warning("Cannot edit message \"{}\", message not found".format(message.clean_content))
        except discord.HTTPException:
            self.log.warning("Cannot edit message \"{}\", failed.".format(message.clean_content))

        return msg

    async def delete(self, message):
        try:
            return await self.client.delete_message(message)
        except discord.Forbidden:
            self.log.warning("Cannot delete message \"{}\", no permission?".format(message.clean_content))
        except discord.NotFound:
            self.log.warning("Cannot delete message \"{}\", invalid channel?".format(message.clean_content))
        except discord.HTTPException:
            self.log.warning("Cannot delete message \"{}\", failed.".format(message.clean_content))

    async def purge(self, channel, *, limit=100, check=None, before=None, after=None, around=None):
        purges = None
        try:
            purges = await self.client.purge_from(channel, limit=limit, check=check, before=before, after=after, around=around)
        except discord.Forbidden:
            self.log.warning("{} - {}: Cannot purge messages, no permission?".format(channel.server, channel.name))
        except discord.NotFound:
            self.log.warning("{} - {}: Cannot purge messages, invalid channel?".format(channel.server, channel.name))
        return purges

    async def add_reaction(self, message, emoji):
        reaction = None
        channel = message.channel
        try:
            reaction = await self.client.add_reaction(message, emoji)
        except discord.Forbidden:
            self.log.warning("{} - {}: Cannot add reaction, no permission?".format(channel.server, channel.name))
        except discord.NotFound:
            self.log.warning("{} - {}: Cannot add reaction, invalid message or emoji?".format(channel.server, channel.name))
        return reaction

    async def clear_reactions(self, message):
        channel = message.channel
        if not channel.is_private:
            try:
                await self.client.clear_reactions(message)
            except discord.Forbidden:
                self.log.warning("{} - {}: Cannot clear reactions, no permission?".format(channel.server, channel.name))


class EnhancedMessage(discord.Message):

    __slots__ = discord.Message.__slots__ + ["client", "clean_mentions", "ai", "config"]

    def __init__(self, client, message):
        super().__init__(reactions=message.reactions)
        self.client = client
        self.clean_mentions = self._get_clean_mentions()
        for slot in message.__slots__:
            if hasattr(message, slot):
                self.__setattr__(slot, getattr(message, slot))

    async def reply(self, content=None, *, embed=None):
        return await self.client.messaging.send(self, content=content, embed=embed, trigger=self)

    async def delete(self):
        await self.client.messaging.delete(self)

    async def edit(self, new=None, *, embed=None, expire_time=0, clear_reactions=False):
        return await self.client.messaging.edit(self, new=new, embed=embed, expire_time=expire_time,
                                                clear_reactions=clear_reactions)

    def _get_clean_mentions(self):
        # Get the member of the bot so the mention can be removed from the message
        try:
            member = discord.utils.get(self.server.members, id=self.client.user.id)
            if member is None:
                member = self.client.user
        except AttributeError:
            member = self.client.user
            # Remove self from the list of mentions in the message
        clean_mentions = self.mentions
        try:
            clean_mentions.remove(member)
        except ValueError:
            pass
        return clean_mentions
