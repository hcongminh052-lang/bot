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

        # 2. Kiểm tra khung giờ (chỉ hoạt động lúc 12h và 19h)
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        
        if now.hour not in [12, 19]:
            return

        # 3. Sử dụng getattr an toàn để không bị lỗi 'components'
        components = getattr(message, 'components', [])
        if components:
            for row in components:
                children = getattr(row, 'children', [])
                for component in children:
                    label = getattr(component, 'label', '') or ''
                    emoji = getattr(component, 'emoji', None)
                    emoji_name = emoji.name if emoji else ''

                    # Bấm nút nếu có chữ "Đánh Boss" hoặc icon ⚔️
                    if "Đánh Boss" in label or "⚔️" in emoji_name:
                        try:
                            await component.click()
                            print(f"[{now.strftime('%H:%M:%S')}] ⚔️ Đã đánh boss tại kênh: {message.channel.name}", flush=True)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"❌ Lỗi nhấn nút: {e}", flush=True)
                            
    print("⚔️ [HỆ THỐNG] Module Tự động Đánh Boss đã được tải.", flush=True)
