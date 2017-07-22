from os import environ

import discord
import praw
import prawcore
from praw import exceptions


class RedditSkill(object):

    def __init__(self, bot):
        self.bot = bot
        self.r = praw.Reddit(client_id=environ.get("REDDIT_CLIENT_ID"),
                             client_secret=environ.get("REDDIT_SECRET"),
                             user_agent=environ.get("REDDIT_USER_AGENT"))

    async def send_image(self, message, *, multireddit=None):

        if multireddit is None:
            await self.bot.safe_send_message(message.channel, "I think you wanted an image from Reddit, "
                                                              "but I'm not sure of what. Sorry.")
            return
        try:
            nsfw_subreddit = [s for s in multireddit.split("+") if self.r.subreddit(s).over18]
        except prawcore.NotFound or prawcore.Redirect:
            await self.bot.safe_send_message(message.channel, "You provided an unknown or invalid subreddit name.")
            return
        try:
            nswf_channel = "nsfw" in message.channel.name
        except TypeError:
            nswf_channel = False
        if nsfw_subreddit and not nswf_channel:
            await self.bot.safe_send_message(message.channel, "You must be in a NSFW channel "
                                                              "to view images from `{}`".format(multireddit))
            return
        try:
            for i in range(1, 20):  # Get an image that can be embedded
                try:
                    submission = self.r.subreddit(multireddit).random()
                except TypeError:
                    continue
                if submission.over_18 and not nswf_channel:
                    continue
                elif any(extension in submission.url for extension in [".png", ".jpg", ".jpeg", ".gif"]) \
                        and submission.score > 10:
                    embed = discord.Embed(title=submission.title, url=submission.shortlink)
                    embed.set_image(url=submission.url)
                    try_subreddit = self.r.subreddit("popular").random().subreddit.display_name
                    embed.set_footer(text="Try asking \"r/{}\"".format(try_subreddit))
                    await self.bot.safe_send_message(message.channel, embed=embed, removable=True)
                    break
            else:
                await self.bot.safe_send_message(message.channel, "Sorry, I took too long to try to find an image.")
        except prawcore.NotFound:
            await self.bot.safe_send_message(message.channel, "Sorry, I can not find photos for `{}`.".format(multireddit))
        except praw.exceptions.ClientException:
            await self.bot.safe_send_message(message.channel, "Sorry, I had an issue communicating with Reddit.")
