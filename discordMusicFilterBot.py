import discord
from discord.ext import commands
from discord_slash import SlashCommand

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
slash = SlashCommand(bot, sync_commands=True)

guild_ids = [832413087092178944]

@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))

@bot.command()
async def hello(ctx):
    """Prints 'Hello' in the channel"""
    await ctx.send('Hello!')

def is_music_message(message):
    return len(message.embeds) > 0  or len(message.attachments) > 0

async def on_message(message):
    if message.author == bot.user:
        return

    if is_music_message(message):
       # TODO Do stuff to it
        await message.channel.send("You're some music, alright!")

bot.add_listener(on_message, 'on_message')

@slash.slash(name="pingu", guild_ids=guild_ids)
async def _pingu(ctx):
    await ctx.send(f"Pew pew pew! I'm firin my command! ({client.latency*1000}ms)")
    
bot.run(token)
