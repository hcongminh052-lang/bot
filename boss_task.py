import asyncio
import discord
from datetime import datetime, timezone, timedelta

TARGET_BOT_ID = 1381506157591527464
TARGET_CHANNEL_ID = 1340657013683650651

async def process_boss_message(message):
    # 1. Kiểm tra kênh và người gửi
    if message.channel.id != TARGET_CHANNEL_ID or message.author.id != TARGET_BOT_ID:
        return

    # 2. Kiểm tra khung giờ 12h và 19h
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    
    if now.hour not in [12, 19]:
        return

    # In log debug khi thấy bot boss nhắn/sửa tin trong khung giờ
    print(f"🔍 [{now.strftime('%H:%M:%S')}] Phát hiện tin nhắn từ Bot Boss...", flush=True)

    # 3. Lấy components an toàn
    components = getattr(message, 'components', [])
    if not components:
        print(f"⚠️ [{now.strftime('%H:%M:%S')}] Tin nhắn không chứa nút bấm (components).", flush=True)
        return

    # 4. Tìm và bấm nút
    for row in components:
        children = getattr(row, 'children', [])
        for component in children:
            label = getattr(component, 'label', '') or ''
            emoji = getattr(component, 'emoji', None)
            emoji_name = emoji.name if emoji else ''

            if "Đánh Boss" in label or "⚔️" in emoji_name:
                try:
                    await component.click()
                    print(f"[{now.strftime('%H:%M:%S')}] ⚔️ ĐÃ ĐÁNH BOSS THÀNH CÔNG!", flush=True)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"❌ Lỗi bấm nút đánh boss: {e}", flush=True)

def start_boss_task(bot):
    # Bắt tin nhắn mới
    @bot.listen('on_message')
    async def auto_boss_on_message(message):
        await process_boss_message(message)

    # Bắt tin nhắn được chỉnh sửa (Edit)
    @bot.listen('on_message_edit')
    async def auto_boss_on_edit(before, after):
        await process_boss_message(after)

    print("⚔️ [HỆ THỐNG] Module Tự động Đánh Boss đã khởi động (New & Edit).", flush=True)
