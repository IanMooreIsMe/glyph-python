from os import environ

import discord
import praw
import prawcore
from praw import exceptions


async def reddit_image(bot, message, *, multireddit=None):
    reddit = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                client_secret=environ.get("REDDIT_SECRET"),
                user_agent=environ.get("REDDIT_USER_AGENT"))
    if multireddit is None:
        await bot.safe_send_message(message.channel, "I think you wanted an image from Reddit, "
                                                     "but I'm not sure of what. Sorry.")
        return
    try:
        for subreddit in multireddit.split("+"):
            nswf_subreddit = reddit.subreddit(subreddit).over18
            if nswf_subreddit:
                await bot.safe_send_message(message.channel,
                                            "<:xmark:314349398824058880> "
                                            "I am forbidden to show NSFW content from `{}`.".format(multireddit))
                return
    except prawcore.NotFound:
        pass
    # nswf_channel = False
    # try:
    #     if message.channel.adult:
    #         nswf_channel = True
    # except AttributeError:
    #     pass
    # if nswf_subreddit and not nswf_channel:
    #     await self.safe_send_message(message.channel, "You must be in a NSFW channel "
    #                                                   "to view NSFW images from `{}`".format(multireddit))
    #     return
    try:
        for i in range(1, 20):  # Get an image that can be embedded
            try:
                submission = reddit.subreddit(multireddit).random()
            except TypeError:
                continue
            if any(extension in submission.url for extension in [".png", ".jpg", ".jpeg", ".gif"]) \
                    and submission.score > 10 and not submission.over_18:
                embed = discord.Embed(title=submission.title, url=submission.shortlink)
                embed.set_image(url=submission.url)
                await bot.safe_send_message(message.channel, embed=embed, removable=True)
                break
        else:
            await bot.safe_send_message(message.channel, "Sorry, I took too long to try to find an image.")
    except prawcore.NotFound:
        await bot.safe_send_message(message.channel, "Sorry, I can not find photos for `{}`.".format(multireddit))
    except praw.exceptions.ClientException:
        await bot.safe_send_message(message.channel, "Sorry, I had an issue communicating with Reddit.")
