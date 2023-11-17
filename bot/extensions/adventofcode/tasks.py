import asyncio
import datetime as dt
import logging
from datetime import datetime

import discord
import pytz
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

from bot import core
from bot.config import settings
from bot.services import http

log = logging.getLogger(__name__)

aoc_time = dt.time(hour=0, minute=0, second=1, tzinfo=pytz.timezone("EST"))
YEAR = datetime.now(tz=pytz.timezone("EST")).year


class AdventOfCodeTasks(commands.Cog):
    """Tasks for the Advent of Code cog."""

    def __init__(self, bot: core.DiscordBot):
        self.bot = bot
        self.daily_puzzle.start()

    def cog_unload(self):
        self.daily_puzzle.cancel()

    @property
    def channel(self) -> discord.TextChannel:
        return self.bot.get_channel(settings.aoc.channel_id)

    @tasks.loop(time=aoc_time)
    async def daily_puzzle(self):
        """Post the daily Advent of Code puzzle"""

        day = datetime.now(tz=pytz.timezone("EST")).day
        month = datetime.now(tz=pytz.timezone("EST")).month
        if day > 25 or month != 12:
            return

        puzzle_url = f"https://adventofcode.com/{YEAR}/day/{day}"
        raw_html = None
        for retry in range(4):
            async with http.session.get(puzzle_url, raise_for_status=False) as resp:
                if resp.status == 200:
                    raw_html = await resp.text()
                    break
            await asyncio.sleep(10)

        if not raw_html:
            return await self.channel.send(
                f"<@&{settings.aoc.role_id}> Good morning! Day {day} is ready to be attempted."
                f"View it online now at {puzzle_url}. Good luck!",
                allowed_mentions=discord.AllowedMentions(roles=True),
            )

        soup = BeautifulSoup(raw_html, "html.parser")
        article = soup.find("article", class_="day-desc")
        title = article.find("h2").text.replace("---", "").strip()
        desc = article.find("p").text.strip()

        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.red(),
            url=puzzle_url,
            timestamp=datetime.now(tz=pytz.timezone("EST")).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        embed.set_author(
            name="Advent Of Code", url="https://adventofcode.com", icon_url="https://adventofcode.com/favicon.png"
        )

        await self.channel.send(
            f"<@&{settings.aoc.role_id}> Good morning! Day {day} is ready to be attempted.",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

    @daily_puzzle.error
    async def daily_puzzle_error(self, _error: Exception):
        """Logs any errors that occur during the daily puzzle task"""
        await self.bot.on_error("daily_puzzle")
