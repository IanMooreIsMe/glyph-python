def server_only(func):
    def wrap(bot, message, ai, config):
        if message.channel.is_private:
            return bot.safe_send_message(message.channel, "You can't do this in a PM!")
        else:
            return func(bot, message, ai, config)
    return wrap


def admin_only(func):
    def wrap(bot, message, ai, config):
        if not message.author.server_permissions.administrator:
            return bot.safe_send_message(message.channel,
                                         "You can't do this, you don't have permission `administrator`!")
        else:
            return func(bot, message, ai, config)
    return wrap
