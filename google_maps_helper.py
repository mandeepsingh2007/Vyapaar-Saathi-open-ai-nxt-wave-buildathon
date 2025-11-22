"""
Google Maps API integration for finding nearby suppliers.
"""
import os
import requests
from typing import List, Dict, Optional

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def get_nearby_suppliers(
    latitude: float,
    longitude: float,
    radius: int = 5000,  # 5km radius
    keyword: str = "wholesale supplier",
    max_results: int = 10
) -> List[Dict]:
    """
    Find nearby suppliers using Google Places API.
    
    Args:
        latitude: Shopkeeper's latitude
        longitude: Shopkeeper's longitude
        radius: Search radius in meters (default 5km)
        keyword: Search keyword (default "wholesale supplier")
        max_results: Maximum number of results to return
        
    Returns:
        List of supplier dictionaries with name, address, phone, rating, etc.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not found in environment variables")
        return []
    
    # Google Places API Nearby Search endpoint
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "keyword": keyword,
        "key": GOOGLE_MAPS_API_KEY,
        "type": "store"  # Can be: store, grocery_or_supermarket, etc.
    }
    
    try:
        print(f"DEBUG_GMAPS: Searching for suppliers near ({latitude}, {longitude}) within {radius}m")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "OK":
            print(f"ERROR_GMAPS: API returned status: {data.get('status')}")
            print(f"ERROR_GMAPS: Error message: {data.get('error_message', 'No error message')}")
            return []
        
        results = data.get("results", [])
        print(f"DEBUG_GMAPS: Found {len(results)} suppliers")
        
        suppliers = []
        for place in results[:max_results]:
            place_id = place.get("place_id")
            
            # Get detailed information including phone number
            details = get_place_details(place_id)
            
            supplier = {
                "name": place.get("name", "Unknown"),
                "address": place.get("vicinity", "Address not available"),
                "rating": place.get("rating", "N/A"),
                "total_ratings": place.get("user_ratings_total", 0),
                "place_id": place_id,
                "location": place.get("geometry", {}).get("location", {}),
                "phone": details.get("phone", "Not available"),
                "formatted_phone": details.get("formatted_phone", "Not available"),
                "website": details.get("website", ""),
                "opening_hours": details.get("opening_hours", {}),
                "is_open": details.get("is_open", None)
            }
            
            suppliers.append(supplier)
        
        return suppliers
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR_GMAPS: Request failed: {e}")
        return []
    except Exception as e:
        print(f"ERROR_GMAPS: Unexpected error: {e}")
        return []


def get_place_details(place_id: str) -> Dict:
    """
    Get detailed information about a place including phone number.
    
    Args:
        place_id: Google Place ID
        
    Returns:
        Dictionary with detailed place information
    """
    if not GOOGLE_MAPS_API_KEY:
        return {}
    
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,international_phone_number,website,opening_hours",
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "OK":
            print(f"DEBUG_GMAPS: Place details status: {data.get('status')} for place_id: {place_id}")
            return {}
        
        result = data.get("result", {})
        
        return {
            "phone": result.get("international_phone_number", ""),
            "formatted_phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "opening_hours": result.get("opening_hours", {}),
            "is_open": result.get("opening_hours", {}).get("open_now", None)
        }
        
    except Exception as e:
        print(f"ERROR_GMAPS: Failed to get place details: {e}")
        return {}


def format_suppliers_message(suppliers: List[Dict], language: str = "hi") -> str:
    """
    Format the suppliers list into a WhatsApp message.
    
    Args:
        suppliers: List of supplier dictionaries
        language: Language code (hi/en)
        
    Returns:
        Formatted message string
    """
    if not suppliers:
        if language == "hi":
            return "❌ क्षमा करें, आपके आस-पास कोई सप्लायर नहीं मिला। कृपया मैन्युअल रूप से फोन नंबर दर्ज करें।"
        else:
            return "❌ Sorry, no suppliers found nearby. Please enter phone number manually."
    
    if language == "hi":
        message = "📍 **आपके आस-पास के सप्लायर:**\n\n"
    else:
        message = "📍 **Nearby Suppliers:**\n\n"
    
    for i, supplier in enumerate(suppliers, 1):
        name = supplier.get("name", "Unknown")
        address = supplier.get("address", "N/A")
        phone = supplier.get("formatted_phone", supplier.get("phone", "Not available"))
        rating = supplier.get("rating", "N/A")
        total_ratings = supplier.get("total_ratings", 0)
        
        # Format rating display
        if rating != "N/A":
            rating_display = f"⭐ {rating}/5 ({total_ratings} reviews)"
        else:
            rating_display = "⭐ No ratings"
        
        # Format phone display
        if phone and phone != "Not available":
            phone_display = f"📞 {phone}"
        else:
            phone_display = "📞 Phone not available"
        
        message += f"**{i}. {name}**\n"
        message += f"   {phone_display}\n"
        message += f"   📍 {address}\n"
        message += f"   {rating_display}\n\n"
    
    if language == "hi":
        message += "\n💡 **सप्लायर को कॉल करने के लिए:**\n"
        message += "सप्लायर का फोन नंबर भेजें (उदाहरण: '+919876543210')"
    else:
        message += "\n💡 **To call a supplier:**\n"
        message += "Send the supplier's phone number (e.g., '+919876543210')"
    
    return message


# Example usage and testing
if __name__ == "__main__":
    # Test with Delhi coordinates
    test_lat = 28.7041
    test_lon = 77.1025
    
    print("Testing Google Maps API integration...")
    print("=" * 70)
    
    suppliers = get_nearby_suppliers(test_lat, test_lon, radius=5000, keyword="wholesale supplier")
    
    if suppliers:
        print(f"\n✅ Found {len(suppliers)} suppliers\n")
        
        # Print in Hindi format
        message_hi = format_suppliers_message(suppliers, language="hi")
        print("HINDI MESSAGE:")
        print("-" * 70)
        print(message_hi)
        
        print("\n" + "=" * 70)
        
        # Print in English format
        message_en = format_suppliers_message(suppliers, language="en")
        print("ENGLISH MESSAGE:")
        print("-" * 70)
        print(message_en)
    else:
        print("❌ No suppliers found or API error")
