import discord
from discord.ext import commands

with open('tokenfile.txt','r') as f:
    token = f.read()

if (token is None):
    raise RuntimeError('Cannot read token from tokenfile.txt')

botDesc = '''A bot to filter linked music in one channel, add to another and playback on demand

Supports the following commands
TODO

'''

intents = discord.Intents.default()

bot = commands.Bot(command_prefix='!', description=botDesc, intents=intents)


@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))

@bot.command()
async def hello(ctx):
    """Prints 'Hello' in the channel"""
    await ctx.send('Hello!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if is_music_message(message):
        # TODO Do stuff to it
        await ctx.send("You're some music, alright!")

def is_music_message(message):
    return len(message.embeds) > 0  or len(message.attachments) > 0

bot.run(token)
