import os

import discord
from discord_slash import SlashCommand
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv, find_dotenv
import datetime

load_dotenv(find_dotenv())

# Inject the Access token
with open('tokenfile.txt','r') as f:
    token = f.read()

if (token is None):
    raise RuntimeError('Cannot read token from tokenfile.txt')

# Default channel names

botDesc = '''A bot to filter linked music in one channel, add to another and playback on demand

Supports the following commands
TODO

'''
intents = discord.Intents.default()

bot = commands.Bot(command_prefix='!', description=botDesc, intents=intents)
slash = SlashCommand(bot, override_type = True)

@bot.command()
async def load(ctx: Context, extension):
    bot.load_extension(f'cogs.{extension}')
    await ctx.send("I have upgraded. I am more powerful.")


@bot.command()
async def unload(ctx: Context, extension):
    bot.unload_extension(f'cogs.{extension}')
    await ctx.send("You have weakened me, but I will still win.")


@bot.command()
async def reload(ctx: Context, extension=None):
    if (extension is None):
        extension = 'centralProcessor'
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    # TODO add timestamp
    print('{0}:  ----- Reboot complete ------'.format(datetime.datetime.now()))
    await ctx.send("Reboot complete")

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[0:-3]}')

ListOfCogs = bot.cogs # this is a dictionary!
print(len(ListOfCogs))
    
for NameOfCog,TheClassOfCog in ListOfCogs.items(): # we can loop trough it!
	print(NameOfCog)

bot.run(token)