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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
        print("  └─ ❌ [PARSE] raw_text rỗng/None", flush=True)
        return None
        
    print(f"  ├─ 📄 [RAW OUTPUT]: {repr(raw_text)}", flush=True)
    text = re.sub(r'\*\*|__|\*|_|`', '', raw_text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    target_text = lines[0] if lines else text
    
    match = re.search(r'(?:là|có tên là|tên là|gọi là|chính là|đáp án|đáp án là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_,]+)', target_text, re.IGNORECASE)
    if match:
        target_text = match.group(1).strip()
        print(f"  ├─ 🔍 [REGEX MATCH]: {repr(target_text)}", flush=True)
        
    cleaned = clean_final_answer(target_text)
    words = cleaned.split()
    print(f"  ├─ 🧹 [CLEANED]: {repr(cleaned)} | Số từ: {len(words)}", flush=True)
    
    if 1 <= len(words) <= 6:
        return cleaned
    elif len(words) > 6:
        truncated = " ".join(words[:4])
        print(f"  ├─ ✂️ [TRUNCATED >6 từ]: {repr(truncated)}", flush=True)
        return truncated
        
    print("  └─ ❌ [PARSE] Không thể trích xuất được từ hợp lệ", flush=True)
    return None

async def ask_gemini_rest(clean_question):
    if not GEMINI_API_KEY:
        print("  └─ ⚠️ [GEMINI REST] Bỏ qua vì không tìm thấy GEMINI_API_KEY", flush=True)
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"Trả lời câu hỏi game sau. CHỈ XUẤT DUY NHẤT TÊN/ĐÁP ÁN (1-4 từ), không viết câu:\n\n{clean_question}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    print(f"🌐 [GEMINI REST] Gửi request đến Gemini 2.0 Flash...", flush=True)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5) as res:
                print(f"  ├─ 📥 [HTTP STATUS]: {res.status}", flush=True)
                if res.status == 200:
                    data = await res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        return parse_best_answer(raw_text)
                elif res.status == 429:
                    print("  └─ ⚠️ [GEMINI REST] Bị Rate Limit (429)", flush=True)
                else:
                    err_body = await res.text()
                    print(f"  └─ ❌ [GEMINI REST ERROR BODY]: {err_body[:200]}", flush=True)
    except Exception as e:
        print(f"  └─ ❌ [GEMINI REST EXCEPTION]: {e}", flush=True)

    return None

async def ask_pollinations_fallback(clean_question):
    models = ["openai", "qwen-coder", "mistral"]
    
    async with aiohttp.ClientSession() as session:
        for model in models:
            prompt = f"Question: {clean_question}\nOutput ONLY the precise answer name (1 to 4 words). No sentence, no explanation."
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded_prompt}?model={model}"
            
            print(f"🌐 [POLLINATIONS] Gọi API Model: '{model}'...", flush=True)
            print(f"  ├─ 🔗 [URL]: {url}", flush=True)
            try:
                async with session.get(url, timeout=6) as res:
                    print(f"  ├─ 📥 [HTTP STATUS]: {res.status}", flush=True)
                    if res.status == 200:
                        raw_text = await res.text()
                        ans = parse_best_answer(raw_text)
                        if ans:
                            return ans
                    else:
                        print(f"  └─ ⚠️ [POLLINATIONS] HTTP {res.status}", flush=True)
            except Exception as e:
                print(f"  └─ ❌ [POLLINATIONS EXCEPTION] Model {model}: {e}", flush=True)
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        print("⚠️ [SOLVE] Không thể trích xuất câu hỏi từ tin nhắn Discord.", flush=True)
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_gemini = await ask_gemini_rest(clean_question)
    if ans_gemini:
        print(f"✅ [KẾT QUẢ GEMINI]: {ans_gemini}\n============================================================\n", flush=True)
        return ans_gemini

    print("⚠️ [FALLBACK] Chuyển sang Pollinations AI...", flush=True)
    ans_fallback = await ask_pollinations_fallback(clean_question)
    if ans_fallback:
        print(f"✅ [KẾT QUẢ POLLINATIONS]: {ans_fallback}\n============================================================\n", flush=True)
        return ans_fallback
        
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
