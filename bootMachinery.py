import os

import discord
from discord_slash import SlashCommand
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Inject the Access token
with open('tokenfile.txt','r') as f:
    token = f.read()

if (token is None):
    raise RuntimeError('Cannot read token from tokenfile.txt')

# Default channel names
listenerChannelName = 'music'
destChannelName = 'music-aggregation'

botDesc = '''A bot to filter linked music in one channel, add to another and playback on demand

Supports the following commands
TODO

'''
intents = discord.Intents.default()

bot = commands.Bot(command_prefix='!', description=botDesc, intents=intents)
slash = SlashCommand(bot, sync_commands=True)

@bot.command()
async def load(ctx: Context, extension):
    bot.load_extension(f'cogs.{extension}')
    await ctx.send("I have upgraded. I am more powerful.")


@bot.command()
async def unload(ctx: Context, extension):
    bot.unload_extension(f'cogs.{extension}')
    await ctx.send("You have weakened me, but I will still win.")


@bot.command()
async def reload(ctx: Context, extension):
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    await ctx.send("Reboot complete")



bot.run(token)