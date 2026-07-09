#!/usr/bin/env python3
"""
Quick Start Chat Script
Run this to start chatting with the travel agent!
"""

import os
import sys
import json
import asyncio
from app.main import run_request
from app.memory import ShortTermMemory

def main():
    """Interactive chat interface for the travel agent"""
    print("🚀 Travel Agent Chat Interface")
    print("=" * 50)
    print("Welcome! I'm your AI travel concierge.")
    print("Tell me about your travel plans and I'll help you plan your trip!")
    print()
    print("Commands:")
    print("  help    - Show this help message")
    print("  status  - Show system status")
    print("  clear   - Clear the screen")
    print("  quit    - Exit the chat")
    print()

    # Initialize session memory (persists across conversation)
    memory = ShortTermMemory(max_items=20, max_tokens=8000)
    
    # Check for .env file
    if not os.path.exists(".env"):
        print("⚠️  Warning: No .env file found!")
        print("   Make sure to set up your environment variables.")
        print("   See env.example for reference.")
        print()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Safe travels!")
                break
            elif user_input.lower() == 'help':
                print("\n📖 Help:")
                print("  Just tell me about your travel plans!")
                print("  Example: 'I want to go to Paris from June 1-8 with my BankGold card'")
                print("  I'll help you with weather, restaurants, currency, and card recommendations!")
                continue
            elif user_input.lower() == 'status':
                print("\n🔍 System Status:")
                print("  ✅ Travel Agent: Ready")
                print("  ✅ Tools: Weather, FX, Search, Card, Knowledge")
                print("  ✅ Memory: Short-term and Long-term")
                print("  ✅ RAG: Vector search enabled")
                continue
            elif user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            elif not user_input:
                continue
            
            # Process the request with session memory
            print("\n🤖 Agent: Let me help you plan your trip...")
            result = asyncio.run(run_request(user_input, memory=memory))
            
            # Parse and display the result
            try:
                plan_data = json.loads(result)
                display_plan(plan_data)
            except json.JSONDecodeError:
                print("❌ Error: Could not parse the response")
                print(f"Raw response: {result}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Chat stopped. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'help' for assistance.")

def display_plan(plan_data):
    """Display the travel plan in a formatted way"""
    # Handle both old format (plan) and new format (trip_plan with Pydantic validation)
    if "trip_plan" in plan_data:
        plan = plan_data["trip_plan"]
    elif "plan" in plan_data:
        plan = plan_data["plan"]
    elif "raw_response" in plan_data:
        # Fallback for unvalidated responses
        print("\n📝 TRAVEL RECOMMENDATIONS")
        print("-" * 30)
        print(plan_data["raw_response"])
        print("\n⚠️  Note: Response was not validated with Pydantic")
        if "validation_error" in plan_data.get("metadata", {}):
            print(f"   Error: {plan_data['metadata']['validation_error']}")
        return
    else:
        print("❌ Error: Invalid plan format")
        return

    # Check if we have agent_response at root level (for backward compatibility)
    agent_response = plan_data.get("agent_response", "")
    
    print("\n" + "="*60)
    print("🎯 TRAVEL PLAN")
    print("="*60)
    
    # Destination and dates
    print(f"📍 Destination: {plan.get('destination', 'N/A')}")
    print(f"📅 Travel Dates: {plan.get('travel_dates', plan.get('dates', 'N/A'))}")
    print()

    # Show Pydantic validation status
    if plan_data.get("metadata", {}).get("data_quality") == "validated_with_pydantic":
        print("✅ Response validated with Pydantic")
        print()

    # Agent summary (from agentic loop) - only show if no structured data
    summary = plan.get('summary', agent_response)
    if summary and not plan.get('results'):
        print("📝 TRAVEL RECOMMENDATIONS")
        print("-" * 30)
        print(summary)
        print()
    
    # Weather
    if 'weather' in plan and plan['weather']:
        weather = plan['weather']
        print("🌤️  WEATHER")
        print("-" * 30)
        print(f"Temperature: {weather.get('temperature_c', 'N/A')}°C")
        print(f"Conditions: {weather.get('conditions', 'N/A')}")
        print(f"Recommendation: {weather.get('recommendation', 'N/A')}")
        print()

    # Search Results (restaurants, hotels, attractions from Pydantic model)
    if 'results' in plan and plan['results']:
        print("🔍 SEARCH RESULTS")
        print("-" * 30)
        for i, result in enumerate(plan['results'][:5], 1):
            category_emoji = {
                'restaurant': '🍽️',
                'hotel': '🏨',
                'event': '🎭',
                'general': '📍'
            }.get(result.get('category', 'general'), '📍')

            print(f"{i}. {category_emoji} {result.get('title', 'N/A')}")
            if result.get('snippet'):
                print(f"   {result['snippet']}")
            if result.get('url'):
                print(f"   🔗 {result['url']}")
            if result.get('rating'):
                print(f"   ⭐ Rating: {result['rating']}/5")
            if result.get('price_range'):
                print(f"   💰 Price: {result['price_range']}")
            print()
        print()

    # Restaurants (for backward compatibility with old format)
    elif 'restaurants' in plan and plan['restaurants']:
        print("🍽️  RESTAURANTS")
        print("-" * 30)
        for i, restaurant in enumerate(plan['restaurants'][:3], 1):
            print(f"{i}. {restaurant.get('name', 'N/A')}")
            if restaurant.get('cuisine'):
                print(f"   Cuisine: {restaurant['cuisine']}")
            if restaurant.get('rating'):
                print(f"   Rating: {restaurant['rating']}/5")
            if restaurant.get('price_range'):
                print(f"   Price: {restaurant['price_range']}")
        print()
    
    # Card recommendation
    if 'card_recommendation' in plan and plan['card_recommendation']:
        card = plan['card_recommendation']
        print("💳 CARD RECOMMENDATION")
        print("-" * 30)
        print(f"Card: {card.get('card', 'N/A')}")
        print(f"Benefit: {card.get('benefit', 'N/A')}")
        print(f"FX Fee: {card.get('fx_fee', 'N/A')}")
        print()
    
    # Currency info
    if 'currency_info' in plan and plan['currency_info']:
        currency = plan['currency_info']
        print("💰 CURRENCY INFO")
        print("-" * 30)
        print(f"Sample Meal (USD): ${currency.get('sample_meal_usd', 'N/A')}")
        if currency.get('sample_meal_eur'):
            print(f"Sample Meal (EUR): €{currency['sample_meal_eur']}")
        if currency.get('usd_to_eur'):
            print(f"Exchange Rate: 1 USD = {currency['usd_to_eur']} EUR")
        print(f"Points Earned: {currency.get('points_earned', 'N/A')}")
        print()
    
    # Next steps
    if 'next_steps' in plan and plan['next_steps']:
        print("📋 NEXT STEPS")
        print("-" * 30)
        for i, step in enumerate(plan['next_steps'], 1):
            print(f"{i}. {step}")
        print()
    
    # Citations
    if 'citations' in plan and plan['citations']:
        print("📚 SOURCES")
        print("-" * 30)
        for i, citation in enumerate(plan['citations'][:3], 1):
            print(f"{i}. {citation}")
        print()
    
    print("="*60)

if __name__ == "__main__":
    main()
