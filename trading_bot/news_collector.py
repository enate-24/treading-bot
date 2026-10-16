"""News and Economic Calendar Data Collector."""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
from threading import Lock


logger = logging.getLogger(__name__)


class NewsImpact(Enum):
    """News impact levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NewsSentiment(Enum):
    """News sentiment."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class EconomicEvent:
    """Economic calendar event."""
    title: str
    country: str
    currency: str
    timestamp: datetime
    impact: NewsImpact
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    
    def is_high_impact(self) -> bool:
        """Check if event is high impact."""
        return self.impact == NewsImpact.HIGH
    
    def is_upcoming(self, minutes: int = 30) -> bool:
        """Check if event is upcoming within specified minutes."""
        now = datetime.now()
        time_diff = (self.timestamp - now).total_seconds() / 60
        return 0 <= time_diff <= minutes
    
    def beats_forecast(self) -> Optional[bool]:
        """Check if actual beats forecast."""
        if self.actual is None or self.forecast is None:
            return None
        return self.actual > self.forecast


@dataclass
class NewsArticle:
    """News article."""
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    sentiment: NewsSentiment
    relevance_score: float
    symbols: List[str]


class NewsCollector:
    """Collects news and economic calendar data from multiple sources."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize news collector.
        
        Args:
            config: Configuration with API keys and settings
        """
        self.config = config
        self.api_keys = config.get('api_keys', {})
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes
        self.lock = Lock()
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 12  # 5 requests per minute = 12 seconds
        
        logger.info("News collector initialized")
    
    def get_economic_calendar(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             currencies: Optional[List[str]] = None) -> List[EconomicEvent]:
        """Get economic calendar events.
        
        Args:
            start_date: Start date for events (default: now)
            end_date: End date for events (default: 24 hours from now)
            currencies: Filter by currencies (e.g., ['USD', 'EUR'])
            
        Returns:
            List of economic events
        """
        try:
            # Set defaults
            if start_date is None:
                start_date = datetime.now()
            if end_date is None:
                end_date = start_date + timedelta(days=1)
            
            # Check cache
            cache_key = f"calendar_{start_date}_{end_date}_{currencies}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
            
            # Fetch from multiple sources
            events = []
            
            # Try Trading Economics API
            if 'trading_economics' in self.api_keys:
                events.extend(self._fetch_trading_economics_calendar(start_date, end_date))
            
            # Try Alpha Vantage (limited calendar support)
            if 'alpha_vantage' in self.api_keys:
                events.extend(self._fetch_alpha_vantage_calendar())
            
            # Try Forex Factory (scraping or unofficial API)
            events.extend(self._fetch_forex_factory_calendar(start_date, end_date))
            
            # Filter by currencies if specified
            if currencies:
                events = [e for e in events if e.currency in currencies]
            
            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            # Cache results
            self._save_to_cache(cache_key, events)
            
            logger.info(f"Fetched {len(events)} economic events")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching economic calendar: {e}")
            return []
    
    def get_news(self, 
                 symbols: Optional[List[str]] = None,
                 keywords: Optional[List[str]] = None,
                 hours_back: int = 24) -> List[NewsArticle]:
        """Get recent news articles.
        
        Args:
            symbols: Filter by trading symbols (e.g., ['EURUSD', 'GBPUSD'])
            keywords: Filter by keywords (e.g., ['forex', 'fed', 'ecb'])
            hours_back: How many hours back to fetch news
            
        Returns:
            List of news articles
        """
        try:
            # Check cache
            cache_key = f"news_{symbols}_{keywords}_{hours_back}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
            
            articles = []
            
            # Try NewsAPI
            if 'newsapi' in self.api_keys:
                articles.extend(self._fetch_newsapi(keywords, hours_back))
            
            # Try Alpha Vantage
            if 'alpha_vantage' in self.api_keys:
                articles.extend(self._fetch_alpha_vantage_news(symbols))
            
            # Try Finnhub
            if 'finnhub' in self.api_keys:
                articles.extend(self._fetch_finnhub_news(symbols))
            
            # Filter and deduplicate
            articles = self._deduplicate_news(articles)
            
            # Sort by relevance and recency
            articles.sort(key=lambda x: (x.relevance_score, x.published_at), reverse=True)
            
            # Cache results
            self._save_to_cache(cache_key, articles)
            
            logger.info(f"Fetched {len(articles)} news articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """Get overall market sentiment.
        
        Returns:
            Dictionary with sentiment metrics
        """
        try:
            # Check cache
            cache_key = "market_sentiment"
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
            
            sentiment = {
                'overall': 'neutral',
                'fear_greed_index': 50,
                'news_sentiment': 0.0,
                'social_sentiment': 0.0,
                'timestamp': datetime.now()
            }
            
            # Get news sentiment
            recent_news = self.get_news(hours_back=6)
            if recent_news:
                bullish = sum(1 for n in recent_news if n.sentiment == NewsSentiment.BULLISH)
                bearish = sum(1 for n in recent_news if n.sentiment == NewsSentiment.BEARISH)
                total = len(recent_news)
                
                if total > 0:
                    sentiment['news_sentiment'] = (bullish - bearish) / total
            
            # Determine overall sentiment
            if sentiment['news_sentiment'] > 0.3:
                sentiment['overall'] = 'bullish'
            elif sentiment['news_sentiment'] < -0.3:
                sentiment['overall'] = 'bearish'
            else:
                sentiment['overall'] = 'neutral'
            
            # Cache results
            self._save_to_cache(cache_key, sentiment, ttl=600)  # 10 minutes
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {'overall': 'neutral', 'timestamp': datetime.now()}
    
    def has_high_impact_news_soon(self, minutes: int = 30, currencies: Optional[List[str]] = None) -> bool:
        """Check if high-impact news is coming soon.
        
        Args:
            minutes: Time window in minutes
            currencies: Filter by currencies
            
        Returns:
            True if high-impact news is upcoming
        """
        try:
            events = self.get_economic_calendar(currencies=currencies)
            
            for event in events:
                if event.is_high_impact() and event.is_upcoming(minutes):
                    logger.warning(f"High-impact news upcoming: {event.title} at {event.timestamp}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking upcoming news: {e}")
            return False
    
    def _fetch_alpha_vantage_news(self, symbols: Optional[List[str]] = None) -> List[NewsArticle]:
        """Fetch news from Alpha Vantage API."""
        try:
            api_key = self.api_keys.get('alpha_vantage')
            if not api_key:
                return []
            
            # Rate limiting
            self._wait_for_rate_limit('alpha_vantage')
            
            # Alpha Vantage news endpoint
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': api_key,
                'limit': 50
            }
            
            if symbols:
                params['tickers'] = ','.join(symbols)
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'feed' in data:
                for item in data['feed']:
                    # Parse sentiment
                    sentiment_score = float(item.get('overall_sentiment_score', 0))
                    if sentiment_score > 0.15:
                        sentiment = NewsSentiment.BULLISH
                    elif sentiment_score < -0.15:
                        sentiment = NewsSentiment.BEARISH
                    else:
                        sentiment = NewsSentiment.NEUTRAL
                    
                    article = NewsArticle(
                        title=item.get('title', ''),
                        description=item.get('summary', ''),
                        source=item.get('source', 'Alpha Vantage'),
                        url=item.get('url', ''),
                        published_at=datetime.strptime(item.get('time_published', ''), '%Y%m%dT%H%M%S'),
                        sentiment=sentiment,
                        relevance_score=float(item.get('relevance_score', 0.5)),
                        symbols=symbols or []
                    )
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage news: {e}")
            return []
    
    def _fetch_newsapi(self, keywords: Optional[List[str]] = None, hours_back: int = 24) -> List[NewsArticle]:
        """Fetch news from NewsAPI.org."""
        try:
            api_key = self.api_keys.get('newsapi')
            if not api_key:
                return []
            
            # Rate limiting
            self._wait_for_rate_limit('newsapi')
            
            # NewsAPI endpoint
            url = "https://newsapi.org/v2/everything"
            
            # Build query
            query = ' OR '.join(keywords) if keywords else 'forex OR trading OR economy'
            
            params = {
                'q': query,
                'apiKey': api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(hours=hours_back)).isoformat(),
                'pageSize': 50
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if data.get('status') == 'ok' and 'articles' in data:
                for item in data['articles']:
                    # Simple sentiment analysis based on title/description
                    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
                    sentiment = self._analyze_sentiment(text)
                    
                    article = NewsArticle(
                        title=item.get('title', ''),
                        description=item.get('description', ''),
                        source=item.get('source', {}).get('name', 'NewsAPI'),
                        url=item.get('url', ''),
                        published_at=datetime.fromisoformat(item.get('publishedAt', '').replace('Z', '+00:00')),
                        sentiment=sentiment,
                        relevance_score=0.7,  # Default relevance
                        symbols=[]
                    )
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching NewsAPI: {e}")
            return []
    
    def _fetch_finnhub_news(self, symbols: Optional[List[str]] = None) -> List[NewsArticle]:
        """Fetch news from Finnhub API."""
        try:
            api_key = self.api_keys.get('finnhub')
            if not api_key:
                return []
            
            # Rate limiting
            self._wait_for_rate_limit('finnhub')
            
            # Finnhub forex news endpoint
            url = "https://finnhub.io/api/v1/news"
            params = {
                'category': 'forex',
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data:
                sentiment = self._analyze_sentiment(f"{item.get('headline', '')} {item.get('summary', '')}")
                
                article = NewsArticle(
                    title=item.get('headline', ''),
                    description=item.get('summary', ''),
                    source=item.get('source', 'Finnhub'),
                    url=item.get('url', ''),
                    published_at=datetime.fromtimestamp(item.get('datetime', 0)),
                    sentiment=sentiment,
                    relevance_score=0.8,
                    symbols=symbols or []
                )
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching Finnhub news: {e}")
            return []
    
    def _fetch_forex_factory_calendar(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Fetch economic calendar from Forex Factory (simplified)."""
        # This would require web scraping or unofficial API
        # For now, return hardcoded major events
        
        major_events = [
            {
                'title': 'Non-Farm Payroll (NFP)',
                'country': 'US',
                'currency': 'USD',
                'impact': NewsImpact.HIGH,
                'day_of_month': 'first_friday'
            },
            {
                'title': 'Federal Reserve Interest Rate Decision',
                'country': 'US',
                'currency': 'USD',
                'impact': NewsImpact.HIGH,
                'frequency': 'every_6_weeks'
            },
            {
                'title': 'CPI (Consumer Price Index)',
                'country': 'US',
                'currency': 'USD',
                'impact': NewsImpact.HIGH,
                'frequency': 'monthly'
            }
        ]
        
        # In production, implement actual scraping or use paid API
        return []
    
    def _fetch_trading_economics_calendar(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Fetch calendar from Trading Economics API."""
        # Requires paid API key
        # Implementation would be similar to other APIs
        return []
    
    def _analyze_sentiment(self, text: str) -> NewsSentiment:
        """Simple sentiment analysis based on keywords."""
        text = text.lower()
        
        bullish_keywords = ['rise', 'gain', 'up', 'growth', 'increase', 'positive', 'strong', 'rally', 'surge', 'boost']
        bearish_keywords = ['fall', 'drop', 'down', 'decline', 'decrease', 'negative', 'weak', 'crash', 'plunge', 'cut']
        
        bullish_count = sum(1 for word in bullish_keywords if word in text)
        bearish_count = sum(1 for word in bearish_keywords if word in text)
        
        if bullish_count > bearish_count:
            return NewsSentiment.BULLISH
        elif bearish_count > bullish_count:
            return NewsSentiment.BEARISH
        else:
            return NewsSentiment.NEUTRAL
    
    def _deduplicate_news(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate news articles."""
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            title_key = article.title.lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_articles.append(article)
        
        return unique_articles
    
    def _wait_for_rate_limit(self, api_name: str) -> None:
        """Wait if necessary to respect rate limits."""
        if api_name in self.last_request_time:
            elapsed = time.time() - self.last_request_time[api_name]
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time[api_name] = time.time()
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                    return data
                else:
                    del self.cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Save data to cache."""
        with self.lock:
            self.cache[key] = (data, datetime.now())
