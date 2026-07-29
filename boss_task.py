import asyncio
import discord
from datetime import datetime, timezone, timedelta

# Cấu hình ID
TARGET_BOT_ID = 1381506157591527464
TARGET_CHANNEL_ID = 1340657013683650651

def start_boss_task(bot):
    @bot.listen('on_message')
    async def auto_boss_listener(message):
        # 1. Kiểm tra ID kênh và Bot
        if message.channel.id != TARGET_CHANNEL_ID:
            return
        if message.author.id != TARGET_BOT_ID:
            return

        # 2. Kiểm tra khung giờ (12h và 19h)
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        
        if now.hour not in [12, 19]:
            return

        # 3. Tìm và bấm nút
        if message.components:
            for row in message.components:
                children = getattr(row, 'children', [])
                for component in children:
                    label = getattr(component, 'label', '') or ''
                    emoji = getattr(component, 'emoji', None)
                    emoji_name = emoji.name if emoji else ''

                    if "Đánh Boss" in label or "⚔️" in emoji_name:
                        try:
                            await component.click()
                            print(f"[{now.strftime('%H:%M:%S')}] ⚔️ Đã đánh boss tại kênh: {message.channel.name}")
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"❌ Lỗi nhấn nút: {e}")
                            
    print("⚔️ [HỆ THỐNG] Module Tự động Đánh Boss đã được tải.")
