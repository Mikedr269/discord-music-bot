import discord
from discord import FFmpegPCMAudio
import glob
import random
import os
import asyncio
import yt_dlp

TOKEN = "εδω το τοκεν"

# 📂 για να παιζει mp3
# Εδω το μπαινει το path για το mp3 MY_BASE_DIR = " 
# Εδω για να μπορει ο φιλος σας να βαζει την δικια του μουσικη το path FRIEND_BASE_DIR = "

# Ρυθμίσεις για το yt-dlp 
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch', 
    'source_address': '0.0.0.0'
}

# Ρυθμίσεις για να γινεται δουελευει ηρεμα το FFMPEG
FFMPEG_OPTIONS = {
    'executable': 'ffmpeg.exe',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class DJMixas(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          
        intents.voice_states = True     
        intents.message_content = True  
        
        super().__init__(intents=intents)
        self.tracks = []
        self.queue = []
        self.voice = None
        self.current_folder = MY_BASE_DIR 
        self.is_youtube = False 
        self._connect_lock = asyncio.Lock()

    async def on_ready(self):
        print(f"DJ MIXAS online. Έτοιμος για MP3 και YouTube Search!")

    def load_tracks(self):
        self.is_youtube = False
        self.tracks = glob.glob(os.path.join(self.current_folder, "*.mp3"))
        self.queue = [] 

    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        if after.channel is None and before.channel is not None:
            if self.voice and self.voice.channel == before.channel:
                remaining = [m for m in before.channel.members if not m.bot]
                if not remaining:
                    async with self._connect_lock:
                        if self.voice and self.voice.is_connected(): 
                            await self.voice.disconnect()
                        self.voice = None
                        self.tracks = []
                        self.queue = []
                        print("■ Βγήκαν όλοι, αποσυνδέθηκα.")

    async def on_message(self, message):
        if message.author.bot: return
        content = message.content.strip()

        # 1. Εντολή !join (Μπαίνει αθόρυβα)
        if content.lower() == "!join":
            if message.author.voice and message.author.voice.channel:
                channel = message.author.voice.channel
                async with self._connect_lock:
                    if self.voice is None or not self.voice.is_connected():
                        try:
                            self.voice = await channel.connect(timeout=15.0, reconnect=True)
                            print(f"▶ Μπήκα στο κανάλι {channel.name}.")
                        except Exception as e: print(f"❌ Σφάλμα σύνδεσης: {e}")
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

        # 2. Εντολή !leave
        elif content.lower() == "!leave":
            async with self._connect_lock:
                if self.voice and self.voice.is_connected(): await self.voice.disconnect()
                self.voice = None
                self.tracks = []
                self.queue = []
                print("■ Αποσυνδέθηκα.")
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

        # 3. Εντολή !skip
        elif content.lower() == "!skip":
            if self.voice and self.voice.is_playing(): self.voice.stop()
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

        # 4. Εντολή !play [υποφάκελος]
        elif content.lower().startswith("!play "):
            sub_folder = content[6:].strip()
            target_path = os.path.join(MY_BASE_DIR, sub_folder)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                self.current_folder = target_path
                self.load_tracks()
                if self.voice and self.voice.is_playing(): self.voice.stop()
                elif self.voice and self.voice.is_connected(): self.start_playing()
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

        # 5. Εντολή !fplay [υποφάκελος]
        elif content.lower().startswith("!fplay "):
            sub_folder = content[7:].strip()
            target_path = os.path.join(FRIEND_BASE_DIR, sub_folder)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                self.current_folder = target_path
                self.load_tracks()
                if self.voice and self.voice.is_playing(): self.voice.stop()
                elif self.voice and self.voice.is_connected(): self.start_playing()
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

        # 6. ΕΝΤΟΛΗ: !yt [όνομα ή link] (Όπως ήταν στην αρχή)
        elif content.lower().startswith("!yt "):
            search_query = content[4:].strip()
            
            if self.voice and self.voice.is_connected():
                self.is_youtube = True
                loop = asyncio.get_running_loop() # Σωστό loop για να μην κρασάρει
                try:
                    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                        info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
                    
                    if 'entries' in info:
                        if not info['entries']:
                            print("❌ Δεν βρέθηκε κανένα αποτέλεσμα.")
                            return
                        info = info['entries'][0]
                    
                    audio_url = info['url']
                    title = info.get('title', 'YouTube Video')
                    
                    if self.voice.is_playing():
                        self.voice.stop()
                    
                    source = FFmpegPCMAudio(audio_url, before_options=FFMPEG_OPTIONS['before_options'], options=FFMPEG_OPTIONS['options'], executable=FFMPEG_OPTIONS['executable'])
                    self.voice.play(source, after=lambda e: loop.call_soon_threadsafe(self.check_queue_after_yt))
                    print(f" ▶ Παίζει από YouTube: {title}")
                    
                except Exception as e:
                    print(f"❌ Αποτυχία αναπαραγωγής από YouTube: {e}")
            else:
                print("❌ Πρέπει πρώτα να γράψεις !join για να μπει το bot.")
                
            await asyncio.sleep(0.5)
            try: await message.delete()
            except: pass

    def check_queue_after_yt(self):
        self.is_youtube = False
        if self.queue:
            self.play_next()

    def start_playing(self):
        if not self.tracks: return
        if self.voice and self.voice.is_playing(): return
        random.shuffle(self.tracks)
        self.queue = self.tracks[:]
        self.play_next()

    def play_next(self):
        if self.is_youtube: return 
        if not self.voice or not self.voice.is_connected() or not self.tracks: return
        if not self.queue:
            random.shuffle(self.tracks)
            self.queue = self.tracks[:]
            
        track = self.queue.pop(0)
        source = FFmpegPCMAudio(track, executable="ffmpeg.exe")
        loop = asyncio.get_running_loop()
        self.voice.play(source, after=lambda e: loop.call_soon_threadsafe(self.play_next))
        print(f" ▶ Παίζει τώρα: {os.path.basename(track)}")

bot = DJMixas()
bot.run(TOKEN)