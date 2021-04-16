import discord

with open('tokenfile.txt','r') as f:
    token = f.read()

if (token is None):
    raise RuntimeError('Cannot read token from tokenfile.txt')


client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

client.run(token)
