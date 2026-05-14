import json
import os
import asyncio
import random
import discord

class ReactHandler:
    def __init__(self, bot, checkpoint_file, channels_file):
        self.bot = bot
        self.checkpoint_file = checkpoint_file
        self.channels_file = channels_file
        self.max_per_msg = 2
        
        # Load dữ liệu
        data = self.load_all_data()
        self.checkpoints = data["checkpoints"]
        self.current_total = data["stats"]["current_total"]
        self.limit = data["stats"]["limit"]
        
        self.auto_enabled = True
        self.is_cleaning = False
        self.queue = asyncio.Queue()
        self.target_channels = self.load_target_channels()

    def load_target_channels(self):
        if not os.path.exists(self.channels_file):
            with open(self.channels_file, "w") as f: pass
            return []
        with open(self.channels_file, "r") as f:
            return [int(line.strip()) for line in f if line.strip() and not line.startswith("#")]

    def load_all_data(self):
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    return json.load(f)
            except: pass
        return {"checkpoints": {}, "stats": {"current_total": 0, "limit": 10000}}

    def save_all_data(self):
        data = {
            "checkpoints": self.checkpoints,
            "stats": {"current_total": self.current_total, "limit": self.limit}
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(data, f, indent=4)

    async def smart_react(self, msg):
        if not self.auto_enabled or self.current_total >= self.limit:
            return

        my_reactions = [str(r.emoji) for r in msg.reactions if r.me]
        missing = [r for r in msg.reactions if str(r.emoji) not in my_reactions]

        if not missing: return

        num = min(len(missing), self.max_per_msg, self.limit - self.current_total)
        to_add = random.sample(missing, num)

        for reaction in to_add:
            try:
                await msg.add_reaction(reaction.emoji)
                self.current_total += 1
                print(f"[{msg.channel.id}] ✨ Đã thả: {self.current_total}/{self.limit}")
                self.save_all_data()
                await asyncio.sleep(random.uniform(0.5, 0.8))
            except: break

    async def reaction_worker(self):
        while True:
            msg = await self.queue.get()
            while self.is_cleaning:
                await asyncio.sleep(1)

            if self.auto_enabled and self.current_total < self.limit:
                await self.smart_react(msg)
                await asyncio.sleep(random.uniform(1.0, 2.0))
            self.queue.task_done()
