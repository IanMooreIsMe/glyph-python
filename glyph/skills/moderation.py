import re
from datetime import datetime, timedelta

import discord
import humanize

from . import utils
from .commander import register


@register("moderation.purge")
async def purge(message):
    duration = message.ai.get_parameter("text_time")
    channel = message.channel
    if not message.author.permissions_in(channel).manage_messages and not channel.is_private:
        await message.reply("You don't have permission to purge messages!")
        return
    if channel.is_private:
        await message.reply("Sorry, I can not purge messages in a DM")
        return

    def text_to_time(text):
        secondsr = re.compile(r"(\d+)(?:\s|)(?:s|sec|second)(?:\b|s)", re.IGNORECASE)
        minutesr = re.compile(r"(\d+)(?:\s|)(?:m|min|minute)(?:\b|s)", re.IGNORECASE)
        hoursr = re.compile(r"(\d+)(?:\s|)(?:h|hour)(?:\b|s)", re.IGNORECASE)
        daysr = re.compile(r"(\d+)(?:\s|)(?:d|day)(?:\b|s)", re.IGNORECASE)
        weeksr = re.compile(r"(\d+)(?:\s|)(?:w|week)(?:\b|s)", re.IGNORECASE)
        try:
            seconds = int(secondsr.match(text).group(1))
        except AttributeError:
            seconds = 0
        try:
            minutes = int(minutesr.match(text).group(1))
        except AttributeError:
            minutes = 0
        try:
            hours = int(hoursr.match(text).group(1))
        except AttributeError:
            hours = 0
        try:
            days = int(daysr.match(text).group(1))
        except AttributeError:
            days = 0
        try:
            weeks = int(weeksr.match(text).group(1))
        except AttributeError:
            weeks = 0
        delta = timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours, weeks=weeks)
        time = datetime.now() - delta
        return time, delta
    time, delta = text_to_time(duration)
    if delta.days > 14:
        embed = discord.Embed(title="Purge Failed",
                              description="<:xmark:344316007164149770> "
                                          "You can only bulk delete messages that are under 14 days old.",
                              timestamp=datetime.utcnow())
        embed.set_footer(text="Moderation | Try asking \"purge 14d\"")
        await message.reply(embed=embed)
        return
    embed = discord.Embed(title="Purging",
                          description="<:empty:344316006438797314> "
                                      "Purging everything since {}.".format(humanize.naturaltime(time)),
                          timestamp=datetime.utcnow())
    embed.set_footer(text="Moderation")
    status = await message.reply(embed=embed)
    deleted = await message.client.messaging.purge_from(channel, limit=100000, after=time,
                                                   check=lambda msg: msg.id != status.id)
    if deleted:
        embed = discord.Embed(title="Purge Successful",
                              description="<:check:344316006040338434> "
                                          "Purged {} messages since {}.".format(len(deleted), humanize.naturaltime(time)),
                              timestamp=datetime.utcnow())
        embed.set_footer(text="Moderation")
        await message.client.safe_edit_message(status, embed=embed)
    else:
        embed = discord.Embed(title="Purge Failed",
                              description="<:xmark:344316007164149770> Either I was given an invalid duration or "
                                          "I don't have Manage Messages permission!",
                              timestamp=datetime.utcnow())
        embed.set_footer(text="Moderation")
        await message.client.messaging.edit_message(status, embed=embed)
    return


@register("moderation.user_info")
async def user_info(message):
    try:
        member = message.clean_mentions[0]
    except IndexError:
        member = message.author
    embed = discord.Embed(title="User Info",
                          description=message.client.auditor.get_user_info(member),
                          timestamp=datetime.utcnow())
    embed.set_thumbnail(url=member.avatar_url)
    embed.set_footer(text="Moderation")
    await message.reply(embed=embed)


@register("moderation.kick")
async def kick(bot, message, ai, config):  # Not finished!
    try:
        member = bot.get_clean_mentions(message)[0]
    except IndexError:
        await bot.safe_send_message(message.channel, "Sorry, can't find a user to kick.")
        return
    if message.channel.is_private:
        await bot.safe_send_message(message.channel, "You have to be in a server to kick someone.")
        return
    elif not message.author.server_permissions.kick_members:
        await bot.safe_send_message(message.channel, "You don't have permission to do kick people.")
        return
    # Get the user
    if member is None:
        try:
            member = discord.utils.get(message.server.members, name=ai["entities"]["user"][0]["value"])
        except KeyError:
            await bot.safe_send_message(message.channel, "Sorry, I couldn't find a user to kick.")
            return
    # Kick the user
    kick = await bot.safe_kick(member)
    if kick:
        await bot.safe_send_message(message.channel, ":ok_hand: ***{} has been kicked!***".format(member.mention))


@register("configuration.load")
@utils.server_only
@utils.admin_only
async def load_config(message):
    haste_regex = re.compile(r"hastebin.com\/(\w{10})")
    try:
        haste = haste_regex.search(ai.get_parameter("url"))
        result = message.client.configdb.inhaste(message.server, haste.group(1))
        if result == "Success!":
            embed = discord.Embed(title="Configuration Update Success",
                                  description="Successfully updated this servers configuration!",
                                  color=0x00FF00,
                                  timestamp=datetime.utcnow())
        else:
            embed = discord.Embed(title="Configuration Update Failure",
                                  description="This servers configuration failed to update for "
                                              "the following reason(s)! Please check that you have "
                                              "a properly formatted JSON and the data is "
                                              "as expected.```{}```\n"
                                              "**Help:** "
                                              "[Documentation]"
                                              "(https://glyph-discord.readthedocs.io"
                                              "/en/latest/configuration.html) - "
                                              "[Official Glyph Server]"
                                              "(https://discord.me/glyph-discord)".format(
                                      result),
                                  color=0xFF0000,
                                  timestamp=datetime.utcnow())
        embed.set_footer(text="Configuration")
        await message.reply(embed=embed)
    except KeyError:
        await message.reply("Sorry, but that url is wrong for me to load a info from.")


@register("configuration.view")
@utils.server_only
@utils.admin_only
async def view_config(message):
    embed = discord.Embed(title="Configuration Viewer",
                          description="Here's the current info: {}\n"
                                      "**Help:** "
                                      "[Documentation]"
                                      "(https://glyph-discord.readthedocs.io"
                                      "/en/latest/configuration.html) "
                                      "- [Official Glyph Server]"
                                      "(https://discord.me/glyph-discord)".format(
                                        message.client.configdb.outhaste(message.server)),
                          timestamp=datetime.utcnow())
    await message.reply(embed=embed)
