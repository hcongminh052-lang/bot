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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "DAP_API_KEY_OPENROUTER_VAO_DAY_HOAC_O_ENV")

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

def parse_best_answer(raw_text):
    if not raw_text:
        return None
        
    print(f"  ├─ 📄 [AI RAW RESPONSE]: {repr(raw_text)}", flush=True)
    
    text = re.sub(r'\*\*|__|\*|_|`', '', raw_text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    target_text = lines[0] if lines else text
    
    target_text = re.sub(r'^(?:đáp án|câu trả lời|kết quả|tên món ăn)(?: là)?:\s*', '', target_text, flags=re.IGNORECASE)
    
    cleaned = clean_final_answer(target_text)
    words = cleaned.split()
    
    if 1 <= len(words) <= 6 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 6:
        return " ".join(words[:4])
        
    return None

async def ask_openrouter_api(clean_question):
    if not OPENROUTER_API_KEY or "DAP_API_KEY" in OPENROUTER_API_KEY:
        print("  └─ ⚠️ [OPENROUTER] Chưa nhận diện được API Key hợp lệ.", flush=True)
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    models = [
        "openrouter/auto",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-small-24b-instruct-2501:free",
        "qwen/qwen-2.5-7b-instruct:free"
    ]

    async with aiohttp.ClientSession() as session:
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý giải đố game. Nhiệm vụ của bạn là CHỈ xuất ra duy nhất tên/đáp án ngắn gọn (từ 1 đến 4 từ). Không viết câu hoàn chỉnh, không thêm lời mở đầu hay giải thích."
                    },
                    {
                        "role": "user",
                        "content": f"Câu hỏi: {clean_question}\nĐáp án:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 20
            }
            try:
                print(f"🌐 [OPENROUTER] Thử model '{model}'...", flush=True)
                async with session.post(url, headers=headers, json=payload, timeout=8) as res:
                    print(f"  ├─ 📥 [HTTP STATUS]: {res.status}", flush=True)
                    if res.status == 200:
                        data = await res.json()
                        choices = data.get("choices", [])
                        if choices:
                            raw_text = choices[0]["message"]["content"].strip()
                            ans = parse_best_answer(raw_text)
                            if ans:
                                return ans
                    else:
                        err_text = await res.text()
                        print(f"  └─ ⚠️ [OPENROUTER ERR BODY]: {err_text[:150]}", flush=True)
            except Exception as e:
                print(f"  └─ ❌ [OPENROUTER EXCEPTION]: {e}", flush=True)

    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_openrouter = await ask_openrouter_api(clean_question)
    if ans_openrouter:
        print(f"✅ [KẾT QUẢ OPENROUTER]: {ans_openrouter}\n============================================================\n", flush=True)
        return ans_openrouter

    print("❌ [KẾT QUẢ]: Thất bại toàn bộ các nguồn.\n============================================================\n", flush=True)
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
