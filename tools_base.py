from livekit.agents import function_tool
from tools import get_weather, get_sports_score
from music_tool import play_music, pause_music, resume_music, stop_music
from news_utils import fetch_news, format_articles, KENYA_COUNTIES, EAST_AFRICA_COUNTRIES

# -------------------------
# News Tool
# -------------------------
@function_tool
async def news_tool(query: str):
    text_lower = query.lower()

    for county in KENYA_COUNTIES:
        if county in text_lower:
            articles = fetch_news(query=county.title())
            return f"📰 Top news from {county.title()}:\n\n{format_articles(articles)}"

    for country in EAST_AFRICA_COUNTRIES:
        if country in text_lower:
            articles = fetch_news(query="East Africa")
            return f"📰 Top East Africa News:\n\n{format_articles(articles)}"

    if "kenya" in text_lower:
        articles = fetch_news(country="ke")
        return f"📰 Top Kenya News:\n\n{format_articles(articles)}"

    if "global" in text_lower or "world" in text_lower:
        articles = fetch_news(query="World")
        return f"📰 Top Global News:\n\n{format_articles(articles)}"

    return "No relevant news found."

# -------------------------
# Weather Tool
# -------------------------
@function_tool
async def weather_tool(location: str):
    return get_weather(location)

# -------------------------
# Sports Tool
# -------------------------
@function_tool
async def sports_tool(team: str):
    return get_sports_score(team)

# -------------------------
# Music Tools
# -------------------------
@function_tool
async def play_music_tool(song: str):
    return play_music(song)

@function_tool
async def pause_music_tool():
    return pause_music()

@function_tool
async def resume_music_tool():
    return resume_music()

@function_tool
async def stop_music_tool():
    return stop_music()