import asyncio
from datetime import datetime

import discord


async def change_role(bot, message, target_user, desired_role, allowed_roles):
    if message.channel.is_private:  # You can't set a role, if you're not in a server
        await bot.safe_send_message(message.channel, "<:xmark:314349398824058880> "
                                                     "You must be in a server to set a role.")
        return
    if not target_user == message.author and not message.author.permissions_in(message.channel).manage_roles:
        await bot.safe_send_message(message.channel,
                                    "You don't have permission to set {}'s role.".format(target_user.name))
        return
    if desired_role is None:
        await bot.safe_send_message(message.channel,
                                    "Sorry, I can not seem to find a desired role in your message.")
        return
    # TODO: Check permissions and improve safe remove and add permissions
    allowed_roles = list(filter(lambda x: x.name.lower() in map(str.lower, allowed_roles), message.server.roles))
    try:
        new_role = list(filter(lambda x: x.name.lower() == desired_role.lower(), message.server.roles))[0]
    except IndexError:
        new_role = None
    if not allowed_roles:
        await bot.safe_send_message(message.channel, "Sorry, but this server has no available roles configured.")
    elif new_role is None or new_role not in allowed_roles:
        await bot.safe_send_message(message.channel,
                                    "Sorry, but `{}` is not an available role.".format(desired_role))
        await bot.skill_list_roles(message, allowed_roles)
    else:
        await bot.safe_remove_roles(target_user, *allowed_roles)  # Remove all old roles
        await asyncio.sleep(.2)  # Wait because of rate limiting
        role_set = await bot.safe_add_roles(target_user, new_role)  # Add the new role
        if role_set:
            role_change_message = "{} you are now a {}!".format(target_user.mention, new_role.mention)
            role_change_embed = discord.Embed(
                title="Poof!", description=role_change_message, colour=0x42F465, timestamp=datetime.now())
            role_change_embed.set_thumbnail(url=target_user.avatar_url)
            role_change_embed.set_footer(text="Roles Skill")
            await bot.safe_send_message(message.channel, embed=role_change_embed)
        else:
            await bot.safe_send_message(message.channel,
                                        "Sorry, I can not assign the role `{}`.".format(desired_role))
            await bot.skill_list_roles(message, allowed_roles)


async def list_roles(bot, message, roles):
    if message.channel.is_private:  # You can't list roles, if you're not in a server
        await bot.safe_send_message(message.channel, "<:xmark:314349398824058880> "
                                                     "You must be in a server to list roles.")
        return
    allowed_roles = list(filter(lambda x: x.name in roles, message.server.roles))
    if not allowed_roles:
        await bot.safe_send_message(message.channel, "Sorry, but {} has no "
                                                     "available roles configured.".format(message.server.name))
    else:
        friendly_available_roles = ""
        for role in allowed_roles:
            friendly_available_roles += ("{}\n".format(role.mention))
        embed = discord.Embed(title="Available Roles",
                              description=friendly_available_roles,
                              timestamp=datetime.now())
        embed.set_footer(text="Roles Skill")
        await bot.safe_send_message(message.channel, embed=embed)
