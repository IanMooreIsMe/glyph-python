def server_only(func):
    def wrap(message):
        if message.channel.is_private:
            return message.reply("You can't do this in a PM!")
        else:
            return func(message)
    return wrap


def admin_only(func):
    def wrap(message):
        if not message.author.server_permissions.administrator:
            return message.reply(message.channel, "You can't do this, you don't have permission `administrator`!")
        else:
            return func(message)
    return wrap
