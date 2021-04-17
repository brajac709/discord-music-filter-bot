import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import musicDatabase as db
import json

listenerChannelName = 'music'
destChannelName = 'music-aggregation'

guild_ids = [832413087092178944]

class Chassis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO use TextDatabase for now.  change to SQL implementation later
        self.database = db.TextDatabase() 

    @commands.Cog.listener()
    async def on_ready(self):
        print('Logged in as {0.user}'.format(self.bot))

    @commands.command()
    async def hello(self, ctx):
        """Prints 'Hello' in the channel"""
        await ctx.send('Hello!')

    def is_music_message(self, message):
        return len(message.embeds) > 0  or len(message.attachments) > 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        #  TODO there might be a better way to handle this in the Bot class - investigate
        if message.channel.name != listenerChannelName:
            return

        if self.is_music_message(message):
            destChannel = discord.utils.get(message.guild.channels, name=destChannelName)
            if destChannel is None:
                # TODO maybe just create the channel?
                await message.channel.send("ERROR: could not find channel " + destChannelName)
            else:
                embed = message.embeds[0] if (len(message.embeds) > 0) else None
                # for now support single file attachment
                attachment = message.attachments[0] if (len(message.attachments)) else None
                fil = await attachment.to_file() if attachment is not None else None

                # It seems to be be better to let Discord add the embed automatically for links... 
                # maybe ther's a better way to copy it. For now only support file attachments
                #await destChannel.send(content=message.content, embed=message.embeds[0], file=fil)
                await destChannel.send(content=message.content, file=fil)
                #TODO for now text database only supports urls, not attachments
                if (embed is not None):
                    self.database.addMusic(embed.title, embed.url)
                await destChannel.send("You're some music, alright!")

    #@slash.slash(self, name="pingu", guild_ids=guild_ids)
    @cog_ext.cog_slash(name="pingu", guild_ids=guild_ids)
    async def _pingu(self, ctx: SlashContext):
        await ctx.send(content=f"Pew pew pew! I'm firin my command! ({self.bot.latency*1000}ms)")

    #@slash.slash(self, name="EXTERMINATE", guild_ids=guild_ids)
    @cog_ext.cog_slash(name="EXTERMINATE", guild_ids=guild_ids)
    async def _exterminate(self, ctx: SlashContext):
        await ctx.send("Ooooh, you got me.")
        await self.bot.close()

def setup(bot):
    bot.add_cog(Chassis(bot))