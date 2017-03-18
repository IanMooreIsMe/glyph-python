# Glyph-Discord

This is the source code for a bot that is used on a private, Mass Effect themed, Discord server.  
This bot requires a valid configuration file, environmental varaibles and wit.ai app.

Setup
---
1. Download the release and extract to your desired folder
2. Create a file called `config.ini` and copy in the example below, adding in your own tokens
3. Make environmental variables for `DISCORD_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_USER_AGENT`, `WIT_TOKEN`

Example Config
---
```ini
[discord]
game = Armax Arsenal Arena


[wikia]
wiki = masseffect

[reddit]
meme = me_irl+meirl
catto = thecatdimension+catpictures
doggo = doggos+doge+dogpictures
snek = sneks+snek_irl

[spoilers]
channel = ark
keywords = kett,tempest,ryder,hyperion,nexus,helius,pathfinder,drack,remnant,peebee,liam,cora,kadara,vetra,kallo,angara,archon,jaal,costa

[countdown]
enabled = true
date = 2017-03-21
icon = ark.png
font = masseffect.ttf
size = 47
color = 255,255,86
prefix=
suffix=+2
```
