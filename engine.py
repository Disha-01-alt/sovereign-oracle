import os
import feedparser
from groq import Groq
from neo4j import GraphDatabase
from datetime import datetime
import time

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
db_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_geopolitical_analysis(headline):
    """The Intelligence Layer: Uses the NEWEST Llama 3.3 model."""
    prompt = f"""
    Analyze this news headline for geopolitical risk in the mining sector: "{headline}"
    Identify:
    1. Primary Country involved.
    2. The Mineral (Lithium/Copper/Nickel/Rare Earth).
    3. Risk Score (1-10).
    4. Historical Note: What past event does this repeat?
    Format response EXACTLY as: Country | Mineral | Score | HistoricalNote
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", # UPDATED MODEL
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def save_to_graph(headline, analysis, link):
    """The Memory Layer: Stores the connection."""
    if not analysis: return
    
    try:
        parts = analysis.split("|")
        if len(parts) < 4: return
        country, mineral, score, note = [p.strip() for p in parts]

        with db_driver.session() as session:
            session.run("""
                MERGE (c:Country {name: $country})
                MERGE (m:Mineral {name: $mineral})
                CREATE (a:Article {title: $title, link: $link, risk: $score, history: $note, date: $date})
                MERGE (a)-[:AFFECTS_SUPPLY_IN]->(c)
                MERGE (a)-[:CONCERNS_RESOURCE]->(m)
            """, country=country, mineral=mineral, title=headline, link=link, 
                 score=score, note=note, date=datetime.now().strftime("%Y-%m-%d"))
            print(f"✅ Success: {headline[:50]}... [Risk: {score}]")
    except Exception as e:
        print(f"Database Error: {e}")

def run_oracle():
    rss_url = "https://news.google.com/rss/search?q=lithium+mining+geopolitics+tax+OR+copper+strike"
    feed = feedparser.parse(rss_url)

    print("DEBUG: Feed entries =", len(feed.entries))

    for entry in feed.entries[:10]:
        print("DEBUG: Headline =", entry.title)
        analysis = get_geopolitical_analysis(entry.title)
        save_to_graph(entry.title, analysis, entry.link)
        time.sleep(1)

if __name__ == "__main__":
    run_oracle()
    db_driver.close()