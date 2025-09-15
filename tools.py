import logging
from livekit.agents import function_tool, RunContext
import requests
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
import webbrowser
import random
import time
from threading import Thread

# ------------------------------
# Weather Tool
# ------------------------------
@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Get weather without extra fluff."""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            return response.text.strip()  # Just the weather data
        return f"Weather for {city} unavailable."
    except Exception as e:
        return f"Uh, couldn't get weather for {city}."


# ------------------------------
# Web Search Tool
# ------------------------------
@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search_tool = DuckDuckGoSearchRun()
        results = await search_tool.arun(tool_input=query)
        return results
    except Exception as e:
        logging.error(f"Search error: {e}")
        return f"Uh, error searching web for '{query}'."


# ------------------------------
# Email Tool
# ------------------------------
@function_tool()
async def send_email(
    context: RunContext,
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """Send an email through Gmail."""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not gmail_user or not gmail_password:
            return "Gmail credentials not set."

        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject

        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())
        server.quit()

        return ""  # Action speaks for itself
    except Exception as e:
        logging.error(f"Email error: {e}")
        return f"Uh, email sending failed: {str(e)}"


# ------------------------------
# Sports Score Tool
# ------------------------------
@function_tool()
async def get_sports_score(context: RunContext, team: str, league: str = "soccer") -> str:
    """Open latest sports scores in browser."""
    try:
        url = f"https://www.scorebat.com/embed/generic/?q={team}"
        webbrowser.open(url)
        return ""  # Action speaks for itself
    except Exception as e:
        logging.error(f"Sports error: {e}")
        return f"Uh, failed to get sports score for {team}: {str(e)}"


# ------------------------------
# Joke Teller Tool
# ------------------------------
@function_tool()
async def tell_joke(context: RunContext) -> str:
    """Tell a random joke."""
    try:
        response = requests.get("https://v2.jokeapi.dev/joke/Any?type=single")
        if response.status_code == 200:
            joke_data = response.json()
            return joke_data.get('joke', 'No joke found, try again!')
        return "Couldn't fetch a joke right now. Try again later!"
    except Exception as e:
        logging.error(f"Joke error: {e}")
        return "My joke generator is broken. Typical."


# ------------------------------
# Timer Tool
# ------------------------------
active_timers = {}

def timer_thread(seconds, timer_id):
    time.sleep(seconds)
    active_timers[timer_id] = "DONE"

@function_tool()
async def set_timer(context: RunContext, minutes: int) -> str:
    """Set a timer for specified minutes."""
    try:
        seconds = minutes * 60
        timer_id = random.randint(1000, 9999)
        active_timers[timer_id] = "RUNNING"
        
        thread = Thread(target=timer_thread, args=(seconds, timer_id))
        thread.daemon = True
        thread.start()
        
        return ""  # Empty string - action speaks for itself
    except Exception as e:
        logging.error(f"Timer error: {e}")
        return f"Uh, failed to set timer: {str(e)}"


# ------------------------------
# Check Timer Tool
# ------------------------------
@function_tool()
async def check_timer(context: RunContext, timer_id: int) -> str:
    """Check if a timer is done."""
    status = active_timers.get(timer_id, "NOT_FOUND")
    if status == "DONE":
        del active_timers[timer_id]
        return f"Timer {timer_id} is DONE! Time's up!"
    elif status == "RUNNING":
        return f"Timer {timer_id} is still running."
    else:
        return f"Timer {timer_id} not found."


# ------------------------------
# Random Fact Tool
# ------------------------------
@function_tool()
async def random_fact(context: RunContext) -> str:
    """Share a random interesting fact."""
    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
        if response.status_code == 200:
            fact_data = response.json()
            return fact_data.get('text', 'No fact found!')
        return "Couldn't fetch a fact right now. Try again later!"
    except Exception as e:
        logging.error(f"Fact error: {e}")
        return "My fact generator is taking a nap. Try again later."


# ------------------------------
# Dictionary Tool
# ------------------------------
@function_tool()
async def define_word(context: RunContext, word: str) -> str:
    """Get definition of a word."""
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if response.status_code == 200:
            data = response.json()
            meaning = data[0]['meanings'][0]['definitions'][0]['definition']
            return f"{word}: {meaning}"
        return f"Could not find definition for '{word}'."
    except Exception as e:
        logging.error(f"Dictionary error: {e}")
        return f"Uh, error looking up '{word}'."


# ------------------------------
# Crypto Price Tool
# ------------------------------
@function_tool()
async def crypto_price(context: RunContext, coin: str = "bitcoin") -> str:
    """Get current cryptocurrency price."""
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd")
        if response.status_code == 200:
            data = response.json()
            price = data[coin]['usd']
            return f"{coin.capitalize()}: ${price:,.2f}"
        return f"Could not get price for {coin}."
    except Exception as e:
        logging.error(f"Crypto error: {e}")
        return f"Uh, error getting {coin} price."