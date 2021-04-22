import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import musicDatabase as db
import json
import youtube_dl

listenerChannelName = 'music'
destChannelName = 'music-aggregation'

guild_ids = [832413087092178944]


#copied from https://stackoverflow.com/questions/56060614/how-to-make-a-discord-bot-play-youtube-audio
# TODO separate this into another module probably
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
# END Youtube handler



class Chassis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO use TextDatabase for now.  change to SQL implementation later
        self.database = db.TextDatabase() 

    @commands.Cog.listener()
    async def on_ready(self):
        print('Logged in as {0.user}'.format(self.bot))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = self.bot.get_channel(832413087608340480)
        members = channel.members
        if not members:
            print(":'( I'm so lonely")
            # TODO when brady add's a stop method, call it

    @commands.command()
    async def hello(self, ctx):
        """Prints 'Hello' in the channel"""
        await ctx.send('Hello!')

    # TODO make sure download and play, whatever library, are using hardware accelerated transcoding
    @commands.command()
    async def play(self, ctx, *, id):
        print(id)
        music = self.database.searchMusic(id)
        if len(music) == 0:
            return
        music = music[0]

        # Connect to the voice channel and play 
        server = ctx.message.guild
        # grab the 1st one for now.  later may want to join the channel of the author of the command
        voice_channel = server.voice_channels[0] if len(server.voice_channels) > 0 else None

        if voice_channel is None:
            await ctx.send('No valid voice channels')
        else:
            musicChannel = ctx.voice_client
            if musicChannel:
                if (musicChannel.channel.id != voice_channel.id):
                    # not joined yet
                    await musicChannel.move_to(voice_channel)
            else:
                await voice_channel.connect()

            async with ctx.typing():
                musicChannel = ctx.voice_client
                if musicChannel:
                    player = await YTDLSource.from_url(music["url"], loop=self.bot.loop)
                    musicChannel.play(player)
            await ctx.send('Now Playing: {}'.format(player.title))

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await ctx.send("Going dark...")

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
        await ctx.send(content=f"puddi puddi ({self.bot.latency*1000}ms)")

    #@slash.slash(self, name="EXTERMINATE", guild_ids=guild_ids)
    @cog_ext.cog_slash(name="EXTERMINATE", guild_ids=guild_ids)
    async def _exterminate(self, ctx: SlashContext):
        await ctx.send("Ooooh, you got me.")
        await self.bot.close()

def setup(bot):
    bot.add_cog(Chassis(bot))