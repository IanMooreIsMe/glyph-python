import discord
import wikia

async def wiki(bot, message, *, wiki=None, query=None):
    if wiki is None:
        await bot.safe_send_message(message.channel, "Sorry, no valid wiki is set.", expire_time=5)
        return
    if query is None:
        await bot.safe_send_message(message.channel, "Sorry, I couldn't find a search query.", expire_time=5)
        return
    try:
        search = wikia.search(wiki, query)
        page = wikia.page(wiki, search[0])
        url = page.url.replace(" ", "_")
        embed = discord.Embed(title=page.title, url=url, description=page.summary)
        try:
            embed.set_thumbnail(url=page.images[0])
        except (IndexError, AttributeError):
            pass
        await bot.safe_send_message(message.channel, embed=embed, removable=True)
    except (ValueError, wikia.wikia.WikiaError):
        await bot.safe_send_message(message.channel,
                                    "Sorry, I have no information for your search query `{}`.".format(query))
