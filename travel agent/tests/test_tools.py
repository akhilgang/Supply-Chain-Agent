"""
Unit tests for tool functions - using real API calls
"""

import pytest
import os
from app.tools.weather import WeatherTools
from app.tools.fx import FxTools
from app.tools.search import SearchTools
from app.tools.card import CardTools


class TestWeatherTool:
    """Test cases for weather tool - using real API calls"""
    
    def test_get_weather_success(self):
        """Test successful weather data retrieval with real API"""
        weather_tool = WeatherTools()
        result = weather_tool.get_weather("Paris")

        # Verify real API response - now returns summary string
        assert isinstance(result, str)
        assert "Paris" in result
        assert "°C" in result

    def test_get_weather_different_locations(self):
        """Test weather tool with different locations"""
        weather_tool = WeatherTools()

        # Test with New York
        result_ny = weather_tool.get_weather("New York")
        assert isinstance(result_ny, str)
        assert "New York" in result_ny

        # Test with Tokyo
        result_tokyo = weather_tool.get_weather("Tokyo")
        assert isinstance(result_tokyo, str)
        assert "Tokyo" in result_tokyo


class TestFxTool:
    """Test cases for FX tool - using real API calls"""
    
    def test_convert_fx_success(self):
        """Test successful currency conversion with real API"""
        fx_tool = FxTools()
        result = fx_tool.convert_fx(100, "USD", "EUR")
        
        # Verify real API response structure
        assert 'amount' in result or 'rates' in result
        if 'amount' in result:
            assert result['amount'] == 100.0
        if 'base' in result:
            assert result['base'] == 'USD'
        if 'rates' in result:
            assert 'EUR' in result['rates']
    
    def test_convert_fx_different_currencies(self):
        """Test FX tool with different currency pairs"""
        fx_tool = FxTools()
        
        # Test USD to GBP
        result_gbp = fx_tool.convert_fx(100, "USD", "GBP")
        assert 'amount' in result_gbp or 'rates' in result_gbp
        
        # Test USD to JPY
        result_jpy = fx_tool.convert_fx(100, "USD", "JPY")
        assert 'amount' in result_jpy or 'rates' in result_jpy


class TestSearchTool:
    """Test cases for search tool - using real API calls"""
    
    @pytest.mark.skipif(
        not all([
            os.getenv("PROJECT_ENDPOINT"),
            os.getenv("AGENT_ID"),
            os.getenv("BING_CONNECTION_ID")
        ]),
        reason="Missing Azure AI Project configuration"
    )
    def test_web_search_success(self):
        """Test successful web search with real API"""
        search_tool = SearchTools()
        result = search_tool.web_search("best restaurants Paris", 5)
        
        # Verify real API response structure
        assert isinstance(result, list)
        assert len(result) > 0
        assert 'title' in result[0]
        assert 'url' in result[0]
        assert 'snippet' in result[0]
    
    def test_web_search_missing_config(self):
        """Test web search with missing configuration"""
        # Temporarily clear env vars if they exist
        original_endpoint = os.environ.pop("PROJECT_ENDPOINT", None)
        original_agent = os.environ.pop("AGENT_ID", None)
        original_connection = os.environ.pop("BING_CONNECTION_ID", None)
        
        try:
            search_tool = SearchTools()
            result = search_tool.web_search("test query", 5)
            
            assert len(result) == 1
            assert "Missing configuration" in result[0]['title']
        finally:
            # Restore env vars if they existed
            if original_endpoint:
                os.environ["PROJECT_ENDPOINT"] = original_endpoint
            if original_agent:
                os.environ["AGENT_ID"] = original_agent
            if original_connection:
                os.environ["BING_CONNECTION_ID"] = original_connection
    
    @pytest.mark.skipif(
        not all([
            os.getenv("PROJECT_ENDPOINT"),
            os.getenv("AGENT_ID"),
            os.getenv("BING_CONNECTION_ID")
        ]),
        reason="Missing Azure AI Project configuration"
    )
    def test_web_search_different_queries(self):
        """Test search tool with different query types"""
        search_tool = SearchTools()
        
        # Test travel query
        result_travel = search_tool.web_search("luxury hotels in Dubai", 3)
        assert isinstance(result_travel, list)
        if len(result_travel) > 0:
            assert 'title' in result_travel[0]
        
        # Test restaurant query
        result_restaurant = search_tool.web_search("best sushi restaurants Tokyo", 3)
        assert isinstance(result_restaurant, list)
        if len(result_restaurant) > 0:
            assert 'title' in result_restaurant[0]


class TestCardTool:
    """Test cases for card tool"""

    def test_recommend_card_success(self):
        """Test successful card recommendation"""
        card_tool = CardTools()
        result = card_tool.recommend_card("dining", "France")

        assert 'best' in result
        assert 'explanation' in result
        assert 'card' in result['best']
        assert 'benefit' in result['best']
        assert 'fx_fee' in result['best']

    def test_recommend_card_different_countries(self):
        """Test card recommendation for different countries"""
        card_tool = CardTools()
        result_france = card_tool.recommend_card("dining", "France")
        result_japan = card_tool.recommend_card("dining", "Japan")

        # Both should return valid results
        assert 'best' in result_france
        assert 'best' in result_japan
        assert 'card' in result_france['best']
        assert 'card' in result_japan['best']

    def test_recommend_card_different_categories(self):
        """Test card recommendation for different spending categories"""
        card_tool = CardTools()
        result_dining = card_tool.recommend_card("dining", "France")
        result_travel = card_tool.recommend_card("travel", "France")

        # Both should return valid results
        assert 'best' in result_dining
        assert 'best' in result_travel
        assert 'card' in result_dining['best']
        assert 'card' in result_travel['best']
