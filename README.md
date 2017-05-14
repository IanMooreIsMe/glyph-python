# Glyph-Discord

This is the source code for a bot that is used on a private, Mass Effect themed, Discord server.  
This bot requires a valid configuration file, environmental variables and wit.ai app.

Setup
---
1. Download the release and extract to your desired folder
2. Edit `config.ini` to match your desires
3. Make environmental variables for `DISCORD_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_USER_AGENT`, `WIT_TOKEN`
4. Create a Discord bot
 1. Go to https://discordapp.com/developers/applications/me
 2. Create a New App (you don't need a Redirect URI)
 3. Make it a Bot User by clicking Create a Bot User
 4. Copy the Token into the environmental variable `DISCORD_TOKEN`
 5. Add the bot to a server using the link https://discordapp.com/api/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0 (replacing CLIENT_ID with the bots Client ID)
5. Create a Reddit App
 1. You must have a reddit account

To Do
---
* Multiserver Support
 * Per-server configurations