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
import google.generativeai as genai

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
else:
    model_gemini = None

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

async def ask_gemini_solver(clean_question):
    if not model_gemini:
        print("⚠️ [GEMINI] Thiếu GEMINI_API_KEY trong biến môi trường!", flush=True)
        return None

    prompt = f"Bạn là hệ thống giải đố game. Trả lời câu hỏi sau bằng tên riêng/đáp án chuẩn xác nhất trong game (ưu tiên tên gốc tiếng Anh/Việt chuẩn của game). Chỉ xuất DUY NHẤT đáp án từ 1 đến 5 từ, không viết cả câu, không giải thích.\n\nCâu hỏi: {clean_question}"
    
    try:
        response = await asyncio.to_thread(model_gemini.generate_content, prompt)
        if response and response.text:
            raw_ans = response.text.strip()
            raw_clean = re.sub(r'\*\*|__|\*|_', '', raw_ans)
            first_line = raw_clean.split('\n')[0].strip()
            cleaned = clean_final_answer(first_line)
            cleaned = re.sub(r'^(đáp án(?: là)?|tên(?: là)?|gọi(?: là)?|chính(?: là)?|là)\s+', '', cleaned, flags=re.IGNORECASE).strip()
            if cleaned:
                return cleaned
    except Exception as e:
        print(f"❌ [GEMINI] Lỗi truy vấn API: {e}", flush=True)

    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"🔍 [SEARCH] Đang xử lý câu hỏi: {clean_question}", flush=True)
    
    ans = await ask_gemini_solver(clean_question)
    if ans:
        print(f"✅ [AI] Tìm thấy đáp án: {ans}", flush=True)
        return ans
        
    return None

@tasks.loop(hours=4, minutes=30)
async def auto_feed_loop(bot_instance):
    if not IS_FEED_ENABLED:
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
