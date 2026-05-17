import os
import random
import asyncio
import requests
from discord.ext import tasks

class GachaHandler:
    def __init__(self, bot):
        self.bot = bot
        # Các thông số cấu hình nút bấm
        self.url = "https://discord.com/api/v9/interactions"
        self.guild_id = "1194106864582004849"
        self.channel_id = "1387434589756199046"
        self.message_id = "1490938876603404399"
        self.application_id = "1381506157591527464"
        self.session_id = "857dabc4789a44153e77d8ac7b7ee3d2"
        self.custom_id = "roll_roll_plastic_0"

    def generate_nonce(self):
        return str(random.randint(10**17, 10**19 - 1))

    def start_loop(self):
        """Kích hoạt vòng lặp 24h"""
        if not self.auto_daily_roll.is_running():
            self.auto_daily_roll.start()

    @tasks.loop(hours=24)
    async def auto_daily_roll(self):
        # Lấy token từ biến môi trường hệ thống của Render
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ [Gacha] Không tìm thấy DISCORD_TOKEN trong Environment!")
            return

        headers = {
            "authorization": token.strip(),
            "content-type": "application/json"
        }
        
        payload = {
            "type": 3,
            "nonce": self.generate_nonce(),
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "message_flags": 32768,
            "message_id": self.message_id,
            "application_id": self.application_id,
            "session_id": self.session_id,
            "data": {
                "component_type": 2,
                "custom_id": self.custom_id
            }
        }

        # Trì hoãn ngẫu nhiên trước khi bấm nút từ 1 đến 5 phút cho an toàn
        delay = random.randint(60, 300)
        print(f"⏳ [Gacha] Sẽ tự động Roll Free sau {delay} giây nữa...")
        await asyncio.sleep(delay)

        try:
            # Chạy request trong executor để không gây nghẽn bot
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(self.url, headers=headers, json=payload)
            )
            print(f"🎰 [Gacha] Kết quả Roll Free | Status: {response.status_code}")
        except Exception as e:
            print(f"❌ [Gacha] Lỗi khi tự động Roll Free: {e}")
