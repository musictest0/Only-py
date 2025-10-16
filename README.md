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
                await self.highrise.
