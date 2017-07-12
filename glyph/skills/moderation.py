import re
from datetime import datetime, timedelta

import discord
import humanize


async def purge(bot, message, duration):
    channel = message.channel
    if not message.author.permissions_in(channel).manage_messages and not message.channel.is_private:
        await bot.safe_send_message(channel, "You don't have permission to purge messages!")
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
                              description="<:xmark:314349398824058880> "
                                          "You can only bulk delete messages that are under 14 days old.",
                              timestamp=datetime.now())
        embed.set_footer(text="Moderation Skill | Try asking \"purge 14d\"")
        await bot.safe_send_message(channel, embed=embed)
        return
    embed = discord.Embed(title="Purging",
                          description="<:empty:314349398723264512> "
                                      "Purging everything since ~{}.".format(humanize.naturaltime(time)),
                          timestamp=datetime.now())
    embed.set_footer(text="Moderation Skill")
    status = await bot.safe_send_message(channel, embed=embed)
    deleted = await bot.safe_purge_from(channel, limit=5000, after=time, check=lambda msg: msg.id != status.id)
    if deleted:
        embed = discord.Embed(title="Purge Successful",
                              description="<:check:314349398811475968> "
                                          "Purged {} messages from ~{}.".format(len(deleted), humanize.naturaltime(time)),
                              timestamp=datetime.now())
        embed.set_footer(text="Moderation Skill")
        await bot.safe_edit_message(status, embed=embed)
    else:
        embed = discord.Embed(title="Purge Failed",
                              description="<:xmark:314349398824058880> I don't have Manage Messages permission!",
                              timestamp=datetime.now())
        embed.set_footer(text="Moderation Skill | Try granting Manage Messages to Glyph")
        await bot.safe_edit_message(status, embed=embed)
    return
