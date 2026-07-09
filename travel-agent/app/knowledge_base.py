"""
Knowledge Base for Credit Card Perks and Policies
Contains curated information about credit card benefits, lounge access, and travel policies.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CardBenefit:
    """Represents a credit card benefit or policy"""
    card_name: str
    category: str  # dining, travel, lounge, fx, etc.
    benefit: str
    details: str
    restrictions: str = ""
    source: str = "knowledge_base"

# Curated knowledge base of credit card benefits
CARD_KNOWLEDGE_BASE = [
    # BankGold Card Benefits
    CardBenefit(
        card_name="BankGold",
        category="dining",
        benefit="4x points on dining worldwide",
        details="Earn 4 points per dollar spent on dining at restaurants worldwide, including takeout and delivery",
        restrictions="Must be coded as restaurant/dining by merchant"
    ),
    CardBenefit(
        card_name="BankGold",
        category="fx",
        benefit="No foreign transaction fees",
        details="No additional fees for purchases made in foreign currencies",
        restrictions="Applies to all international transactions"
    ),
    CardBenefit(
        card_name="BankGold",
        category="travel",
        benefit="Travel insurance coverage",
        details="Comprehensive travel insurance including trip cancellation, baggage delay, and emergency medical",
        restrictions="Must use card to book travel, coverage limits apply"
    ),
    CardBenefit(
        card_name="BankGold",
        category="lounge",
        benefit="Priority Pass Select membership",
        details="Complimentary access to 1,300+ airport lounges worldwide",
        restrictions="Limited to 2 free visits per year, then $32 per visit"
    ),
    
    # BankPlatinum Card Benefits
    CardBenefit(
        card_name="BankPlatinum",
        category="dining",
        benefit="5x points on dining worldwide",
        details="Earn 5 points per dollar spent on dining at restaurants worldwide",
        restrictions="Must be coded as restaurant/dining by merchant"
    ),
    CardBenefit(
        card_name="BankPlatinum",
        category="fx",
        benefit="No foreign transaction fees",
        details="No additional fees for purchases made in foreign currencies",
        restrictions="Applies to all international transactions"
    ),
    CardBenefit(
        card_name="BankPlatinum",
        category="lounge",
        benefit="Unlimited Priority Pass membership",
        details="Unlimited complimentary access to 1,300+ airport lounges worldwide",
        restrictions="Must be primary cardholder"
    ),
    CardBenefit(
        card_name="BankPlatinum",
        category="travel",
        benefit="Concierge service",
        details="24/7 concierge service for travel planning, reservations, and assistance",
        restrictions="Available to primary cardholders only"
    ),
    CardBenefit(
        card_name="BankPlatinum",
        category="travel",
        benefit="Global Entry/TSA PreCheck credit",
        details="Up to $100 credit for Global Entry or TSA PreCheck application fee",
        restrictions="Once every 4 years, must use card to pay"
    ),
    
    # BankRewards Card Benefits
    CardBenefit(
        card_name="BankRewards",
        category="dining",
        benefit="2x points on dining",
        details="Earn 2 points per dollar spent on dining at restaurants",
        restrictions="Must be coded as restaurant/dining by merchant"
    ),
    CardBenefit(
        card_name="BankRewards",
        category="fx",
        benefit="3% foreign transaction fee",
        details="3% fee on all foreign currency transactions",
        restrictions="Applies to all international transactions"
    ),
    CardBenefit(
        card_name="BankRewards",
        category="travel",
        benefit="Basic travel insurance",
        details="Basic trip cancellation and baggage delay coverage",
        restrictions="Must use card to book travel, lower coverage limits"
    ),
    
    # General Travel Policies
    CardBenefit(
        card_name="General",
        category="policy",
        benefit="Travel notification",
        details="Notify bank of international travel to avoid card blocks",
        restrictions="Required for all international travel"
    ),
    CardBenefit(
        card_name="General",
        category="policy",
        benefit="ATM withdrawal limits",
        details="Daily ATM withdrawal limit of $500-$1,000 depending on card type",
        restrictions="Higher limits available with advance notice"
    ),
    CardBenefit(
        card_name="General",
        category="policy",
        benefit="Emergency card replacement",
        details="24/7 emergency card replacement service worldwide",
        restrictions="Fees may apply for expedited delivery"
    ),
]

# Country-specific benefits and restrictions
COUNTRY_SPECIFIC_BENEFITS = {
    "France": {
        "dining_multiplier": 1.0,  # No special multiplier for France
        "popular_cuisines": ["French", "Mediterranean", "Bistro", "Fine Dining"],
        "tipping_culture": "Service charge usually included, 5-10% extra for exceptional service",
        "payment_preference": "Credit cards widely accepted, cash for small establishments"
    },
    "Italy": {
        "dining_multiplier": 1.0,
        "popular_cuisines": ["Italian", "Pizza", "Gelato", "Wine Bars"],
        "tipping_culture": "Service charge usually included, small tip for exceptional service",
        "payment_preference": "Credit cards accepted, cash preferred for small amounts"
    },
    "Spain": {
        "dining_multiplier": 1.0,
        "popular_cuisines": ["Spanish", "Tapas", "Paella", "Sangria"],
        "tipping_culture": "Service charge usually included, small tip for exceptional service",
        "payment_preference": "Credit cards widely accepted, cash for small establishments"
    },
    "Japan": {
        "dining_multiplier": 1.0,
        "popular_cuisines": ["Japanese", "Sushi", "Ramen", "Izakaya"],
        "tipping_culture": "No tipping expected, may be considered rude",
        "payment_preference": "Cash preferred, credit cards accepted in major establishments"
    }
}

# Lounge access information
LOUNGE_ACCESS_INFO = {
    "Priority Pass": {
        "description": "Access to 1,300+ airport lounges worldwide",
        "coverage": "Global coverage in major airports",
        "amenities": ["Complimentary food and beverages", "WiFi", "Work spaces", "Showers (select locations)"],
        "access_method": "Show Priority Pass card and boarding pass"
    },
    "Airport Lounges": {
        "CDG": {
            "name": "Air France Lounge",
            "location": "Terminal 2E, Gates L-M",
            "hours": "5:30 AM - 10:30 PM",
            "amenities": ["Hot meals", "Bar service", "Showers", "Business center"]
        },
        "JFK": {
            "name": "Centurion Lounge",
            "location": "Terminal 4, near Gate A5",
            "hours": "5:00 AM - 11:00 PM",
            "amenities": ["Chef-prepared meals", "Premium bar", "Showers", "Spa services"]
        }
    }
}

def search_card_benefits(card_name: str = None, category: str = None, country: str = None) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for credit card benefits.
    
    Args:
        card_name: Specific card name to search for
        category: Benefit category (dining, travel, lounge, fx, etc.)
        country: Country-specific information
        
    Returns:
        List of matching benefits
    """
    results = []
    
    # Filter by card name and category
    for benefit in CARD_KNOWLEDGE_BASE:
        if card_name and card_name.lower() not in benefit.card_name.lower():
            continue
        if category and category.lower() not in benefit.category.lower():
            continue
            
        results.append({
            "card_name": benefit.card_name,
            "category": benefit.category,
            "benefit": benefit.benefit,
            "details": benefit.details,
            "restrictions": benefit.restrictions,
            "source": benefit.source
        })
    
    # Add country-specific information if requested
    if country and country in COUNTRY_SPECIFIC_BENEFITS:
        country_info = COUNTRY_SPECIFIC_BENEFITS[country]
        results.append({
            "card_name": "Country-Specific",
            "category": "local_info",
            "benefit": f"Travel tips for {country}",
            "details": f"Payment preferences: {country_info['payment_preference']}. Tipping: {country_info['tipping_culture']}",
            "restrictions": "",
            "source": "knowledge_base"
        })
    
    return results

def get_lounge_access_info(airport_code: str = None) -> Dict[str, Any]:
    """
    Get lounge access information for specific airport or general info.
    
    Args:
        airport_code: Specific airport code (e.g., 'CDG', 'JFK')
        
    Returns:
        Lounge access information
    """
    if airport_code and airport_code.upper() in LOUNGE_ACCESS_INFO["Airport Lounges"]:
        return LOUNGE_ACCESS_INFO["Airport Lounges"][airport_code.upper()]
    
    return LOUNGE_ACCESS_INFO["Priority Pass"]

def get_card_recommendation(card_name: str, category: str, amount: float, country: str = None) -> Dict[str, Any]:
    """
    Get specific card recommendation based on usage.

    Args:
        card_name: Name of the credit card
        category: Spending category (dining, travel, etc.)
        amount: Transaction amount
        country: Country where transaction will occur

    Returns:
        Card recommendation with benefits and calculations
    """
    benefits = search_card_benefits(card_name, category)

    # Also get FX fee info separately
    fx_benefits = search_card_benefits(card_name, "fx")

    if not benefits and not fx_benefits:
        return {
            "card": card_name,
            "benefit": "No specific benefits found",
            "fx_fee": "Unknown",
            "points_earned": 0,
            "recommendation": "Consider using a different card for better rewards"
        }

    # Calculate points earned
    points_multiplier = 0
    fx_fee = "Unknown"

    # Check category benefits for points
    for benefit in benefits:
        if "points" in benefit["benefit"].lower():
            # Extract multiplier from benefit text
            if "5x" in benefit["benefit"]:
                points_multiplier = 5
            elif "4x" in benefit["benefit"]:
                points_multiplier = 4
            elif "3x" in benefit["benefit"]:
                points_multiplier = 3
            elif "2x" in benefit["benefit"]:
                points_multiplier = 2
            elif "1x" in benefit["benefit"]:
                points_multiplier = 1

    # Check FX benefits for fee info
    for benefit in fx_benefits:
        if "foreign transaction" in benefit["benefit"].lower():
            if "no " in benefit["benefit"].lower():
                fx_fee = "None (0%)"
            elif "3%" in benefit["benefit"]:
                fx_fee = "3%"
            else:
                fx_fee = "Applies"

    points_earned = int(amount * points_multiplier)

    return {
        "card": card_name,
        "benefit": benefits[0]["benefit"] if benefits else "General rewards",
        "fx_fee": fx_fee,
        "points_earned": points_earned,
        "recommendation": f"Use {card_name} to earn {points_earned} points on this {category} purchase"
    }

# Knowledge base content for RAG ingestion
KNOWLEDGE_BASE_CONTENT = [
    {
        "content": "BankGold card offers 4x points on dining worldwide with no foreign transaction fees. Perfect for international travel and restaurant spending.",
        "metadata": {"card": "BankGold", "category": "dining", "type": "benefit"},
        "tags": ["dining", "travel", "points", "international"]
    },
    {
        "content": "BankPlatinum card provides unlimited Priority Pass lounge access and 5x points on dining. Includes concierge service and Global Entry credit.",
        "metadata": {"card": "BankPlatinum", "category": "lounge", "type": "benefit"},
        "tags": ["lounge", "concierge", "travel", "premium"]
    },
    {
        "content": "Priority Pass Select membership gives access to 1,300+ airport lounges worldwide. Show card and boarding pass for entry.",
        "metadata": {"card": "general", "category": "lounge", "type": "policy"},
        "tags": ["lounge", "airport", "access", "worldwide"]
    },
    {
        "content": "In France, credit cards are widely accepted at restaurants. Service charge is usually included, with 5-10% extra for exceptional service.",
        "metadata": {"country": "France", "category": "dining", "type": "local_info"},
        "tags": ["france", "dining", "tipping", "payment"]
    },
    {
        "content": "Travel insurance coverage includes trip cancellation, baggage delay, and emergency medical when using BankGold or BankPlatinum cards.",
        "metadata": {"card": "travel_insurance", "category": "travel", "type": "benefit"},
        "tags": ["insurance", "travel", "coverage", "emergency"]
    }
]
