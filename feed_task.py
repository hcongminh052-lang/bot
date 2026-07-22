import json
import os
import asyncio
import random
import re
import urllib.parse
import pytz
import discord
from discord.ext import commands, tasks
from datetime import datetime
import io
import aiohttp

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

def is_valid_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    return 8 <= now.hour < 22

def clean_final_answer(text):
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[^a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_,]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_real_question(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        if '?' in line and not line.startswith('💬') and not line.startswith('↩️'):
            clean_line = re.sub(r'\*\*|__|[*_`]', '', line)
            return clean_line.strip()
            
    for line in lines:
        if not line.startswith('💬') and not line.startswith('↩️') and "Reply" not in line:
            clean_line = re.sub(r'\*\*|__|[*_`]', '', line)
            return clean_line.strip()
            
    return None

async def ask_ai_solver(clean_question):
    prompt = f"Bạn là hệ thống giải đố game chuyên nghiệp. Hãy trả lời câu hỏi sau thật chính xác. CHỈ TRẢ VỀ DUY NHẤT TÊN/ĐÁP ÁN CHÍNH XÁC. Không trả lời thành câu, không giải thích, không viết thêm từ thừa.\n\nCâu hỏi: {clean_question}"
    url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=8) as res:
                if res.status == 200:
                    raw_response = await res.text()
                    cleaned = clean_final_answer(raw_response)
                    
                    match = re.search(r'(?:có tên là|tên là|gọi là|chính là|là|đáp án|tên)\s+(.*)', cleaned, re.IGNORECASE)
                    if match:
                        cleaned = match.group(1).strip()
                        
                    words = cleaned.split()
                    if 1 <= len(words) <= 6:
                        return cleaned
    except Exception:
        pass
        
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"🔍 [SEARCH] Đang xử lý câu hỏi: {clean_question}", flush=True)
    
    ans = await ask_ai_solver(clean_question)
    if ans:
        print(f"✅ [AI] Tìm thấy đáp án: {ans}", flush=True)
        return ans
        
    return None

@tasks.loop(hours=4, minutes=30)
async def auto_feed_loop(bot_instance):
    if not IS_FEED_ENABLED:
        return

    if not is_valid_time():
        return

    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    channel = bot_instance.get_channel(chosen_channel_id)
    
    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300)
                await asyncio.sleep(extra_wait)
            
            if not IS_FEED_ENABLED:
                return

            await channel.send(".feed")
            
        except Exception:
            pass

async def setup_message_listener(bot_instance):
    @bot_instance.event
    async def on_message(message):
        global IS_FEED_ENABLED

        if message.content == "!feed off":
            IS_FEED_ENABLED = False
            await message.reply("🛑 Đã tạm dừng vòng lặp tự động gửi `.feed`.")
            return

        if message.content == "!feed on":
            IS_FEED_ENABLED = True
            await message.reply("🌾 Đã bắt đầu lại vòng lặp tự động gửi `.feed`.")
            return

        if message.channel.id not in FEED_CHANNEL_IDS:
            return

        if message.author.id == BOT_GAME_ID:
            question_text = ""
            if message.embeds:
                embed = message.embeds[0]
                question_text = embed.description if embed.description else (embed.title if embed.title else "")
            else:
                question_text = message.content

            if question_text:
                answer = await solve_question(question_text)
                if answer:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    await message.reply(answer)
                else:
                    print("⚠️ [FEED] Không thể trích xuất được đáp án chính xác.", flush=True)

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    
    @auto_feed_loop.before_loop
    async def before_auto_feed():
        await bot.wait_until_ready()
        
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
