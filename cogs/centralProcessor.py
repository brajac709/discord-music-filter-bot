import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import musicDatabase as db
import json
import youtube_dl
import sys, io
import asyncio
from async_timeout import timeout
import itertools

listenerChannelName = 'music'
destChannelName = 'music-aggregation'

guild_ids = [832413087092178944]


#copied from https://stackoverflow.com/questions/56060614/how-to-make-a-discord-bot-play-youtube-audio
# TODO separate this into another module probably
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
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
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5, requester):
        super().__init__(source, volume)

        self.data = data
        self.requester = requester

        self.title = data.get('title')
        self.url = data.get('url')
        self.web_url = data.get('webpage_url')

    @classmethod
    async def from_url(cls, ctx, url, *, loop=None, stream=True, playnow=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        if stream and not playnow:
            # store just enough info to retrieve the stream again and queue metadata
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}
        else:
            # TODO not sure why it only plays half the stream
            filename = data['url'] if stream else ytdl.prepare_filename(data) 
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, requester=ctx.author)

    @classmethod
    async def prepare_stream(cls, data, *, loop):
        """ Youtube stream links expire, so prepare the stream"""
        loop = loop or asyncio.get_event_loop()
        if isinstance(data, cls):
            requester = data.requester
            web_url = data.web_url
        else:
            requester = data['requester']
            web_url = data['webpage_url']

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=web_url, download=False))

        # TODO even with this implementation it only plays about a minute of the stream

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)

# END Youtube handler


class MusicPlayer(commands.Cog):
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for 
    different guilds to listen to different playlists simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.play_done_evt = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.music_loop())

    async def music_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.play_done_evt.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.prepare_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.play_done_evt.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.play_done_evt.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))



class Chassis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO use TextDatabase for now.  change to SQL implementation later
        self.database = db.TextDatabase() 

        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

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

    def _afterPlay(self, error):
        self.bot.loop.call_soon_threadsafe(self.next.set)
        if error:
            raise error

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

            player = self.get_player(ctx)

            # If stream is True, source will be a dict which will be used later to regather the stream.
            # TODO stream currently doesn't play the whole stream, not sure why
            # If stream is False, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
            # TODO download cannot add the same song to the playlist twice because the file is locked for download
            #      may need to implement the download at the time the song will be played or something
            source = await YTDLSource.from_url(ctx, music["url"], loop=self.bot.loop, stream=False, playnow=False)

            await player.queue.put(source)

            # ---- old handling - play immediately  ----
            #async with ctx.typing():
            #    musicChannel = ctx.voice_client
            #    if musicChannel:
            #        self.next.clear()
            #        player = await YTDLSource.from_url(ctx, music["url"], loop=self.bot.loop)
            #        musicChannel.play(player, after=self._afterPlay)
            #await ctx.send('Now Playing: {}'.format(player.title))

            #await self.next.wait()
            #await ctx.send(f'Done Playing: {player.title}')
            #await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        """Pause the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send('I am not currently playing anything!')
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(f'**`{ctx.author}`**: Paused the song!')

    @commands.command()
    async def resume(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!', )
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(f'**`{ctx.author}`**: Resumed the song!')

    @commands.command()
    async def skip(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!')

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently connected to voice!')

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('There are currently no more queued songs.')

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @commands.command(name='now_playing', aliases=['current', 'currentsong', 'playing'])
    async def now_playing_(self, ctx):
        """Display information about the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently connected to voice!', )

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send('I am not currently playing anything!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await ctx.send(f'**Now Playing:** `{vc.source.title}` '
                                   f'requested by `{vc.source.requester}`')

    @commands.command()
    async def stop(self, ctx):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!')

        await self.cleanup(ctx.guild)
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

    @cog_ext.cog_slash(name="ERROR", guild_ids=guild_ids)
    async def _testerror(self, ctx: SlashContext):
        await ctx.send("Throwing Error")
        raise Exception(f"Error thrown by user {ctx.author}")

def setup(bot):
    bot.add_cog(Chassis(bot))

