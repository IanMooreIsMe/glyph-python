# Glyph-Discord

This is the source code for a bot that is used on a private, Mass Effect themed, Discord server.  
This bot requires a valid configuration file, environmental variables and wit.ai app.

Setup
---
1. Download the release and extract to your desired folder
2. Edit `config.ini` to match your desires
3. Make environmental variables for `DISCORD_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_USER_AGENT`, `WIT_TOKEN` (don't ask me how, I'm developing locally in PyCharm and set them there and deploy to Heroku where they are setup nice and easily)
4. Create a Discord bot
 1. Go to https://discordapp.com/developers/applications/me
 2. Create a New App (you don't need a Redirect URI)
 3. Make it a Bot User by clicking Create a Bot User
 4. Copy the Token into the environmental variable `DISCORD_TOKEN`
 5. Add the bot to a server using the link https://discordapp.com/api/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0 (replacing CLIENT_ID with the bots Client ID)
5. Create a Reddit App
 1. You must have a Reddit account, create one if you don't have one
 2. Go to https://www.reddit.com/prefs/apps/
 3. Create another app
  1. Give it a name and a description
  2. Set redirect uri to http://www.example.com/unused/redirect/uri
  3. Create app
 4. Copy secret into the environmental variable `REDDIT_SECRET`
 5. Copy the numbers under "personal use script" into the environmental variable `REDDIT_CLIENT_ID`
 6. Set `REDDIT_USER_AGENT` to something that names the bot and mentions your Reddit username
6. Creating the Wit.ai app
 1. You must have a wit.ai account, create one if you don't have one
 2. Go to https://wit.ai/apps/new
 3. Give the app a name, a short description, and set it to private
 4. Then upload the latest backup included with the release, this is vital as it is configured and trained to work with the bot program
 5. The wit app uses metadata to customize responses such as canned_response and multireddit. Most likely you won't have any need to change. However you may want to change the one under the entity called command for wiki. It is set by default to the masseffect Wikia wiki but you can change it to whichever existing one you like.
 6. You may also have to train in a few user name examples (which have mostly been removed to protect people using the genesis bot)
 7. You may also have to train in the names of cosmetic roles that users can apply on your server (on the server Glyph began on, we use roles to change the color of users to identify them as a specific race)
 8. This wit app is very fresh and still needs work
7. Install the required packages
 1. Start a console in the directory you unpacked the bot in
 2. Run `pip install -r requirements.txt`
8. Run `run.py` and enjoy using Glyph

To Do
-----
* Make a wiki on how to use the bot
* Multiserver Support
 * Per-server configurations