import discord
from discord.ext import commands
import re
import pybettor as pb
import os
import logging
import math
from pybettor.convert_odds import convert_odds
from pybettor.implied_prob import implied_prob
from pybettor.kelly_bet import kelly_bet
from flask import Flask#Not needed tbh
from threading import Thread

# Set up logging for easier debugging
logging.basicConfig(level=logging.INFO)

# Bot's intents to enable receiving messages
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to calculate EV%, Kelly Wager, and other shit
def calculate_summary(book_odds_str, fair_odds_str, bankroll=1000):
    try:
        book_odds_num = float(book_odds_str)
        fair_odds_num = float(fair_odds_str)

        book_odds = convert_odds(book_odds_num, cat_in='us', cat_out='dec')[0]
        fair_odds = convert_odds(fair_odds_num, cat_in='us', cat_out='dec')[0]

        book_prob = implied_prob(book_odds, category='dec')[0]
        fair_prob = implied_prob(fair_odds, category='dec')[0]

        ev_percent = ((fair_prob / book_prob) - 1) * 100
        ev_percent = math.ceil(ev_percent * 10) / 10

        unit_size = bankroll * 0.01

        full_kelly_wager = round(kelly_bet(unit_size, fair_prob, book_odds_num, category='us', kelly_factor=1), 2)
        half_kelly_wager = round(kelly_bet(unit_size, fair_prob, book_odds_num, category='us', kelly_factor=2), 2)
        quarter_kelly_wager = round(kelly_bet(unit_size, fair_prob, book_odds_num, category='us', kelly_factor=4), 2)

        full_kelly_units = f"{full_kelly_wager / unit_size:.2f}"
        quarter_kelly_units = f"{quarter_kelly_wager / unit_size:.2f}"

        fair_bet_percentage = round(fair_prob * 100, 2)
        fair_value_odds = convert_odds(fair_odds, cat_in='dec', cat_out='us')[0]

        return {
            'ev_percent': ev_percent,
            'full_kelly_units': full_kelly_units,
            'quarter_kelly_units': quarter_kelly_units,
            'fair_value_odds': fair_value_odds,
            'fair_bet_percentage': fair_bet_percentage
        }
    except Exception as e:
        logging.error(f"Error in calculating summary metrics: {e}")
        return None

# Event for when the bot is ready
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')

# Event for when a message is sent in the server
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    odds_pattern = r"(-?\d+)\s*:\s*(-?\d+)"
    match = re.search(odds_pattern, message.content)

    if match:
        book_odds_str = match.group(1)
        fair_odds_str = match.group(2)

        summary = calculate_summary(book_odds_str, fair_odds_str)

        if summary:
            embed = discord.Embed(title="EV Stats", color=0x2ECC71)  # Green 

            # Input section
            embed.add_field(name="Input", value=f"Input: {book_odds_str}: {fair_odds_str}\nPayout Odds: {'+' if int(book_odds_str) > 0 else ''}{book_odds_str}", inline=False)

            # EV Stats section
            embed.add_field(name="EV Stats (Worst-Case)", value=(
                
                f"FV: {'+' if int(summary['fair_value_odds']) > 0 else ''}{summary['fair_value_odds']}\n"
                f"EV%: {summary['ev_percent']}%\n"
            ), inline=False)

            # Kelly section
            embed.add_field(name="Kelly 💹", value=(
                f"FK: {summary['full_kelly_units']}u\n"
                f"QK: {summary['quarter_kelly_units']}u"
            ), inline=False)

            await message.channel.send(embed=embed)
        else:
            await message.channel.send("Error calculating summary metrics.")
    else:
        logging.info("No odds pattern detected.")

    await bot.process_commands(message)

# Flask Web Server to keep Replit alive/for testing crap
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    keep_alive()
    bot.run(TOKEN)
else:
    logging.error("Bot token is not set. Please check your environment variables.")
