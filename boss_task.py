import asyncio
import discord
from datetime import datetime, timezone, timedelta

TARGET_BOT_ID = 1381506157591527464
TARGET_CHANNEL_ID = 1340657013683650651

async def process_boss_message(message):
    if message.channel.id != TARGET_CHANNEL_ID:
        return
    if message.author.id != TARGET_BOT_ID:
        return

    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)

    is_valid_time = (now.hour == 12 and 0 <= now.minute <= 15) or \
                    (now.hour == 19 and 0 <= now.minute <= 15)

    if is_valid_time:
        if hasattr(message, 'components') and message.components:
            for row in message.components:
                children = getattr(row, 'children', [])
                for component in children:
                    label = getattr(component, 'label', '') or ''
                    emoji = getattr(component, 'emoji', None)
                    emoji_name = emoji.name if emoji else ''

                    if "Đánh Boss" in label or "⚔️" in emoji_name:
                        try:
                            await component.click()
                            print(f"[{now.strftime('%H:%M:%S')}] Đã đánh tại: {message.channel.name}")
                        except Exception as e:
                            print(f"Lỗi nhấn nút: {e}")

def start_boss_task(bot):
    @bot.listen('on_message')
    async def auto_boss_on_message(message):
        await process_boss_message(message)

    @bot.listen('on_message_edit')
    async def auto_boss_on_edit(before, after):
        await process_boss_message(after)
        
    print("Module Tự động Đánh Boss đã được tải.")
