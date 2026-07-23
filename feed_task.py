import json
import os
import asyncio
import random
import re
import urllib.parse
import discord
from discord.ext import commands, tasks
import io
import aiohttp
from bs4 import BeautifulSoup

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

GENSHIN_ELEMENTS = {
    "thủy": "Thủy",
    "hydro": "Thủy",
    "hỏa": "Hỏa",
    "pyro": "Hỏa",
    "lôi": "Lôi",
    "electro": "Lôi",
    "thảo": "Thảo",
    "dendro": "Thảo",
    "băng": "Băng",
    "cryo": "Băng",
    "phong": "Phong",
    "anemo": "Phong",
    "nham": "Nham",
    "geo": "Nham"
}

BAD_WORDS = ["nhân v", "nhân vật", "hình ảnh", "kết quả", "trả lời", "câu hỏi", "thông tin", "được biết", "xem thêm", "genshin", "impact", "wiki", "fandom", "wikipedia", "lịch sử"]
STOP_WORDS = {"đã", "được", "có", "không", "như", "là", "những", "một", "với", "cho", "trong", "về", "đang", "sẽ", "khi", "bằng", "các", "theo"}

def clean_final_answer(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'[/_\\\-]', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s]', '', text)
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

def parse_extracted_phrase(raw_found, question_type=None):
    if not raw_found:
        return None
        
    cleaned = clean_final_answer(raw_found)
    cleaned = re.sub(r'^(?:món|món ăn|là|của|tên là|có tên là)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    words = cleaned.split()
    if not words:
        return None
        
    if words[0].lower() in STOP_WORDS:
        return None
        
    if any(bad in cleaned.lower() for bad in BAD_WORDS):
        return None

    if question_type == "element" and cleaned.lower() in ["fontaine", "furina", "mondstadt", "liyue", "inazuma", "sumeru", "natlan", "snezhnaya"]:
        return None

    if 1 <= len(words) <= 5 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 5:
        return " ".join(words[:3])
        
    return None

def detect_element_in_text(text):
    text_lower = text.lower()
    for key, val in GENSHIN_ELEMENTS.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, text_lower):
            return val
    return None

async def fetch_fandom_api(clean_question, is_element_query):
    url = f"https://genshin-impact.fandom.com/vi/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_question)}&format=json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        print("🌐 [FANDOM API] Đang truy vấn trực tiếp Fandom Wiki...", flush=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=4) as res:
                if res.status == 200:
                    data = await res.json()
                    search_results = data.get("query", {}).get("search", [])
                    for item in search_results:
                        snippet = item.get("snippet", "")
                        clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                        
                        if is_element_query:
                            found_elem = detect_element_in_text(clean_snippet)
                            if found_elem:
                                return found_elem

                        title = item.get("title", "")
                        quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title)
                        if quoted_matches:
                            ans = parse_extracted_phrase(quoted_matches[0], "element" if is_element_query else None)
                            if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                                return ans
                        ans = parse_extracted_phrase(title, "element" if is_element_query else None)
                        if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                            return ans
    except Exception:
        pass
    return None

async def fetch_web_search(clean_question, is_element_query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    searx_instances = [
        "https://searx.be/search",
        "https://searx.tiekoetter.com/search",
        "https://search.mdosch.de/search"
    ]
    
    print("🌐 [WEB SEARCH] Đang tìm kiếm qua SearxNG JSON & DDG POST...", flush=True)
    async with aiohttp.ClientSession() as session:
        for instance in searx_instances:
            try:
                params = {"q": clean_question, "format": "json"}
                async with session.get(instance, params=params, headers=headers, timeout=5) as res:
                    if res.status == 200:
                        data = await res.json()
                        results = data.get("results", [])
                        for result in results:
                            snippet_text = result.get("content", "")
                            
                            if is_element_query:
                                found_elem = detect_element_in_text(snippet_text)
                                if found_elem:
                                    return found_elem

                            title_text = result.get("title", "")
                            quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title_text)
                            for match in quoted_matches:
                                ans = parse_extracted_phrase(match, "element" if is_element_query else None)
                                if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                                    return ans
                                    
                            if '|' in title_text or '-' in title_text:
                                delimiter = '|' if '|' in title_text else '-'
                                possible_name = title_text.split(delimiter)[0].strip()
                                ans = parse_extracted_phrase(possible_name, "element" if is_element_query else None)
                                if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                                    return ans

                            match = re.search(r'(?:là|có tên là|tên là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9\s\-_]{2,25})', snippet_text, re.IGNORECASE)
                            if match:
                                ans = parse_extracted_phrase(match.group(1), "element" if is_element_query else None)
                                if ans:
                                    return ans
            except Exception:
                continue
                
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            payload = {"q": clean_question, "b": ""}
            async with session.post(ddg_url, data=payload, headers=headers, timeout=5) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    for result in soup.find_all('div', class_='result'):
                        snippet_tag = result.find('a', class_='result__snippet')
                        snippet_text = snippet_tag.get_text().strip() if snippet_tag else ""
                        
                        if is_element_query:
                            found_elem = detect_element_in_text(snippet_text)
                            if found_elem:
                                return found_elem

                        title_tag = result.find('a', class_='result__title')
                        title_text = title_tag.get_text().strip() if title_tag else ""
                        
                        quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title_text)
                        for match in quoted_matches:
                            ans = parse_extracted_phrase(match, "element" if is_element_query else None)
                            if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                                return ans
                                
                        if '|' in title_text:
                            possible_name = title_text.split('|')[0].strip()
                            ans = parse_extracted_phrase(possible_name, "element" if is_element_query else None)
                            if ans and ans.lower() not in ["genshin impact", "furina", "fandom", "wiki"]:
                                return ans

                        match = re.search(r'(?:là|có tên là|tên là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9\s\-_]{2,25})', snippet_text, re.IGNORECASE)
                        if match:
                            ans = parse_extracted_phrase(match.group(1), "element" if is_element_query else None)
                            if ans:
                                return ans
        except Exception:
            pass

    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    is_element_query = "nguyên tố" in clean_question.lower()

    ans_fandom = await fetch_fandom_api(clean_question, is_element_query)
    if ans_fandom:
        print(f"✅ [KẾT QUẢ FANDOM]: {ans_fandom}\n============================================================\n", flush=True)
        return ans_fandom

    ans_web = await fetch_web_search(clean_question, is_element_query)
    if ans_web:
        print(f"✅ [KẾT QUẢ WEB SEARCH]: {ans_web}\n============================================================\n", flush=True)
        return ans_web

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
