import os
import subprocess

import discord
from discord_slash import SlashCommand
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv, find_dotenv
import datetime
import sys,io

load_dotenv(find_dotenv())

def setOutput():
    f = open('logfile.txt','a')
    f.seek(0,io.SEEK_END)
    sys.stdout = f
    sys.stderr = f

def resetOutput():
    sys.stdout.close()
    #sys.stderr.close()  # since they're the same file don't close twice???
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

setOutput()

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
    bot.reload_extension(f'cogs.{extension}')
    # TODO add timestamp
    print('{0}:  ----- Reboot complete ------'.format(datetime.datetime.now()))
    await ctx.send("Reboot complete")

@bot.command()
async def pull(ctx: Context):
    print('pulling....')
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print('pull')

# TODO may want this as a slash command instead
@bot.command()
async def dump(ctx: Context):
    sys.stdout.flush()
    sys.stderr.flush()
    f = discord.File('logfile.txt')
    await ctx.send("Here's the log", file=f)

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[0:-3]}')

print('{0} ----- Starting Up ------'.format(datetime.datetime.now()))
ListOfCogs = bot.cogs # this is a dictionary!
print(len(ListOfCogs))
    
for NameOfCog,TheClassOfCog in ListOfCogs.items(): # we can loop trough it!
	print(NameOfCog)

bot.run(token)

resetOutput()