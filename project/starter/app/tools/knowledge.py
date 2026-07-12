"""
Knowledge Base Tool for Credit Card Perks and Policies
Provides RAG-based search over curated credit card benefits and travel policies.
"""

import logging
from typing import List, Dict, Any
from semantic_kernel.functions import kernel_function
from app.knowledge_base import search_card_benefits, get_lounge_access_info, get_card_recommendation
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

class KnowledgeTools:
    """Tools for searching credit card knowledge base and policies"""
    
    @kernel_function(
        description="Search for credit card benefits and policies",
        name="search_knowledge"
    )
    async def search_knowledge(
        self, 
        query: str, 
        card_name: str = None, 
        category: str = None,
        country: str = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for credit card benefits and policies.
        
        Args:
            query: Search query for RAG retrieval
            card_name: Specific card name to filter by
            category: Benefit category (dining, travel, lounge, fx, etc.)
            country: Country for local information
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant knowledge base entries
        """
        try:
            logger.info(f"Searching knowledge base: {query}")
            
            # First try RAG retrieval for semantic search
            rag_results = []
            try:
                rag_results = await retrieve(query, k=max_results, partition_key="cards")
                logger.info(f"RAG retrieved {len(rag_results)} results")
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
            
            # Also search structured knowledge base
            structured_results = search_card_benefits(card_name, category, country)
            
            # Combine and deduplicate results
            all_results = []
            seen_content = set()
            
            # Add RAG results first (they're more relevant to the query)
            for result in rag_results:
                content = result.get('content', '')
                if content and content not in seen_content:
                    all_results.append({
                        "content": content,
                        "metadata": result.get('metadata', {}),
                        "source": "rag_knowledge_base",
                        "relevance_score": result.get('score', 0.0)
                    })
                    seen_content.add(content)
            
            # Add structured results
            for result in structured_results:
                content = f"{result['benefit']}: {result['details']}"
                if content not in seen_content:
                    all_results.append({
                        "content": content,
                        "metadata": {
                            "card_name": result['card_name'],
                            "category": result['category'],
                            "benefit": result['benefit']
                        },
                        "source": "structured_knowledge_base",
                        "relevance_score": 1.0  # Structured results are always relevant
                    })
                    seen_content.add(content)
            
            # Sort by relevance score and limit results
            all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return all_results[:max_results]
            
        except Exception as e:
            logger.error(f"❌ Failed to search knowledge base: {e}")
            return [{
                "content": f"Error searching knowledge base: {e}",
                "metadata": {},
                "source": "error",
                "relevance_score": 0.0
            }]
    
    @kernel_function(
        description="Get specific credit card recommendation based on usage",
        name="get_card_recommendation"
    )
    def get_card_recommendation(
        self,
        card_name: str,
        category: str,
        amount: float,
        country: str = None
    ) -> Dict[str, Any]:
        """
        Get specific card recommendation with benefits and calculations.
        
        Args:
            card_name: Name of the credit card
            category: Spending category (dining, travel, etc.)
            amount: Transaction amount
            country: Country where transaction will occur
            
        Returns:
            Card recommendation with benefits and calculations
        """
        try:
            logger.info(f"Getting card recommendation for {card_name} - {category} - ${amount}")
            
            recommendation = get_card_recommendation(card_name, category, amount, country)
            
            logger.info(f"Card recommendation: {recommendation['recommendation']}")
            return recommendation
            
        except Exception as e:
            logger.error(f"❌ Failed to get card recommendation: {e}")
            return {
                "card": card_name,
                "benefit": "Error retrieving benefits",
                "fx_fee": "Unknown",
                "points_earned": 0,
                "recommendation": f"Error getting recommendation for {card_name}: {e}"
            }
    
    @kernel_function(
        description="Get lounge access information for airports",
        name="get_lounge_access"
    )
    def get_lounge_access(
        self,
        airport_code: str = None,
        card_name: str = None
    ) -> Dict[str, Any]:
        """
        Get lounge access information for specific airport or general info.
        
        Args:
            airport_code: Specific airport code (e.g., 'CDG', 'JFK')
            card_name: Credit card name to check lounge benefits
            
        Returns:
            Lounge access information
        """
        try:
            logger.info(f"Getting lounge access info for {airport_code or 'general'}")
            
            # Get general lounge info
            lounge_info = get_lounge_access_info(airport_code)
            
            # Add card-specific benefits if provided
            if card_name:
                card_benefits = search_card_benefits(card_name, "lounge")
                if card_benefits:
                    lounge_info["card_benefits"] = card_benefits
            
            logger.info(f"Found lounge access info: {lounge_info.get('name', 'General Priority Pass')}")
            return lounge_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get lounge access info: {e}")
            return {
                "error": f"Failed to get lounge access information: {e}",
                "name": "Unknown",
                "location": "Unknown",
                "hours": "Unknown"
            }
    
    @kernel_function(
        description="Get travel tips and local information for a country",
        name="get_travel_tips"
    )
    def get_travel_tips(
        self,
        country: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Get travel tips and local information for a specific country.
        
        Args:
            country: Country name
            category: Information category (dining, payment, culture, etc.)
            
        Returns:
            Travel tips and local information
        """
        try:
            logger.info(f"Getting travel tips for {country} - {category}")
            
            # Search for country-specific information
            tips = search_card_benefits(country=country)
            
            # Filter by category if specified
            if category != "general":
                tips = [tip for tip in tips if category.lower() in tip.get('category', '').lower()]
            
            if tips:
                return {
                    "country": country,
                    "category": category,
                    "tips": tips,
                    "source": "knowledge_base"
                }
            else:
                return {
                    "country": country,
                    "category": category,
                    "tips": [{"benefit": "No specific tips found", "details": "General travel advice applies"}],
                    "source": "knowledge_base"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get travel tips: {e}")
            return {
                "country": country,
                "category": category,
                "tips": [{"benefit": "Error", "details": f"Failed to get travel tips: {e}"}],
                "source": "error"
            }