import logging

_skills = {}

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


class SkillCommander(object):

    def __init__(self, client):
        self.client = client
        # self.reddit = reddit.RedditSkill(bot)
        self.skills = {}

    async def process(self, message, ai, config):
        action = ai.get_action_depth(0)
        if "ignore" in str(ai.contexts) and not ai.get_action_depth(1) == "insult":  # If ignoring the user
            await self.client.messaging.reply(message, f"No {message.author.mention}, I'm done helping you for now.")
        elif action == "skill" and not ai.action_incomplete:  # If not ignoring the user and no follow up intent
            skill = ai.get_skill()
            try:
                message.__setattr__("ai", ai)
                message.__setattr__("config", config)
                await _skills[skill](message)
            except KeyError:
                await self.client.messaging.reply(message,
                                                  f"<:confusablob:341765305711722496> "
                                                  f"Odd, you seem to have triggered `{skill}`, "
                                                  f"a skill that isn't currently available.")
        else:
            await message.reply(ai.response)


def register(action):
    def dec(func):
        _skills.update({action: func})
        log.info("Registered {}".format(action))
    return dec
