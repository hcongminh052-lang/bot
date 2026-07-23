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
from bs4 import BeautifulSoup

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

BAD_WORDS = ["nhân v", "nhân vật", "hình ảnh", "kết quả", "trả lời", "câu hỏi", "thông tin", "được biết", "xem thêm", "genshin", "impact", "wiki", "fandom"]

def clean_final_answer(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
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

def parse_extracted_phrase(raw_found):
    if not raw_found:
        return None
        
    cleaned = clean_final_answer(raw_found)
    cleaned = re.sub(r'^(?:món|món ăn|là|của|tên là|có tên là)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    if any(bad in cleaned.lower() for bad in BAD_WORDS):
        return None

    words = cleaned.split()
    if 1 <= len(words) <= 5 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 5:
        return " ".join(words[:3])
        
    return None

async def ask_duckduckgo_web_search(clean_question):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    urls = [
        f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_question)}",
        f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(clean_question)}"
    ]
    
    try:
        print("🌐 [DDG WEB] Đang cào dữ liệu DuckDuckGo Search...", flush=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                async with session.get(url, headers=headers, timeout=6) as res:
                    if res.status == 200:
                        html_text = await res.text()
                        soup = BeautifulSoup(html_text, 'html.parser')
                        
                        results = soup.find_all('div', class_='result')
                        if not results:
                            results = soup.find_all('td', class_='result-snippet')
                            
                        for result in results:
                            title_tag = result.find('a', class_='result__title') or result.find('a')
                            snippet_tag = result.find('a', class_='result__snippet') or result
                            
                            title_text = title_tag.get_text().strip() if title_tag else ""
                            snippet_text = snippet_tag.get_text().strip() if snippet_tag else ""
                            
                            quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title_text)
                            for match in quoted_matches:
                                ans = parse_extracted_phrase(match)
                                if ans and ans.lower() not in ["genshin impact", "furina", "fandom"]:
                                    return ans
                                    
                            if '|' in title_text:
                                possible_name = title_text.split('|')[0].strip()
                                ans = parse_extracted_phrase(possible_name)
                                if ans and ans.lower() not in ["genshin impact", "furina", "fandom"]:
                                    return ans

                            match = re.search(r'(?:là|có tên là|tên là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9\s\-_]{2,25})', snippet_text, re.IGNORECASE)
                            if match:
                                ans = parse_extracted_phrase(match.group(1))
                                if ans:
                                    return ans
    except Exception as e:
        print(f"  └─ ❌ [DDG WEB EXCEPTION]: {e}", flush=True)
        
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_ddg = await ask_duckduckgo_web_search(clean_question)
    if ans_ddg:
        print(f"✅ [KẾT QUẢ DDG WEB]: {ans_ddg}\n============================================================\n", flush=True)
        return ans_ddg

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
