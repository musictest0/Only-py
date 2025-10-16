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
                await self.send_private_message(user, msg)

        elif message.strip() == "-banlist" and self.is_admin(user.username):
            if not self.banned_titles:
                await self.highrise.chat("📭 No songs are currently banned.")
                return

            banned_list = list(self.banned_titles)
            items_per_page = 10
            total = len(banned_list)
            pages = (total + items_per_page - 1) // items_per_page

            for page in range(pages):
                start = page * items_per_page
                end = start + items_per_page
                chunk = banned_list[start:end]
                chunk_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(chunk, start=start)])

                await self.send_private_message(user, f"🚫 Banned Songs ({start+1}-{min(end, total)} of {total}):\n{chunk_text}")
                await asyncio.sleep(1.5)

        elif message.startswith("-ban ") and self.is_admin(user.username):
    # Only allow -ban with a space, so it doesn't overlap with -banlist
            try:
                if not self.current_song:
                    await self.highrise.chat(f"🎵 @{user.username}, no song is currently playing to ban!")
                    return

                banned_title = self.current_song["title"].strip().lower()

                if banned_title in self.banned_titles:
                    await self.highrise.chat(f"🚫 @{user.username}, '{self.current_song['title']}' is already banned.")
                    return

                self.banned_titles.add(banned_title)
                self.save_banned_songs()
                await self.highrise.chat(f"🚫 [@{user.username}], BANNED '{self.current_song['title']}' from being played again!")
                # 🔄 Auto-skip just like -skip command
                await self.skip_song(user)  # ← Reuses your existing skip logic
            except Exception as e:
                await self.highrise.chat(f"⚠️ Ban failed: {e}")
                
        elif message.startswith("-unban ") and self.is_admin(user.username):
            parts = message.split(" ", 1)
            if len(parts) < 2 or not parts[1].isdigit():
                await self.highrise.chat("⚠️ Use: -unban <number>. Check list with -banlist")
                return

            index = int(parts[1]) - 1
            banned_list = list(self.banned_titles)

            if index < 0 or index >= len(banned_list):
                await self.highrise.chat("❌ Invalid unban number.")
                return

            removed = banned_list.pop(index)
            self.banned_titles = set(banned_list)  # update the set
            self.save_banned_songs()
            await self.highrise.send_whisper(user.id, f"✅ Unbanned: '{removed}'")
        
        elif message.startswith('-skip'):
            await self.skip_song(user)

        elif message.startswith('-delq'):
            parts = message.split()
            if len(parts) == 1:
                await self.del_last_song(user.username)

        elif message.startswith('-clearq') and self.is_admin(user.username):
            parts = message.split()
            if len(parts) == 1:
                await self.clear_queue()

        elif message.startswith('-q'):
            await self.check_queue(user)
            
        elif message.startswith('-np'):
            await self.now_playing(user)

        elif message.startswith('-history'):
            await self.show_history(user)

        elif message.startswith('-rank'):
            if not self.ranks:
                await self.highrise.chat(random.choice([
                    "🏆 No rankings yet! Request some songs to get on the list! 🎵",
                    "🏆 No rankings available! Let's play some music to build the list! ✨",
                    "🏆 Rankings are empty for now! Play a song and join the game! 😎"
                ]))
                return
            user_ids = list(self.ranks.keys())
            usernames = await self.get_user_details(user_ids)
            ranking = []
            for uid in user_ids:
                if usernames.get(uid):
                    song_count = self.ranks[uid].get("song_count", 0)
                    ranking.append((uid, usernames[uid], song_count))
            ranking.sort(key=lambda x: (-x[2], x[1].lower()))
            top_5 = ranking[:5]
            leaderboard_message = "🏆 Top DJs of MJBots! 🎧\n\n"
            for index, (_, username, song_count) in enumerate(top_5, 1):
                leaderboard_message += f"{index}. @{username}: {song_count} songs 🎶\n"
            user_position = None
            user_song_count = self.ranks.get(user_id, {"song_count": 0})["song_count"]
            for index, (uid, username, song_count) in enumerate(ranking, 1):
                if uid == user_id:
                    user_position = index
                    break
            if user_position:
                leaderboard_message += f"\n📍 You're in {user_position}th place with {user_song_count} songs! 🚀"
            else:
                leaderboard_message += "\n📍 You haven't requested any songs yet. Want to join the ranking? 🎵"
            for msg in await self.split_message(leaderboard_message):
                await self.send_private_message(user, msg)
                await asyncio.sleep(0.5)

        else:
            try:
                await handle_economy_admin_commands(self, user, message)
            except Exception as e:
                print(f"Error executing handle_economy_admin_commands: {e}")
                await self.highrise.chat(random.choice([
                    "🚫 Oops, something went wrong with the command! Try again! 🎵",
                    "🚫 Yikes, the command failed! Can you try again? ✨",
                    "🚫 Hmm, that command didn't work! Give it another shot! 😎"
                ]))

    async def on_message(self, user_id: str, conversation_id: str, is_new_conversation: bool) -> None:
        """Handles private messages (DMs)."""
        try:
            # Check if user is already saved
            if user_id in self.datas:
                saved_convo_id = self.datas[user_id].get("conversation_id", None)
                if saved_convo_id != conversation_id:
                    # Update only if conversation_id is different
                    print(f"🔄 Updating conversation ID for {self.datas[user_id]['username']} from {saved_convo_id} → {conversation_id}")
                    self.datas[user_id]["conversation_id"] = conversation_id
                    self.save_datas()
                    print(f"✅ Successfully updated conversation ID.")
            else:
                # If user is not saved, proceed to get their message and save them
                response = await self.highrise.get_messages(conversation_id)
                print(f"Received response: {response}")

                if isinstance(response, GetMessagesRequest.GetMessagesResponse) and response.messages:
                    message = response.messages[0].content
                    print(f"Received message: {message}")

                    user_response = await self.webapi.get_user(user_id)
                    if hasattr(user_response, 'user'):
                        username = user_response.user.username
                        print(f"👤 New user detected: {username} (ID: {user_id})")

                        # Save new user
                        self.datas[user_id] = {
                            "username": username,
                            "conversation_id": conversation_id,
                            "subscribe": True
                        }
                        self.save_datas()
                        print(f"✅ New user saved with conversation ID.")

                        # Send welcome message
                        welcome_msg = (
                            f"🎉 Welcome, [{username}]! Your profile is now set up.\n\n"
                            "🚀 You now have access to all commands. Type `!help` in room chat to get started!"
                        )
                        await self.highrise.send_message(conversation_id, welcome_msg)

            # Handle commands
            response = await self.highrise.get_messages(conversation_id)
            if isinstance(response, GetMessagesRequest.GetMessagesResponse):
                message = response.messages[0].content.lower().strip()
            else:
                return

            if message.startswith('-play '):
                if self.is_loading:
                    await self.highrise.send_message(conversation_id, random.choice([
                        "🎵 Hold on, I'm getting the sound ready! Try again soon! 🔄",
                        "🎵 Loading the vibe, just a moment! Try again in a bit! ✨",
                        "🎵 Tuning the speakers! Wait a second and try again! 🎶"
                    ]))
                    return

                if user_id in self.blocked_users:
                    await self.highrise.send_message(conversation_id, random.choice([
                        "🚫 You're blocked from song requests! Contact an admin! 😢",
                        "🚫 Song requests are blocked for you! Reach out to an admin! 🎵",
                        "🚫 You can't request songs now! Talk to the admins! ✨"
                    ]))
                    return

                username = (await self.get_user_details([user_id])).get(user_id)
                if not username:
                    await self.highrise.send_message(conversation_id, random.choice([
                        "😕 Couldn't find your name! Try in the room chat! 🎶",
                        "😕 Oops, your name didn't show up! Please use the room chat! ✨",
                        "😕 Hmm, couldn't find your user! Try in the main chat! 😎"
                    ]))
                    return

                song_request = message[len('-play '):].strip()
                if self.user_song_count.get(username, 0) >= self.settings["queue_limit_per_user"]:
                    await self.highrise.send_message(conversation_id, random.choice([
                        f"🚧 @{username}, you already have {self.settings['queue_limit_per_user']} songs in the queue! Wait for one to play! 🎶",
                        f"🚧 @{username}, you've hit the limit of {self.settings['queue_limit_per_user']} songs! Hang tight! ✨",
                        f"🚧 @{username}, that's {self.settings['queue_limit_per_user']} requests from you! Hold on, it'll play soon! 😎"
                    ]))
                    return

                if self.ctoggle and not self.is_vip(user_id):
                    play_cost = self.settings.get("play_cost", 5)
                    user_balance = await self.get_user_balance(user_id)
                    if user_balance < play_cost:
                        await self.highrise.send_message(conversation_id, random.choice([
                            f"💸 You need {play_cost} gold to play! Balance: {user_balance}. Try -daily or donate! 🎵",
                            f"💸 You're short {play_cost} gold! Balance: {user_balance}. Use -daily or support the bot! ✨",
                            f"💸 Your {user_balance} gold doesn't cover the {play_cost} needed! Try -daily! 😎"
                        ]))
                        return

                    await self.highrise.send_message(conversation_id, random.choice([
                        "🎶 Use -play in the room chat to pay with gold! Let's go! 😎",
                        "🎶 In the room chat, use !play to spend your gold! Play that song! ✨",
                        "🎶 To pay with gold, type !play in the main chat! Ready? 🎵"
                    ]))
                    return

                await self.add_to_queue(song_request, username)
                await self.highrise.send_message(conversation_id, random.choice([
                    f"🎵 Nice one, @{username}! '{song_request}' has been added to the queue! 🎉",
                    f"🎵 @{username}, '{song_request}' is in the queue! Let's vibe! ✨",
                    f"🎵 Great choice, @{username}! '{song_request}' is on the list! 😎"
                ]))
            else:
                await self.highrise.send_message(conversation_id, random.choice([
                    "🎵 Use commands in the room chat or type -play <song> here! 📬",
                    "🎵 Room chat is best for commands! Try -play <song> in DMs! ✨",
                    "🎵 Main chat is better for commands! Use -play <song> here! 😎"
                ]))
        except Exception as e:
            print(f"❌ Error in on_message: {e}")

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem | Item) -> None:
        """Gerencia doações (tips) recebidas pelo bot."""
        if isinstance(tip, CurrencyItem) and receiver.id == self.highrise.my_id:
            await self.update_user_balance(sender.id, tip.amount)
            status = " (VIP 🎖️)" if self.is_vip(sender.id) else ""
            await self.highrise.chat(random.choice([
                f"💸 Thanks, @{sender.username}{status}! You donated {tip.amount} gold! Balance: {await self.get_user_balance(sender.id)} gold! 🎵",
                f"💸 @{sender.username}{status}, appreciate the {tip.amount} gold! Your balance now: {await self.get_user_balance(sender.id)} gold! ✨",
                f"💸 Awesome, @{sender.username}{status}! You gave {tip.amount} gold! Current balance: {await self.get_user_balance(sender.id)} gold! 😎"
            ]))

    async def process_play_payment(self, user: User, play_cost: int):
        """Processa o pagamento para tocar uma música."""
        if self.is_vip(user.id):
            await self.highrise.chat(random.choice([
                f"🎖️ @{user.username}, as a VIP, your song is on us! Play that tune! 🎶",
                f"🎖️ @{user.username}, VIPs play for free! Pick your song and let's go! ✨",
                f"🎖️ @{user.username}, free songs for VIPs! What's next? 😎"
            ]))
            return
        try:
            await self.update_user_balance(user.id, -play_cost)
            await self.update_user_balance(self.highrise.my_id, play_cost)
            new_balance = await self.get_user_balance(user.id)
            await self.highrise.chat(random.choice([
                f"💸 @{user.username}, you paid {play_cost} gold for the song! Balance: {new_balance} gold. Let's enjoy it! 🎵",
                f"💸 @{user.username}, {play_cost} gold paid! Your balance is {new_balance} gold. Play that track! ✨",
                f"💸 @{user.username}, song unlocked for {play_cost} gold! Current balance: {new_balance} gold! 😎"
            ]))
        except Exception as e:
            print(f"Error processing payment: {e}")
            await self.highrise.chat(random.choice([
                "🚫 Oops, something went wrong with the payment! Try again! 🎵",
                "🚫 Yikes, the payment failed! Can you try again? ✨",
                "🚫 Hmm, couldn't process the gold! Give it another shot! 😎"
            ]))

    async def check_queue(self, user: User):
        """Displays a premium, styled song queue (top 10)."""
        total_songs = len(self.song_queue)
        top_limit = 10

        if total_songs == 0:
            await self.highrise.send_whisper(user.id, random.choice([
            "🌌 The music galaxy is silent... Add your favorite track with `-play` ✨",
            "🪐 No tracks yet! Type `-play` and let the rhythm begin 🎶",
            "🥱 It's quiet here... Queue up a vibe using `-play`!"
        ]))
            return

        track_word = "Track" if total_songs == 1 else "Tracks"
        msg = f"""✨ Your Music Lounge ✨  
🎼 Total {total_songs} {track_word} in queue  
━━━━━━━━━━━━━━━━━━━\n"""

        music_emojis = ["🎵", "🎶", "🎧", "🎼", "🎷", "🎺", "🎸", "🪕", "🎻", "📻"]

        for idx, song in enumerate(self.song_queue[:top_limit], start=1):
            title = song.get("title", "Unknown Title")
            owner = song.get("owner", "Unknown")
            dedicated = f" 💖 for @{song['dedicated_to']}" if song.get("dedicated_to") else ""
            emoji = music_emojis[(idx - 1) % len(music_emojis)]

            msg += (
            f"\n{emoji} {idx}. {title}\n"
            f"   ↳ 🙋 Requested by @{owner}{dedicated}\n"
        )

        msg += "\n━━━━━━━━━━━━━━━━━━━\n💡 Use `-play` to add more tracks!"

    # Send the full message in one whisper
        await self.send_private_message(user, msg)

    
    async def show_history(self, user: User):
        """Exibe o histórico das últimas músicas tocadas."""
        total_songs = len(self.history)
        if total_songs == 0:
            await self.highrise.send_whisper(user.id, random.choice([
                "📜 We haven't played anything yet! Request a song with -play! 🎶",
                "📜 History is empty! Let's vibe with -play! ✨",
                "📜 No songs in history! Use -play to get started! 😎"
            ]))
            return
        history_message = f"🎶 Last {min(total_songs, 15)} songs played:\n\n"
        for index, song in enumerate(self.history[-15:][::-1], 1):
            duration = song.get('duration', 0)
            duration_minutes = int(duration // 60)
            duration_seconds = int(duration % 60)
            formatted_duration = f"{duration_minutes}:{duration_seconds:02d}"
            dedication = f" (dedicated to @{song['dedicated_to']})" if song.get('dedicated_to') else ""
            history_message += f"{index}. '{song['title']}' ({formatted_duration}) by @{song['owner']}{dedication} [{song['timestamp']}]\n"
        for msg in await self.split_message(history_message):
            await self.send_private_message(user, msg)
            await asyncio.sleep(0.5)


    async def add_to_queue(self, song_request, owner, dedicated_to=None):
        """Adiciona uma música à fila."""
        try:
            await self.highrise.chat(random.choice([
        "🔎 Searching for the perfect song for you... 🎵",
        "🔎 Looking up your song with care... 🎶",
        "🔎 Getting the next hit ready... Hang tight! ✨"
    ]))
        # 🔒 Check if song is banned before attempting to play
            for banned_title in self.banned_titles:
                if banned_title.lower() in song_request.lower():
                    await self.highrise.chat(f"⛔ @{owner}, the song '{song_request}' is banned and cannot be played. Try another!")
                    return

            max_queue_limit = self.settings.get("queue_limit_per_user", 3)
            if self.user_song_count.get(owner, 0) >= max_queue_limit:
                await self.highrise.chat(random.choice([
            f"🚫 @{owner}, you already have {max_queue_limit} songs in the queue! Wait for one to play! 🎶",
            f"🚫 @{owner}, you've hit the limit of {max_queue_limit} requests! Hang tight! ✨",
            f"🚫 @{owner}, that's {max_queue_limit} songs from you! Hold on, it'll play soon! 😎"
        ]))
                return

            file_path, title, duration = await self.download_youtube_audio(song_request)
            if file_path and title and duration:
                if title.lower() in self.banned_titles:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    await self.highrise.chat(f"🚫 @{owner}, '{title}' is banned and cannot be played. Pick another song.")
                    return
                max_duration = self.settings.get("max_song_duration", 12) * 60
                if duration > max_duration:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"File deleted: {file_path}")
                    await self.highrise.chat(random.choice([
                f"⏳ @{owner}, '{title}' exceeds {self.settings['max_song_duration']} minutes! Pick another? 🎵",
                f"⏳ @{owner}, '{title}' is too long! Max is {self.settings['max_song_duration']} min. Try another! ✨",
                f"⏳ @{owner}, '{title}' goes over the {self.settings['max_song_duration']} minute limit! Another song? 😎"
            ]))
                    return

                if any(song['title'].lower() == title.lower() for song in self.song_queue):
                    await self.highrise.chat(random.choice([
                f"🔁 @{owner}, '{title}' is already in the queue! Try another song! 🎶",
                f"🔁 @{owner}, '{title}' has already been requested! Pick a different song! ✨",
                f"🔁 @{owner}, '{title}' is already on the list! How about another hit? 😎"
            ]))
                    return

                if self.currently_playing_title and self.currently_playing_title.lower() == title.lower():
                    await self.highrise.chat(random.choice([
                f"🎧 @{owner}, '{title}' is playing now! Wait for it to finish! 🎵",
                f"🎧 @{owner}, '{title}' is already on! Hold tight! ✨",
                f"🎧 @{owner}, '{title}' is the current song! Try another later! 😎"
            ]))
                    return

                song_data = {
            'title': title,
            'file_path': file_path,
            'owner': owner,
            'duration': duration
        }
                if dedicated_to:
                    song_data['dedicated_to'] = dedicated_to

                self.song_queue.append(song_data)
                self.user_song_count[owner] = self.user_song_count.get(owner, 0) + 1

                user_id = None
                room_users = await self.highrise.get_room_users()
                for room_user, _ in room_users.content:
                    if room_user.username == owner:
                        user_id = room_user.id
                        break
                if user_id:
                    await self.update_rank(user_id)

                await self.save_queue()

                duration_minutes = int(duration // 60)
                duration_seconds = int(duration % 60)
                formatted_duration = f"{duration_minutes}:{duration_seconds:02d}"
                queue_position = len(self.song_queue)

                if dedicated_to:
                    await self.highrise.chat(random.choice([
                f"💖 A sweet dedication is on the way!\n🎵 Title: {title}\n⏱ Duration: {formatted_duration}\n📀 Queue: #{queue_position}\n🫶 From: @{owner} ➜ @{dedicated_to}\n🎶 Let the feelings flow!",
                f"💝 Song Shared with Love!\n🎼 Track: {title}\n🕒 Length: {formatted_duration}\n📀 Queue Spot: #{queue_position}\n🎁 @{owner} ➝ @{dedicated_to}\n✨ That’s a vibe with meaning!",
                f"🎁 Music Gift Incoming!\n🎵 Song: {title}\n🕓 Duration: {formatted_duration}\n📀 Position: #{queue_position}\n🎊 Dedicated by: @{owner} to @{dedicated_to}\n💕 Heartfelt moments ahead!",
                f"🎧 A track from the heart!\n📜 Title: {title}\n⏳ Duration: {formatted_duration}\n📀 Queue: #{queue_position}\n💖 @{owner} dedicated this to @{dedicated_to}\n🎉 Turn it up with love!",
                f"🎼 Special Dedication!\n🎵 Title: {title}\n⏱ Duration: {formatted_duration}\n📀 Queue No: #{queue_position}\n🤍 From: @{owner} to @{dedicated_to}\n🎊 Music with emotions attached!",
                f"💞 @{owner} just made it special for @{dedicated_to}!\n🎶 Track: {title} • {formatted_duration}\n📀 Queue: #{queue_position}\n📨 Let the music speak the feelings!"
            ]))
                else:
                    await self.highrise.chat(random.choice([
                f"\n🎶 Now Queued!\n📜 Title: {title}\n⏱ Duration: {formatted_duration}\n📀 Queue: #{queue_position}\n🙋 Requested by: @{owner}\n✨ Get ready to vibe!",
                f"\n🎵 Song Added to Queue!\n🎼 Title: {title}\n🕒 Length: {formatted_duration}\n📀 Position: #{queue_position}\n📣 Requested by: @{owner}\n🔥 Stay tuned!",
                f"\n🎧 New Track in the Lineup!\n🎵 Title: {title}\n⏳ Time: {formatted_duration}\n📀 Queue No: #{queue_position}\n🧑‍🎤 Requested by: @{owner}\n🎉 Let's jam!",
                f"\n🎼 Added to Playlist!\n📜 Track: {title}\n⏱ Duration: {formatted_duration}\n📀 Queue: #{queue_position}\n🔊 Requested by: @{owner}\n💓 Music is loading...",
                f"\n📥 Incoming Song Request!\n🎶 Title: {title}\n🕘 Duration: {formatted_duration}\n📀 Spot: #{queue_position}\n🙋 From: @{owner}\n🚀 On its way to the speakers!",
                f"\n🎤 You’re gonna love this one!\n🎵 Title: {title}\n🕓 Duration: {formatted_duration}\n📀 Queue Position: #{queue_position}\n🧍 Requested by: @{owner}\n🎊 Get ready to groove!"
            ]))

                if not self.currently_playing_title:
                    await self.play_next_song()
            else:
                await self.highrise.chat(random.choice([
            f"🚫 Couldn't find '{song_request}'! Try another song! 🎵",
            f"🚫 Oops, '{song_request}' wasn't found! Pick another tune! ✨",
            f"🚫 Hmm, '{song_request}' isn't available! Try a different hit! 😎"
        ]))
        except Exception as e:
            await self.highrise.chat(f"❌ Something went wrong while adding the song. Try again!")
            print(f"Error in add_to_queue: {e}")
            traceback.print_exc()
            
    async def del_last_song(self, owner):
        """Remove a última música do usuário da fila."""
        last_song = None
        for song in reversed(self.song_queue):
            if song['owner'] == owner:
                last_song = song
                break
        if last_song:
            self.song_queue.remove(last_song)
            self.user_song_count[owner] -= 1
            await self.highrise.chat(random.choice([
                f"🗑️ @{owner}, '{last_song['title']}' was removed from the queue! 🎶",
                f"🗑️ @{owner}, your song '{last_song['title']}' is out of the list! ✨",
                f"🗑️ @{owner}, I removed '{last_song['title']}' from the queue for you! 😎"
            ]))
            await self.save_queue()
        else:
            await self.highrise.chat(random.choice([
                f"😕 @{owner}, you don't have any songs in the queue! Try -play! 🎵",
                f"😕 @{owner}, no songs from you in the queue! Want to request one? ✨",
                f"😕 @{owner}, your queue is empty! Use !play to add a song! 😎"
            ]))

    async def clear_queue(self):
        """Limpa a fila de músicas e remove arquivos baixados."""
        self.song_queue.clear()
        self.user_song_count.clear()
        downloaded_files = glob.glob('downloads/*')
        for file in downloaded_files:
            try:
                os.remove(file)
                print(f"File deleted: {file}")
            except Exception as e:
                print(f"Error deleting file {file}: {e}")
        await self.save_queue()
        await self.highrise.chat(random.choice([
            "🗑️ Queue cleared and files removed! Ready to start fresh? 🎶",
            "🗑️ Emptied the queue and files! Ready for new songs? ✨",
            "🗑️ All clear! Queue empty, let's request some songs! 😎"
        ]))

    async def download_youtube_audio(self, song_request):
        """Baixa o áudio de uma música do YouTube com yt-dlp e retorna MP3 compatível."""
        try:
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
                'default_search': 'ytsearch',
                'quiet': True,
                'noplaylist': True,
                'cookiefile': 'cookies.txt',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song_request, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                video_id = info['id']
                title = info['title']
                duration = info['duration']
                file_path = f"downloads/{video_id}.mp3"

                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Arquivo MP3 não encontrado: {file_path}")

                print(f"Downloaded: {file_path} with title: {title}, duration: {duration} seconds")
                return file_path, title, duration

        except Exception as e:
            print(f"Error downloading song: {e}")
            await self.highrise.chat(random.choice([
                f"🚫 Erro ao baixar '{song_request}'! Tente outra música! 🎵",
                f"🚫 Não consegui encontrar '{song_request}'! Escolha outro hit! ✨"
            ]))
            return None, None, None

    async def now_playing(self, user: User):
        """Exibe informações sobre a música que está tocando."""
        if self.current_song is None:
            await self.highrise.send_whisper(user.id, random.choice([
                "🎵 Nothing's playing now! Request a song with !play! 🎶",
                "🎵 It's quiet in here! How about picking a tune with !play? ✨",
                "🎵 No song playing! Use !play to liven up the room! 😎"
            ]))
            return
        if self.currently_playing_title:
            current_song = self.current_song
            total_duration = current_song.get('duration', 0)
            adjusted_total_duration = total_duration
            delay_threshold = 20
            elapsed_time = time.time() - self.song_start_time
            if elapsed_time < delay_threshold:
                elapsed_time = 0
            else:
                elapsed_time -= delay_threshold
            elapsed_time = min(elapsed_time, adjusted_total_duration)
            progress_percentage = (elapsed_time / adjusted_total_duration) * 100
            progress_bar_length = 10
            filled_length = int(progress_percentage / (100 / progress_bar_length))
            progress_bar = '█' * filled_length
            empty_bar = '▒' * (progress_bar_length - filled_length)
            progress_bar_display = f"[{progress_bar}{empty_bar}]"
            total_duration_str = f"{int(adjusted_total_duration // 60)}:{int(adjusted_total_duration % 60):02d}"
            elapsed_time_str = f"{int(elapsed_time // 60)}:{int(elapsed_time % 60):02d}"
            dedication = f" (dedicated to @{current_song['dedicated_to']})" if current_song.get('dedicated_to') else ""
            message = random.choice([
                f"🎶 Now playing: '{self.currently_playing_title}'\n\n{elapsed_time_str} {progress_bar_display} {total_duration_str}\nBy @{current_song['owner']}{dedication} 🎵",
                f"🎶 On air: '{self.currently_playing_title}'\n\n{elapsed_time_str} {progress_bar_display} {total_duration_str}\nRequested by @{current_song['owner']}{dedication} ✨",
                f"🎶 Vibe: '{self.currently_playing_title}'\n\n{elapsed_time_str} {progress_bar_display} {total_duration_str}\nChosen by @{current_song['owner']}{dedication} 😎"
            ])
            for msg in await self.split_message(message):
                await self.highrise.send_whisper(user.id, msg)
                await asyncio.sleep(0.5)
        else:
            await self.highrise.send_whisper(user.id, random.choice([
                "🎵 Nothing's playing now! Request a song with -play! 🎶",
                "🎵 It's quiet in here! How about picking a tune with -play? ✨",
                "🎵 No song playing! Use -play to liven up the room! 😎"
            ]))

    async def play_next_song(self):
        """Toca a próxima música da fila."""
        try:
            self.skip_event.clear()
            await asyncio.sleep(2)
            if not self.song_queue:
                self.currently_playing = False
                self.currently_playing_title = None
                await self.highrise.chat(random.choice([
                "📭 The queue is empty! Who's got the next song? 🎶",
                "📭 No songs in the queue! Use -play to keep the vibe going! ✨",
                "📭 Queue is clear! Let's grab a song with -play! 😎"
            ]))
                return
            if self.currently_playing:
                print("A song is already playing. Avoiding starting a new one.")
                return
            next_song = self.song_queue.pop(0)
            await self.save_queue()
            self.current_song = next_song
            self.save_current_song()
            self.currently_playing = True
            self.currently_playing_title = next_song['title']
            song_title = next_song['title']
            song_owner = next_song['owner']
            dedicated_to = next_song.get('dedicated_to')
            file_path = next_song['file_path']
            self.song_start_time = time.time()
            duration = next_song.get('duration', 0)
            duration_minutes = int(duration // 60)
            duration_seconds = int(duration % 60)
            formatted_duration = f"{duration_minutes}:{duration_seconds:02d}"
        
        # Get listener count using tuple unpacking
            room_users = await self.highrise.get_room_users()
            listener_count = len(room_users.content)
            dedication_text = f"🎁 Dedicated by @{song_owner} ➜ @{dedicated_to}" if dedicated_to else f"🙋 Requested by: @{song_owner}"
        
            await self.highrise.chat(random.choice([
        f"\n🎵 Now Playing! 🎵\n📜 Title: {song_title}\n⏱ Duration: {formatted_duration}\n{dedication_text}\n👥 Total listeners: {listener_count}",
        f"\n🎶 Current Track 🎶\n🎼 Title: {song_title}\n🕒 Time: {formatted_duration}\n{dedication_text}\n👂 Listeners in room: {listener_count}",
        f"\n🎧 You're listening to:\n🎵 {song_title} • {formatted_duration}\n{dedication_text}\n👥 Vibe shared with {listener_count} people!"
    ]))
            print(f"Playing: {song_title}")
            history_entry = {
            'title': song_title,
            'owner': song_owner,
            'duration': duration,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
            if dedicated_to:
                history_entry['dedicated_to'] = dedicated_to
            self.history.append(history_entry)
            await self.save_history()
            mp3_file_path = await self.convert_to_mp3(file_path)
            if not mp3_file_path:
                await self.highrise.chat(random.choice([
                "⏳ Processing the song, one moment please... 🎵",
                "⏳ Preparing the song, just a second! ✨",
                "⏳ Loading the hit, hold on a moment! 😎"
            ]))
                new_file_path, new_title, new_duration = await self.download_youtube_audio(song_title)
                if new_file_path:
                    mp3_file_path = await self.convert_to_mp3(new_file_path)
                    if not mp3_file_path:
                        await self.highrise.chat(random.choice([
                        "🚫 Couldn't process the song! Moving to the next one! 🎶",
                        "🚫 Oops, the song failed! Next song coming up! ✨",
                        "🚫 Yikes, the song got stuck! On to the next hit! 😎"
                    ]))
                        self.currently_playing = False
                        await asyncio.sleep(10)
                        await self.play_next_song()
                        return
                    else:
                        file_path = new_file_path
                else:
                    await self.highrise.chat(random.choice([
                    "🚫 Failed to download! Moving to the next song! 🎶",
                    "🚫 Couldn't load! Next track coming up! ✨",
                    "🚫 Song not found! Let's go to the next hit! 😎"
                ]))
                    self.currently_playing = False
                    await asyncio.sleep(10)
                    await self.play_next_song()
                    return
            await self.stream_to_radioking(mp3_file_path)
            if os.path.exists(mp3_file_path):
                os.remove(mp3_file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            self.currently_playing = False
            self.current_song = None
            if not self.skip_event.is_set():
                if song_owner not in self.user_song_count:
                    self.user_song_count[song_owner] = 0
                self.user_song_count[song_owner] -= 1
                await asyncio.sleep(10)
                await self.play_next_song()
            else:
                self.skip_event.clear()
        except Exception as e:
            await self.highrise.chat(f"❌ An error occurred while playing the next song. Skipping to next.")
            print(f"Error in play_next_song: {e}")
            traceback.print_exc()
            self.currently_playing = False
            await asyncio.sleep(5)
            await self.play_next_song()

    async def convert_to_mp3(self, audio_file_path):
        """Converte para MP3 apenas se necessário."""
        try:
            if audio_file_path.endswith('.mp3'):
                return audio_file_path

            mp3_file_path = audio_file_path.rsplit('.', 1)[0] + '.mp3'
            if os.path.exists(mp3_file_path):
                return mp3_file_path

            subprocess.run([
                'ffmpeg', '-y', '-i', audio_file_path,
                '-acodec', 'libmp3lame', '-ab', '128k', '-ar', '44100', '-ac', '2', mp3_file_path
            ], check=True)

            return mp3_file_path
        except Exception as e:
            print(f"Erro ao converter para MP3: {e}")
            return None

    async def stream_to_radioking(self, mp3_file_path):
        """Transmite o arquivo MP3 para o servidor RadioKing."""
        icecast_server = "link.zeno.fm"

        icecast_port = 80

        mount_point = "/esjz5fvuzvwvv"

        username = "source"

        password = "VwU6gPr5"

        icecast_url = f"icecast://{username}:{password}@{icecast_server}:{icecast_port}{mount_point}"
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._run_ffmpeg, mp3_file_path, icecast_url)
            await asyncio.get_event_loop().run_in_executor(None, future.result)

    def _run_ffmpeg(self, mp3_file_path, icecast_url):
        """Executa o FFmpeg para transmissão."""
        command = [
            'ffmpeg', '-y', '-re', '-i', mp3_file_path,
            '-f', 'mp3', '-acodec', 'libmp3lame', '-ab', '192k',
            '-ar', '44100', '-ac', '2', '-reconnect', '1', '-reconnect_streamed', '1',
            '-reconnect_delay_max', '2', icecast_url
        ]
        try:
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait()
                self.ffmpeg_process = None
            self.ffmpeg_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = self.ffmpeg_process.communicate()
            if self.ffmpeg_process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {stderr.decode('utf-8')}")
        except Exception as e:
            print(f"FFmpeg process error: {e}")

    async def skip_song(self, user):
        """Pula a música atual."""
        if self.currently_playing:
            if self.is_admin(user.username) or (self.current_song and self.current_song['owner'] == user.username):
                async with asyncio.Lock():
                    self.skip_event.set()
                    if self.ffmpeg_process:
                        self.ffmpeg_process.terminate()
                        self.ffmpeg_process.wait()
                        self.ffmpeg_process = None
                    song_owner = self.current_song['owner']
                    if song_owner in self.user_song_count:
                        self.user_song_count[song_owner] -= 1
                        if self.user_song_count[song_owner] <= 0:
                            del self.user_song_count[song_owner]
                    await self.highrise.chat(random.choice([
                        f"⏭️ @{user.username} skipped the current song! Next one up! 🎶",
                        f"⏭️ @{user.username} hit skip! Next song coming up! ✨",
                        f"⏭️ Song skipped by @{user.username}! Let's play the next hit! 😎"
                    ]))
                    await asyncio.sleep(10)
                    self.currently_playing = False
                    await self.play_next_song()
            else:
                await self.highrise.chat(random.choice([
                    "🔒 Only the song owner or an admin can skip! Try another command! 🎵",
                    "🔒 Oops, only the owner or admin can skip the song! How about requesting a new one? ✨",
                    "🔒 Only the owner or admin can skip! Use !play to pick a song! 😎"
                ]))
        else:
            await self.highrise.chat(random.choice([
                "🎵 No song to skip! Request one with -play! 🎶",
                "🎵 Nothing playing to skip! Try -play to start! ✨",
                "🎵 No song right now! How about a -play? 😎"
            ]))

    async def stop_existing_stream(self):
        """Para qualquer transmissão ativa."""
        if self.ffmpeg_process:
            print("Stopping active stream...")
            try:
                self.ffmpeg_process.terminate()
                await asyncio.sleep(1)
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.kill()
                print("Stream stopped successfully.")
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self.ffmpeg_process = None
        else:
            print("No active stream to stop.")

    async def musicbot_dance(self):
        """Faz o bot dançar enquanto há músicas na fila ou tocando."""
        while True:
            try:
                if self.song_queue or self.currently_playing:
                    await self.highrise.send_emote('dance-tiktok11', self.highrise.my_id)
                    await asyncio.sleep(9.5)
                else:
                    await self.highrise.send_emote('emote-hello', self.highrise.my_id)
                    await asyncio.sleep(2.7)
            except Exception as e:
                print(f"Error sending emote: {e}")

    async def save_queue(self):
        """Salva a fila de músicas no arquivo JSON."""
        async with asyncio.Lock():
            try:
                with open('song_queue.json', 'w') as file:
                    json.dump(self.song_queue, file)
                await self.backup_file('song_queue.json')
            except Exception as e:
                print(f"Error saving queue: {e}")

    def load_queue(self):
        """Carrega a fila de músicas do arquivo JSON."""
        try:
            with open('song_queue.json', 'r') as file:
                self.song_queue = json.load(file)
                print("Song queue loaded from file.")
        except FileNotFoundError:
            self.song_queue = []
        except Exception as e:
            print(f"Error loading queue: {e}")

    async def get_actual_pos(self, user_id):
        """Obtém a posição atual de um usuário na sala."""
        room_users = await self.highrise.get_room_users()
        for user, position in room_users.content:
            if user.id == user_id:
                return position

    def save_loc_data(self):
        """Salva dados de localização do bot, incluindo direção."""
        loc_data = {
            'bot_position': {
                'x': self.bot_pos.x,
                'y': self.bot_pos.y,
                'z': self.bot_pos.z,
                'facing': self.bot_pos.facing  # 🆕 Added facing
            } if self.bot_pos else None,
            'ctoggle': self.ctoggle
        }
        with open('loc_data.json', 'w') as file:
            json.dump(loc_data, file)

    def load_loc_data(self):
        """Carrega dados de localização do bot com direção."""
        try:
            with open('loc_data.json', 'r') as file:
                loc_data = json.load(file)
                pos_data = loc_data.get('bot_position')
                if pos_data:
                    self.bot_pos = Position(
                        x=pos_data['x'],
                        y=pos_data['y'],
                        z=pos_data['z'],
                        facing=pos_data.get('facing', 'Front')  # default 'Front' if missing
                )
                else:
                    self.bot_pos = None
                self.ctoggle = loc_data.get('ctoggle', False)
        except FileNotFoundError:
            pass

    def save_current_song(self):
        """Salva a música atual no arquivo JSON."""
        with open("current_song.json", "w") as file:
            json.dump(self.current_song, file)

    def load_current_song(self):
        """Carrega a música atual do arquivo JSON."""
        try:
            with open("current_song.json", "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    async def send_private_message(self, user: User, message: str) -> None:
        """Send a private message to the user if they have a valid conversation_id in self.datas."""
        if user.id in self.datas and "conversation_id" in self.datas[user.id]:
            conversation_id = self.datas[user.id]["conversation_id"]
            await self.highrise.send_message(conversation_id, message)
        else:
            await self.highrise.chat(
            f"👋 Hey [{user.username}], I can't DM you yet! Please message me 'hi' in DM so I can reply properly. Then try again here!"
        )

    async def equip_item(self: BaseBot, user: User, message: str):
        parts = message.strip().split(" ")
        if len(parts) < 2:
            await self.highrise.chat("❗ Please provide the item ID.")
            return

        item_id = parts[1]

        try:
        # Create the item directly
            new_item = Item(
            type="clothing",
            amount=1,
            id=item_id,
            account_bound=False,
            active_palette=0
        )

        # Remove conflicting items from the same category
            outfit = (await self.highrise.get_my_outfit()).outfit
            item_category = item_id.split("-")[0][0:4]
            outfit = [item for item in outfit if item.id.split("-")[0][0:4] != item_category]

            outfit.append(new_item)
            await self.highrise.set_outfit(outfit)

            await self.highrise.chat(f"✅ Equipped `{item_id}` successfully.")
        except Exception as e:
            await self.highrise.chat(f"⚠️ Failed to equip: {e}")