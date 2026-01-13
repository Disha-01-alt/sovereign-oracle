import os
import feedparser
from groq import Groq
from neo4j import GraphDatabase
from datetime import datetime
import time
from dotenv import load_dotenv

# Load variables from .env if running locally, otherwise from Environment Variables
load_dotenv()

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
db_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_geopolitical_analysis(headline):
    """The Intelligence Layer: Strict Data Extraction."""
    system_prompt = "You are a data-extraction bot. You output ONLY the format: Country | Mineral | Score | HistoricalNote. No conversation. No explanations."
    user_prompt = f"Analyze this headline: '{headline}'. If no country/mineral is found, use 'Global' and 'Diversified'."

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 # Low temperature for consistent formatting
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def save_to_graph(headline, analysis, link):
    """The Memory Layer: Stores patterns and tracks Hype."""
    if not analysis or "|" not in analysis: return
    
    try:
        parts = analysis.split("|")
        if len(parts) < 4: return
        country, mineral, score, note = [p.strip() for p in parts]

        with db_driver.session() as session:
            # 1. Calculate Hype (Count recent articles on this mineral/country)
            hype_res = session.run("""
                MATCH (m:Mineral {name: $mineral})<-[:CONCERNS_RESOURCE]-(a:Article)
                WHERE a.date = $date
                RETURN count(a) as hype_count
            """, mineral=mineral, date=datetime.now().strftime("%Y-%m-%d")).single()
            
            hype_score = (hype_res['hype_count'] or 0) + 1

            # 2. Save with Relationships
            session.run("""
                MERGE (c:Country {name: $country})
                MERGE (m:Mineral {name: $mineral})
                CREATE (a:Article {
                    title: $title, 
                    link: $link, 
                    risk: toInteger($score), 
                    hype: toInteger($hype),
                    history: $note, 
                    date: $date,
                    timestamp: datetime()
                })
                MERGE (a)-[:AFFECTS_SUPPLY_IN]->(c)
                MERGE (a)-[:CONCERNS_RESOURCE]->(m)
            """, country=country, mineral=mineral, title=headline, link=link, 
                 score=score, hype=hype_score, note=note, 
                 date=datetime.now().strftime("%Y-%m-%d"))
            
            print(f"✅ Pattern Mapped: {country} | {mineral} | Risk: {score} | Hype: {hype_score}")
    except Exception as e:
        print(f"Database Error: {e}")

def run_oracle():
    # Targeted search for your specific idea (History + Risk)
    query = "lithium+mining+policy+OR+copper+supply+disruption+OR+resource+nationalization"
    rss_url = f"https://news.google.com/rss/search?q={query}"
    feed = feedparser.parse(rss_url)

    print(f"🚀 Sovereign Intelligence Engine: Processing {min(len(feed.entries), 15)} signals...")

    for entry in feed.entries[:15]:
        analysis = get_geopolitical_analysis(entry.title)
        save_to_graph(entry.title, analysis, entry.link)
        time.sleep(0.5) # Fast processing

if __name__ == "__main__":
    run_oracle()
    db_driver.close()