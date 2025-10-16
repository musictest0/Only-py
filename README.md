import os
import subprocess
from highrise import BaseBot, User, Position, CurrencyItem, Item
from highrise.models import GetMessagesRequest
from concurrent.futures import ThreadPoolExecutor
import asyncio
import json
import random
import string
import time
import glob
import yt_dlp as youtube_dl
from datetime import datetime
from economy_admin import handle_economy_admin_commands, handle_vip_confirmation
from highrise import *
from highrise.webapi import *
from highrise.models_webapi import *
from highrise.models import *


# Caminhos dos arquivos para armazenamento persistente
WALLETS_FILE = "wallets.json"  # Carteiras
SETTINGS_FILE = "settings.json"  # Configurações
RANKS_FILE = "ranks.json"  # Ranqueamentos
VIPS_FILE = "vips.json"  # VIPs
LOGS_FILE = "logs.json"  # Logs
HISTORY_FILE = "history.json"  # Histórico
BLOCKED_FILE = "blocked.json"  # Usuários bloqueados
ADMINS_FILE = "admins.json"  # Administradores
OUTFIT_FILE = "outfit.json"  # Roupas
BACKUP_DIR = "backups"  # Diretório de backups

class MyBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.datas_file = "datas.json"
        self.datas = self.load_datas()
        #fav system
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        #ban system
        self.banned_titles = self.load_banned_songs()
        #continuies emotes
        self.file_path = "emote_dict.json"
        self.emote_data = self.load_emotes()
        
        self.dance = None  # Dança atual
        self.current_song = None  # Música atual
        self.song_queue = []  # Fila de músicas
        self.pending_confirmations = {}  # Confirmações pendentes
        self.currently_playing = False  # Indicador de música tocando
        self.skip_event = asyncio.Event()  # Evento para pular música
        self.ffmpeg_process = None  # Processo FFmpeg
        self.currently_playing_title = None  # Título da música atual
        self.wallets = self.load_wallets()  # Carrega carteiras
        self.settings = self.load_settings()  # Carrega configurações
        self.ranks = self.load_ranks()  # Carrega ranqueamentos
        self.vips = self.load_vips()  # Carrega VIPs
        self.logs = self.load_logs()  # Carrega logs
        self.history = self.load_history()  # Carrega histórico
        self.blocked_users = self.load_blocked()  # Carrega usuários bloqueados
        self.user_song_count = {}  # Contagem de músicas por usuário
        self.admins = self.load_admins()  # Carrega administradores
        self.outfit = self.load_outfit()  # Carrega roupas
        self.bot_pos = None  # Posição do bot
        self.ctoggle = False  # Alternância de custo
        self.is_loading = True  # Indicador de carregamento
        self.username_cache = {}  # Cache de nomes de usuário
        self.last_backup_time = time.time()  # Último backup
        self.start_time = time.time()  # Hora de início

    def load_emotes(self):
        """Load emotes from emote_dict.json"""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {self.file_path}: {e}")
            return {}

    def save_emotes(self):
        """Save emote_data to emote_dict.json"""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.emote_data, f, indent=2)
        except Exception as e:
            print(f"Error saving {self.file_path}: {e}")

    
    def save_banned_songs(self):
        with open("banned_songs.json", "w") as f:
            json.dump(list(self.banned_titles), f)

    def load_banned_songs(self):
        if os.path.exists("banned_songs.json"):
            with open("banned_songs.json", "r") as f:
                return set(json.load(f))
        return set()  # Important fallback if file doesn't exist

    
    def load_favorites(self):
        """Load user's favorite songs from the favorites file."""
        try:
            with open(self.favorites_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("[favorites.json] not found. Starting with an empty favorites list.")
            return {}
        except json.JSONDecodeError:
            print("Error decoding favorites.json. Using empty list as fallback.")
            return {}

    async def save_favorites(self):
        """Save the user's favorite songs to the favorites file."""
        async with asyncio.Lock():
            try:
                with open(self.favorites_file, "w") as f:
                    json.dump(self.favorites, f, indent=4)
                await self.backup_file(self.favorites_file)  # Optional: backup support
            except Exception as e:
                print(f"Failed to save favorites.json: {e}")
    
    def load_datas(self):
        try:
            with open(self.datas_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def save_datas(self):
        with open(self.datas_file, "w") as f:
            json.dump(self.datas, f, indent=4)
            
    def load_wallets(self):
        """Carrega as carteiras dos usuários do arquivo JSON."""
        try:
            with open(WALLETS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Error decoding wallets.json. Starting with empty wallets.")
            return {}

    async def save_wallets(self):
        """Salva as carteiras no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(WALLETS_FILE, 'w') as f:
                    json.dump(self.wallets, f, indent=4)
                await self.backup_file(WALLETS_FILE)
            except Exception as e:
                print(f"Error saving wallets: {e}")

    def load_settings(self):
        """Carrega as configurações do bot com valores padrão."""
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except FileNotFoundError:
            settings = {}
        except json.JSONDecodeError:
            print("Error decoding settings.json. Using default settings.")
            settings = {}
        defaults = {
            "play_cost": 5,  # Custo para tocar música
            "max_song_duration": 12,  # Duração máxima da música (minutos)
            "queue_limit_per_user": 3  # Limite de músicas por usuário na fila
        }
        for key, value in defaults.items():
            if key not in settings:
                settings[key] = value
        return settings

    async def save_settings(self):
        """Salva as configurações no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                await self.backup_file(SETTINGS_FILE)
            except Exception as e:
                print(f"Error saving settings: {e}")

    def load_ranks(self):
        """Carrega os ranqueamentos dos usuários."""
        try:
            with open(RANKS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Error decoding ranks.json. Starting with empty rankings.")
            return {}

    async def save_ranks(self):
        """Salva os ranqueamentos no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(RANKS_FILE, 'w') as f:
                    json.dump(self.ranks, f, indent=4)
                await self.backup_file(RANKS_FILE)
            except Exception as e:
                print(f"Error saving rankings: {e}")

    def load_vips(self):
        """Carrega a lista de VIPs e preço do VIP."""
        try:
            with open(VIPS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"vip_price": 100, "vip_users": []}
        except json.JSONDecodeError:
            print("Error decoding vips.json. Starting with default VIP data.")
            return {"vip_price": 100, "vip_users": []}

    async def save_vips(self):
        """Salva a lista de VIPs no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(VIPS_FILE, 'w') as f:
                    json.dump(self.vips, f, indent=4)
                await self.backup_file(VIPS_FILE)
            except Exception as e:
                print(f"Error saving VIPs: {e}")

    def load_logs(self):
        """Carrega os logs de comandos."""
        try:
            with open(LOGS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"settime": [], "setlimit": []}
        except json.JSONDecodeError:
            print("Error decoding logs.json. Starting with empty logs.")
            return {"settime": [], "setlimit": []}

    async def save_logs(self):
        """Salva os logs no arquivo JSON com backup, mantendo até 100 entradas por comando."""
        async with asyncio.Lock():
            try:
                for command in self.logs:
                    if len(self.logs[command]) > 100:
                        self.logs[command] = self.logs[command][-100:]
                with open(LOGS_FILE, 'w') as f:
                    json.dump(self.logs, f, indent=4)
                await self.backup_file(LOGS_FILE)
            except Exception as e:
                print(f"Error saving logs: {e}")

    def load_history(self):
        """Carrega o histórico das últimas 15 músicas tocadas."""
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                return history[-15:] if len(history) > 15 else history
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            print("Error decoding history.json. Starting with empty history.")
            return []

    async def save_history(self):
        """Salva o histórico no arquivo JSON com backup, mantendo até 15 entradas."""
        async with asyncio.Lock():
            try:
                if len(self.history) > 15:
                    self.history = self.history[-15:]
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(self.history, f, indent=4)
                await self.backup_file(HISTORY_FILE)
            except Exception as e:
                print(f"Error saving history: {e}")

    def load_blocked(self):
        """Carrega a lista de usuários bloqueados."""
        try:
            with open(BLOCKED_FILE, 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()
        except json.JSONDecodeError:
            print("Error decoding blocked.json. Starting with empty blocked list.")
            return set()

    async def save_blocked(self):
        """Salva a lista de usuários bloqueados no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(BLOCKED_FILE, 'w') as f:
                    json.dump(list(self.blocked_users), f, indent=4)
                await self.backup_file(BLOCKED_FILE)
            except Exception as e:
                print(f"Error saving blocked users: {e}")

    def load_admins(self):
        """Carrega a lista de administradores."""
        try:
            with open(ADMINS_FILE, "r") as f:
                return set(json.load(f))
        except FileNotFoundError:
            return {"Mr.jawaan"}  # Admin padrão
        except json.JSONDecodeError:
            print("Error decoding admins.json. Starting with default admin.")
            return {"Mr.jawaan"}

    async def save_admins(self):
        """Salva a lista de administradores no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(ADMINS_FILE, "w") as f:
                    json.dump(list(self.admins), f, indent=4)
                await self.backup_file(ADMINS_FILE)
            except Exception as e:
                print(f"Error saving admins: {e}")

    def load_outfit(self):
        """Carrega a configuração de roupas do bot."""
        try:
            with open(OUTFIT_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_outfit()
        except json.JSONDecodeError:
            print("Error decoding outfit.json. Using default outfit.")
            return self.get_default_outfit()

    async def save_outfit(self):
        """Salva a configuração de roupas no arquivo JSON com backup."""
        async with asyncio.Lock():
            try:
                with open(OUTFIT_FILE, 'w') as f:
                    json.dump(self.outfit, f, indent=4)
                await self.backup_file(OUTFIT_FILE)
            except Exception as e:
                print(f"Error saving outfit: {e}")

    def get_default_outfit(self):
        """Define a roupa padrão do bot."""
        shirt = ["shirt-n_weddingbubblegrab2022blackblazershirtopen"]
        pant = ["pants-n_starteritems2019cuffedjeansblack"]
        item_top = random.choice(shirt)
        item_bottom = random.choice(pant)
        return [
            {"type": "clothing", "amount": 1, "id": "body-flesh", "account_bound": False, "active_palette": 1},
            {"type": "clothing", "amount": 1, "id": item_top, "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": item_bottom, "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "hair_back-n_pococorewards2020magicalundercut", "account_bound": False, "active_palette": 1},
            {"type": "clothing", "amount": 1, "id": "nose-n_01", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "hair_front-n_malenew16", "account_bound": False, "active_palette": 1},
            {"type": "clothing", "amount": 1, "id": "freckle-n_registrationavatars2023contour", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "freckle-n_aprilfoolsinvisible2021hiddenface", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "sock-n_starteritems2020whitesocks", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "shoes-n_room12019sneakersblack", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "mouth-n_aprilfoolsinvisible2020mouth", "account_bound": False, "active_palette": -1},
            {"type": "clothing", "amount": 1, "id": "eyebrow-n_basic2018newbrows14", "account_bound": False, "active_palette": -1},
        ]

    async def apply_outfit(self):
        """Aplica a roupa configurada ao bot."""
        try:
            outfit = [Item(**item) for item in self.outfit]
            await self.highrise.set_outfit(outfit=outfit)
            print("Outfit applied successfully.")
        except Exception as e:
            print(f"Error applying outfit: {e}")
            await self.highrise.chat(random.choice([
                "🚫 Oops, something went wrong while changing the look! Shall I try again? ✨",
                "🚫 Couldn't change the outfit! Want to try again? 🎵",
                "🚫 Yikes, the wardrobe got stuck! Should I give it another go? 😅"
            ]))

    async def backup_file(self, file_path):
        """Cria um backup do arquivo especificado com timestamp."""
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            file_name = os.path.basename(file_path)
            backup_path = os.path.join(BACKUP_DIR, f"{file_name.split('.')[0]}_{timestamp}.json")
            with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                json.dump(json.load(src), dst, indent=4)
            backups = sorted(glob.glob(os.path.join(BACKUP_DIR, f"{file_name.split('.')[0]}_*.json")))
            if len(backups) > 24:
                for old_backup in backups[:-24]:
                    os.remove(old_backup)
        except Exception as e:
            print(f"Error creating backup of {file_path}: {e}")

    async def backup_task(self):
        """Tarefa periódica para criar backups a cada hora."""
        while True:
            if time.time() - self.last_backup_time >= 3600:
                for file in [WALLETS_FILE, SETTINGS_FILE, RANKS_FILE, VIPS_FILE, LOGS_FILE, HISTORY_FILE, BLOCKED_FILE, ADMINS_FILE, OUTFIT_FILE, 'song_queue.json', 'current_song.json']:
                    if os.path.exists(file):
                        await self.backup_file(file)
                self.last_backup_time = time.time()
            await asyncio.sleep(60)

    def log_command(self, command: str, user_id: str, details: str, target_user_id: str = None):
        """Registra um comando executado no log."""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "details": details
        }
        if target_user_id:
            log_entry["target_user_id"] = target_user_id
        if command not in self.logs:
            self.logs[command] = []
        self.logs[command].append(log_entry)
        asyncio.create_task(self.save_logs())

    async def get_user_balance(self, user_id: str) -> int:
        """Retorna o saldo de ouro do usuário."""
        return self.wallets.get(user_id, 0)

    async def update_user_balance(self, user_id: str, amount: int):
        """Atualiza o saldo de ouro do usuário."""
        self.wallets[user_id] = self.wallets.get(user_id, 0) + amount
        if self.wallets[user_id] < 0:
            self.wallets[user_id] = 0
        await self.save_wallets()

    async def update_rank(self, user_id: str):
        """Atualiza o ranqueamento do usuário com base nas músicas solicitadas."""
        if user_id not in self.ranks:
            self.ranks[user_id] = {"song_count": 0, "level": 1, "last_daily": None}
        self.ranks[user_id]["song_count"] += 1
        songs = self.ranks[user_id]["song_count"]
        new_level = 1 + (songs // 15)
        if new_level > self.ranks[user_id]["level"]:
            self.ranks[user_id]["level"] = new_level
            usernames = await self.get_user_details([user_id])
            username = usernames.get(user_id, "Unknown User")
            await self.highrise.chat(random.choice([
                f"🎉 Congrats, @{username}! You've reached level {new_level}! Keep shining! ✨",
                f"🎉 @{username}, you leveled up to {new_level}! What a vibe! 🚀",
                f"🎉 Awesome job, @{username}! You're now level {new_level}! Play more! 🎶"
            ]))
        await self.save_ranks()

    def is_vip(self, user_id: str) -> bool:
        """Verifica se o usuário é VIP."""
        return user_id in self.vips.get("vip_users", [])

    async def on_start(self, session_metadata):
        """Executado ao iniciar o bot."""
        try:
            self.queue = []
            self.currently_playing = False

            await self.highrise.chat(random.choice([
            "🎼 MJBots is ready to rock! Loading the rhythm, just a moment! 🔊",
            "🎉 Yo, I'm here! Getting the music ready for the party! 🕺💃",
            "🎤 MJBots in the house! Tuning the speakers, we'll start soon! 🚀"
        ]))

            self.is_loading = True
            print("MJBot is ready and loaded!")
            print("Bot starting... clearing any active stream.")

            self.load_loc_data()
            if self.bot_pos:
                await self.highrise.teleport(self.highrise.my_id, self.bot_pos)

            await self.stop_existing_stream()
            await asyncio.sleep(5)

            self.skip_event.clear()
            self.load_queue()
            self.current_song = self.load_current_song()

            if self.current_song:
                await self.highrise.chat(random.choice([
                f"🔄 Back with the vibe: '{self.current_song['title']}'! Let's enjoy it! 🎶",
                f"🔄 Resuming '{self.current_song['title']}'! Ready for the beat? 🎵",
                f"🔄 Continuing with '{self.current_song['title']}'! Time to dance! ✨"
            ]))
                self.song_queue.insert(0, self.current_song)
                await asyncio.sleep(10)

            self.is_loading = False

            await self.highrise.chat(random.choice([
            "🎉 All set! Use -help to see my commands and start the party! 😎",
            "🎵 Music on! Type -help for commands and let's have fun! 🕺",
            "🚀 MJBots is online! Check commands with -help and play some tunes! 🎧"
        ]))

            if self.song_queue:
                print("Resuming playback of queued songs...")
                await self.play_next_song()

        # Start background tasks
            self.background_tasks = [
            asyncio.create_task(self.backup_task()),
           # asyncio.create_task(self.emote_loop())
        ]

        except Exception as e:
            print(f"❌ [on_start] Error: {e}")
            if "closing transport" in str(e).lower():
                print("🔁 Highrise disconnected at startup. Restarting bot...")
                await self.shutdown_tasks()
                raise SystemExit(1)  # Triggers restart from main.py
            raise

    async def shutdown_tasks(self):
        print("🧹 Shutting down all background tasks...")
        for task in getattr(self, "background_tasks", []):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    print(f"✅ Task {task.get_coro().__name__} cancelled.")
        self.background_tasks.clear()

    
    async def emote_loop(self):
        """Continuously sends random emotes based on duration from emote_dict.json"""
        while True:
            try:
                if not self.emote_data:
                    print("No emotes loaded.")
                    await asyncio.sleep(10)
                    continue

                # Pick a random emote
                emote_info = random.choice(list(self.emote_data.values()))
                emote_id = emote_info.get("id")
                duration = emote_info.get("duration", 5)  # default 5s if missing

                if emote_id:
                    await self.highrise.send_emote(emote_id)
                    print(f"[EMOTE] Sent {emote_info.get('name')} ({emote_id})")
                    await asyncio.sleep(duration + 2)
                else:
                    print("Invalid emote data, skipping.")
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"[emote_loop error]: {e}")
                await asyncio.sleep(5)

    
    def is_admin(self, username):
        """Verifica se o usuário é administrador."""
        return username in self.admins

    async def split_message(self, message: str, max_length: int = 250) -> list:
        """Divide mensagens longas em partes menores."""
        if len(message) <= max_length:
            return [message]
        messages = []
        current = ""
        for line in message.split("\n"):
            if len(current) + len(line) + 1 <= max_length:
                current += line + "\n"
            else:
                if current:
                    messages.append(current.strip())
                current = line + "\n"
        if current:
            messages.append(current.strip())
        return messages

    async def get_user_details(self, user_ids: list) -> dict:
        """Obtém detalhes dos usuários, utilizando cache para otimizar."""
        result = {}
        uncached_ids = [uid for uid in user_ids if uid not in self.username_cache]
        if uncached_ids:
            for uid in uncached_ids:
                try:
                    response = await self.webapi.get_user(uid)
                    if response.user:
                        self.username_cache[uid] = response.user.username
                    else:
                        self.username_cache[uid] = None
                except Exception as e:
                    print(f"Error fetching user details for {uid}: {str(e)}")
                    self.username_cache[uid] = None
        for uid in user_ids:
            result[uid] = self.username_cache.get(uid)
        return result

    async def on_chat(self, user: User, message: str) -> None:
        """Gerencia mensagens no chat da sala."""
        #message = message.lower().strip()
        user_id = user.id

        if message.startswith("-") and user.id not in self.datas:
            await self.highrise.send_whisper(
    user.id,
    f"\n✨ Hello [{user.username}], it looks like your profile setup is incomplete.\n\n"
    "📩 To get started, please send `hi` to [@Bot_agent] in DM and complete your profile setup.\n"
    f"🔁 Once done, you can try `{message}` again to access all features."
            )
            return

        if message.startswith("-equip"):
            await self.equip_item(user, message)

        if message.startswith("-item "):
            parts = message.strip().split(" ", 1)
            if len(parts) < 2:
                await self.highrise.chat("Invalid command")
                return

            item_name = parts[1].strip()
            print(f"Searching item: {item_name}")

            try:
                response = await self.webapi.get_items(item_name=item_name)
                print(response)

                if not response.items:
                    await self.highrise.chat(f"No item found: {item_name}")
                    return

                item = response.items[0]
                name = item.item_name
                item_id = item.item_id
                category = item.category.value
                rarity = item.rarity.value if item.rarity else "Unknown"
                pops_price = item.pops_sale_price if item.pops_sale_price is not None else "N/A"
                tradable = "✅" if item.is_tradable else "❌"
                purchasable = "✅" if item.is_purchasable else "❌"

                first_id = response.first_id
                last_id = response.last_id

                msg = (
            f"🎭 [{name}] -- (ID: {item_id})\n"
            f"📦 Category: {category}\n"
            f"🌟 Rarity: {rarity}\n"
            f"💰 Pops Price: {pops_price}\n"
            f"🔗 Tradable: {tradable} | 🛒 Purchasable: {purchasable}\n"
            f"📄 First ID: {first_id}\n"
            f"📄 Last ID: {last_id}"
        )
                await self.send_private_message(user, msg)

            except Exception as e:
                await self.highrise.chat(f"Error in item: {e}")

        # Gerencia confirmação de VIP
        if message.startswith('-confirm vip '):
            if user_id in self.pending_confirmations:
                response = message[len('-confirm vip '):].strip()
                if response in ['yes', 'y', 'no', 'n']:
                    await handle_vip_confirmation(self, user_id, None, response)
                else:
                    await self.highrise.chat(random.choice([
                        f"🚫 @{user.username}, use -confirm vip yes or -confirm vip no! 📜",
                        f"🚫 @{user.username}, invalid response! Try -confirm vip yes/no! ✨",
                        f"🚫 @{user.username}, wrong command! Use -confirm vip yes or no! 😎"
                    ]))
            else:
                await self.highrise.chat(random.choice([
                    f"🚫 @{user.username}, no pending VIP purchase! Use -buy vip first! 📜",
                    f"🚫 @{user.username}, nothing to confirm! Try -buy vip! ✨",
                    f"🚫 @{user.username}, no VIP request pending! Start with -buy vip! 😎"
                ]))
            return

        if message == '-fit 1' and self.is_admin(user.username):
            self.outfit = self.get_default_outfit()
            await self.apply_outfit()
            await self.save_outfit()
            self.log_command("fit", user_id, "Applied default outfit")
            await self.highrise.chat(random.choice([
        f"👗 @{user.username}, MJBots is rocking a new look! Default style on point! ✨",
        f"👗 @{user.username}, default outfit activated! MJBots looks stylish! 🎵",
        f"👗 @{user.username}, default style applied! Pure elegance! 😎"
    ]))
            return

        if message == '-help':
            help_message = (
        "🎵 Welcome to MJBots, your virtual DJ! Check out the available commands: 🎶\n\n"
        "🎧 -help music     - Commands to pick and enjoy music\n"
        "💰 -help economy   - Manage your gold and VIP status\n"
        "🔧 -help admin     - Exclusive functions for admins\n\n"
        "✨ Quick commands:\n"
        "  💸 -balance - Check your gold balance\n"
        "  📜 -profile - View your level and requested songs\n"
        "  🎁 -daily   - Earn free gold daily\n\n"
        "🔥 Type -help <category> for more details and let's party! 🎉"
    )
            for msg in await self.split_message(help_message):
                await self.send_private_message(user, msg)
                await asyncio.sleep(0.5)
                
        elif message == '-help music':
            music_help_message = (
    "🎶 Commands to liven up the room with music! 🎵\n\n"
    "🎸 -play <song>              - Choose a song to play\n"
    "   Ex.: -play Bohemian Rhapsody\n"
    "🎁 -play @user <song>     - Dedicate a song to someone\n"
    "   Ex.: -play @Friend Happy Birthday\n"
    f"   Cost: {self.settings['play_cost']} gold (free for VIPs)\n\n"
    "⏭️ -skip                    - Skip the current song (owner or admin)\n"
    "🗑️ -delq                    - Remove your last song from the queue\n"
    "📋 -q                       - View the song queue\n"
    "   Ex.: -q 2 (for page 2)\n"
    "🎧 -np                      - See the currently playing song\n"
    "📜 -history                 - View the last 15 played songs\n"
    "🏆 -rank                    - Check the request ranking\n\n"
    "💖 Favorites System:\n"
    "⭐ -fav                     - Add current song to your favorites\n"
    "📂 -my fav                  - View your favorite songs list\n"
    "▶️ -playfav [number]          - Play a song from your favorites\n"
    "❌ -removefav [number]        - Remove a song from your favorites\n"
    f"   Limit: 20 songs (VIPs: 40 songs)\n\n"
    f"ℹ️ Limit: {self.settings['queue_limit_per_user']} songs per person\n"
    f"⏱️ Max duration: {self.settings['max_song_duration']} minutes"
            )
            for msg in await self.split_message(music_help_message):
                await self.send_private_message(user, msg)
                await asyncio.sleep(0.5)

        elif message.startswith('-play '):
            try:
                if self.is_loading:
                    await self.highrise.chat(random.choice([
                "🎵 Hold on, I'm tuning the speakers! Try again soon! 🔄",
                "🎵 Loading the vibe, just a sec! Try again in a bit! ✨",
                "🎵 Getting the sound ready! Wait a moment and try again! 🎶"
            ]))
                    return

                if user_id in self.blocked_users:
                    await self.highrise.chat(random.choice([
                f"🚫 @{user.username}, you're blocked from song requests. Contact an admin! 😔",
                f"🚫 @{user.username}, song requests are blocked for you. Reach out to an admin! 🎵",
                f"🚫 @{user.username}, you can't request songs now. Talk to the admins! ✨"
            ]))
                    return

                parts = message[len('-play '):].strip().split(' ', 1)
                if len(parts) < 1 or not parts[0]:
                    await self.highrise.chat(random.choice([
                "🎶 Oops, you forgot the song! Use: -play <song> or -play @user <song> 🎵",
                "🎶 Whoa, where's the song? Try: -play <song> or -play @user <song> ✨",
                "🎶 Hmm, didn't catch that! Type: -play <song> or -play @user <song> 😎"
            ]))
                    return

                target_username = None
                song_request = None

                if parts[0].startswith('@') and len(parts) > 1:
                    target_username = parts[0][1:]
                    song_request = parts[1].strip()
                    if not song_request:
                        await self.highrise.chat(random.choice([
                    "🎁 Forgot the song to dedicate! Use: -play @user <song> 🎶",
                    "🎁 Oops, no song specified! Try: -play @user <song> ✨",
                    "🎁 Dedication without a song? Type: -play @user <song> 😎"
                ]))
                        return

                    room_users = await self.highrise.get_room_users()
                    target_user = None
                    for room_user, _ in room_users.content:
                        if room_user.username.lower() == target_username.lower():
                            target_user = room_user
                            target_username = room_user.username
                            break
                    if not target_user:
                        await self.highrise.chat(random.choice([
                    f"😕 @{target_username} isn't in the room! Try another or just the song! 🎵",
                    f"😕 Couldn't find @{target_username} here! Pick another or request a song! ✨",
                    f"😕 @{target_username} is missing! Dedicate to someone else or just the song! 😎"
                ]))
                        return
                else:
                    song_request = message[len('-play '):].strip()

                if self.user_song_count.get(user.username, 0) >= self.settings["queue_limit_per_user"]:
                    await self.highrise.chat(random.choice([
                f"🚧 @{user.username}, you already have {self.settings['queue_limit_per_user']} songs in the queue! Wait for one to play! 🎶",
                f"🚧 @{user.username}, you've hit the limit of {self.settings['queue_limit_per_user']} songs! Hang tight! ✨",
                f"🚧 @{user.username}, that's {self.settings['queue_limit_per_user']} requests from you! Hold on, it'll play soon! 😎"
            ]))
                    return

                if self.ctoggle and not self.is_vip(user_id):
                    play_cost = self.settings.get("play_cost", 5)
                    user_balance = await self.get_user_balance(user.id)
                    if user_balance < play_cost:
                        await self.highrise.chat(random.choice([
                    f"💸 @{user.username}, you need {play_cost} gold to play! Balance: {user_balance}. Try -daily or donate! 🎵",
                    f"💸 @{user.username}, you're short {play_cost} gold! Balance: {user_balance}. Use -daily or support the bot! ✨",
                    f"💸 @{user.username}, your {user_balance} gold doesn't cover the {play_cost} needed! Try -daily! 😎"
                ]))
                        return
                    await self.process_play_payment(user, play_cost)

                await self.add_to_queue(song_request, user.username, dedicated_to=target_username)
    
            except Exception as e:
                await self.highrise.chat("❌ An unexpected error occurred during the song request. Please try again.")
                print(f"Error in -play command: {e}")
                traceback.print_exc()
                
        elif message.startswith("-playfav "):
            parts = message.split(" ", 1)
            if len(parts) < 2 or not parts[1].isdigit():
                await self.highrise.chat(f"▶️ Usage: -playfav <number> (Check with -favorites)")
                return

            index = int(parts[1]) - 1
            user_id = user.id
            if user_id not in self.favorites or index >= len(self.favorites[user_id]["songs"]):
                await self.highrise.chat(f"📛 @{user.username}, invalid favorite number!")
                return

            song = self.favorites[user_id]["songs"][index]
            await self.add_to_queue(song['title'], user.username)

        elif message.startswith("-removefav "):
            parts = message.split(" ", 1)
            if len(parts) < 2 or not parts[1].isdigit():
                await self.highrise.chat(f"🗑 Usage: -removefav <number>")
                return

            index = int(parts[1]) - 1
            user_id = user.id
            if user_id not in self.favorites or index >= len(self.favorites[user_id]["songs"]):
                await self.highrise.send_whisper(user.id, f"🚫 @{user.username}, no such favorite song at #{index+1}!")
                return

            removed = self.favorites[user_id]["songs"].pop(index)
            await self.save_favorites()
            await self.highrise.send_whisper(user.id, f"🗑 @{user.username}, removed '{removed['title']}' from favorites.")

        elif message.strip() == "-fav":
            try:
                if not self.current_song:
                    await self.highrise.chat(f"🎵 @{user.username}, no song is currently playing!")
                    return

                song = self.current_song.copy()
                song_entry = {
            "title": song["title"],
            "url": song.get("url", "N/A"),
            "owner": song.get("owner", "Unknown")
        }

                user_id = user.id
                if user_id not in self.favorites:
                    self.favorites[user_id] = {"username": user.username, "songs": []}

                if any(s["title"].lower() == song_entry["title"].lower() for s in self.favorites[user_id]["songs"]):
                    await self.highrise.chat(f"⭐ @{user.username}, '{song_entry['title']}' is already in your favorites!")
                    return

                is_vip = user_id in self.vips.get("vip_users", [])
                limit = 40 if is_vip else 20
                if len(self.favorites[user_id]["songs"]) >= limit:
                    await self.highrise.chat(f"🚫 @{user.username}, you reached your favorite song limit ({limit}). Remove some with `-removefav <number>`.")
                    return

                self.favorites[user_id]["songs"].append(song_entry)
                await self.save_favorites()
                await self.highrise.chat(f"⭐ @{user.username}, added '{song_entry['title']}' to your favorites!")

            except Exception as e:
                print(f"Error in -fav command: {e}")
                await self.highrise.chat(f"⚠️ Error: {e}")

        
        elif message.strip() == "-my fav":
            user_id = user.id
            if user_id not in self.favorites or not self.favorites[user_id]["songs"]:
                await self.highrise.send_whisper(user.id, f"📂 @{user.username}, you don't have any favorite songs yet!")
                return

            favs = self.favorites[user_id]["songs"]
            message_chunks = []
            chunk = f"🎶 [@{user.username}] Favorite Songs:\n"

            for i, song in enumerate(favs, 1):
                line = f"{i}. {song['title']} by {song.get('owner', 'Unknown')}\n"
                if len(chunk + line) > 900:
                    message_chunks.append(chunk.strip())
                    chunk = line
                else:
                    chunk += line

            if chunk.strip():
                message_chunks.append(chunk.strip())

            for msg in message_chunks:
                await self.send_private_mes
