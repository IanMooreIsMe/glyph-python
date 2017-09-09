from datetime import datetime
from os import getpid, path

import humanize
import psutil
from discord import Embed

from .commander import register


@register("help")
async def info(bot, message, ai, config):
    help_file = path.join(path.dirname(path.abspath(__file__)), "text/help.txt")
    with open(help_file, "r") as file:
        text = file.read()
    embed = Embed(
        title="Glyph Help",
        description=text,
        colour=0x4286F4)
    await bot.safe_send_message(message.channel, embed=embed)


@register("status")
async def status(bot, message, ai, config):
    def status_embed(ping):
        process = psutil.Process(getpid())
        last_restart_timedelta = datetime.now() - datetime.fromtimestamp(process.create_time())
        last_restart = humanize.naturaltime(last_restart_timedelta)
        servers = humanize.intcomma(bot.total_servers())
        members = humanize.intcomma(bot.total_members())
        messages = len(bot.messages)
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
        embed = Embed(title="Glyph Status", timestamp=datetime.utcfromtimestamp(process.create_time()))
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
    msg = await bot.safe_send_message(message.channel, embed=status_embed("?"))
    diff = int((datetime.now().microsecond - start) / 1000)
    await bot.safe_edit_message(msg, embed=status_embed(diff))
