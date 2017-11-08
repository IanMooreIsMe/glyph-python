import asyncio
import random
from datetime import datetime

import discord

from .commander import register


@register("role.set")
async def change_role(message):
    desired_role = message.ai.get_parameter("role")
    selectable_roles = message.config["roles"]["selectable"]
    try:
        target_user = message.clean_mentions[0]
    except IndexError:
        target_user = message.author
    if message.channel.is_private:  # You can't set a role, if you're not in a server
        await message.reply("<:xmark:344316007164149770> You must be in a server to set a role.")
        return
    if not target_user == message.author and not message.author.permissions_in(message.channel).manage_roles:
        await message.reply("You don't have permission to set {}'s role.".format(target_user.name))
        return
    if desired_role is None:
        await message.reply("Sorry, I can not seem to find a desired role in your message.")
        return
    # TODO: Check permissions and improve safe remove and add permissions
    allowed_roles = list(filter(lambda x: x.name.lower() in map(str.lower, selectable_roles), message.server.roles))
    try:
        new_role = list(filter(lambda x: x.name.lower() == desired_role.lower(), message.server.roles))[0]
    except IndexError:
        new_role = None
    if not allowed_roles:
        await message.reply("Sorry, but this server has no available roles configured.")
    elif new_role is None or new_role not in allowed_roles:
        await message.reply("Sorry, but `{}` is not an available role.".format(desired_role))
        # await list_roles(bot, message, allowed_roles)  # TODO: Fix
    else:
        await message.client.safe_remove_roles(target_user, *allowed_roles)  # Remove all old roles
        await asyncio.sleep(.2)  # Wait because of rate limiting
        role_set = await message.client.safe_add_roles(target_user, new_role)  # Add the new role
        if role_set:
            role_change_message = "{} you are now a {}!".format(target_user.name, new_role.name)
            role_change_embed = discord.Embed(
                title="Poof!", description=role_change_message, colour=0x42F465, timestamp=datetime.now())
            role_change_embed.set_thumbnail(url=target_user.avatar_url)
            role_change_embed.set_footer(text="Roles Skill")
            await message.reply(embed=role_change_embed)
        else:
            await message.reply("Sorry, I can not assign the role `{}`.".format(desired_role))
            # await list_roles(bot, message, allowed_roles)


@register("role.list")
async def list_roles(message):
    selectable_roles = message.config["roles"]["selectable"]
    if message.channel.is_private:  # You can't list roles, if you're not in a server
        await message.reply("<:xmark:344316007164149770> You must be in a server to list roles.")
        return
    allowed_roles = list(filter(lambda x: x.name in selectable_roles, message.server.roles))
    if not allowed_roles:
        await message.reply("Sorry, but {} has no available roles configured.".format(message.server.name))
    else:
        friendly_available_roles = ""
        for role in allowed_roles:
            friendly_available_roles += ("**{}** - {}\n".format(role.name, role.mention))
        embed = discord.Embed(title="Available Roles",
                              description=friendly_available_roles,
                              timestamp=datetime.utcnow())
        try_role = random.choice(allowed_roles)
        embed.set_footer(text="Roles Skill | Try asking \"Set me as {}\"".format(try_role))
        await message.reply(embed=embed)
