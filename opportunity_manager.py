"""
Opportunity Manager Module
Analyzes local events and inventory to generate smart business tips.
"""
import os
from openai import OpenAI
import json
from supabase_client import get_stock_levels
from event_scanner import scan_local_events
import asyncio

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def analyze_opportunities(user_id, latitude, longitude, city, area):
    """
    1. Scans for events near the user.
    2. Fetches user's current inventory.
    3. Uses AI to match events with inventory needs.
    """
    try:
        # 1. Scan for events
        print(f"DEBUG_OPP: Scanning events for {area}, {city}...")
        raw_events = scan_local_events(city, area)
        
        if not raw_events:
            return "कोई विशेष स्थानीय ईवेंट नहीं मिला, लेकिन सदाबहार आइटम जैसे दूध और ब्रेड का स्टॉक चेक करें।"

        # 2. Get User Inventory
        print(f"DEBUG_OPP: Fetching inventory for {user_id}...")
        stock_items = await get_stock_levels(user_id)
        
        # Format inventory for AI
        inventory_str = "Current Inventory:\n"
        if stock_items:
            for item in stock_items:
                inventory_str += f"- {item['item_name']}: {item['quantity']} {item['unit']}\n"
        else:
            inventory_str = "Inventory is empty/unknown."

        # Format events for AI
        events_str = "Found Local Events/News:\n"
        for e in raw_events[:10]: # Limit to top 10 to save tokens
            events_str += f"- {e['title']}: {e['snippet']}\n"

        # 3. AI Analysis
        print("DEBUG_OPP: Sending data to AI for analysis...")
        
        prompt = f"""
        You are a smart business advisor for a small Kirana store (grocery shop) in {area}, {city}.
        
        {events_str}
        
        {inventory_str}
        
        Task:
        1. Identify **ONLY REAL, SPECIFIC LOCAL EVENTS** from the list that will impact a grocery store (e.g., a specific festival date, a cricket match nearby, a wedding season peak, a local fair/mela, or a protest/rally).
        2. **STRICTLY IGNORE** generic seasonal advice like "It is winter so sell tea" unless there is a specific event.
        3. If no specific local event is found, simply state: "वर्तमान में आपके क्षेत्र में कोई विशेष स्थानीय इवेंट नहीं मिला है।"
        
        For each VALID event found:
        - Explain the event clearly.
        - **Think like a smart shopkeeper:** What will people actually buy *during* or *before* this event?
          - **Sports/Marathon:** Water bottles, Energy drinks (Glucon-D, Gatorade), Juices, Bananas, Biscuits. (NOT raw dal/rice).
          - **Festivals:** Sweets, Ghee, Sugar, Maida, Gift packs.
          - **Protests/Rallies:** Water pouches, Chips, Biscuits.
        - Suggest items to **SELL** (from Current Inventory if applicable).
        - Suggest items to **ORDER** (Critical high-demand items for this specific event, even if not currently tracked).
        - Explain **WHY** this specific event creates a profit opportunity.
        
        Output Format (in Hindi, professional but friendly):
        Start with a greeting mentioning the location.
        
        If events are found:
        🎯 **[Event Name]**
        💡 **Opportunity:** [Why it matters]
        ✅ **Sell from Stock:** [Relevant items from inventory]
        📦 **Order Now:** [High-demand items to stock up on for this event]
        
        If NO events are found:
        "वर्तमान में {area} में कोई विशेष स्थानीय इवेंट (जैसे मेला, मैच, या त्यौहार) नहीं मिला है जो आपके व्यापार को प्रभावित करे। हम लगातार स्कैन कर रहे हैं।"
        """

        response = client.chat.completions.create(
            model="gpt-4o", # Using a smart model for reasoning
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant for Indian shopkeepers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        analysis = response.choices[0].message.content
        return analysis

    except Exception as e:
        print(f"ERROR_OPP: {e}")
        return "अभी जानकारी उपलब्ध नहीं है। कृपया थोड़ी देर बाद प्रयास करें।"
