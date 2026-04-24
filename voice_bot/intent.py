"""
Intent Classification module

Features:
- Rule-based intent classification (initial version)
- Keyword matching and semantic analysis
- Confidence scoring
- Extensible for ML models (RoBERTa) in future
"""

import logging
import re
from typing import Tuple, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Enum for all supported intents"""
    ORDER_TRACKING = 'ORDER_TRACKING'
    PRODUCT_SEARCH = 'PRODUCT_SEARCH'
    PAYMENT_ISSUE = 'PAYMENT_ISSUE'
    RETURN_REQUEST = 'RETURN_REQUEST'
    GENERAL_QUERY = 'GENERAL_QUERY'
    UNKNOWN = 'UNKNOWN'


class IntentClassifier:
    """Rule-based intent classifier"""
    
    # Keywords for each intent (expandable for ML models)
    INTENT_KEYWORDS = {
        IntentType.ORDER_TRACKING: {
            'keywords': [
                'order', 'tracking', 'status', 'where is', 'when will',
                'delivery', 'shipped', 'arrived', 'track', 'order number',
                'invoice', 'ordinal', 'order id', 'purchase'
            ],
            'phrases': [
                'where is my order',
                'track my order',
                'order status',
                'when will i receive',
                'delivery status',
                'my order',
            ],
            'weight': 1.0
        },
        IntentType.PRODUCT_SEARCH: {
            'keywords': [
                'find', 'search', 'show', 'product', 'item', 'clothes',
                'shirt', 'pants', 'dress', 'shoe', 'brand', 'category',
                'price', 'available', 'stock', 'size', 'color', 'material',
                'do you have', 'what is', 'looking for'
            ],
            'phrases': [
                'find me a',
                'show me',
                'do you have',
                'what products',
                'search for',
                'product search',
                'categories available',
            ],
            'weight': 1.0
        },
        IntentType.PAYMENT_ISSUE: {
            'keywords': [
                'payment', 'paid', 'charge', 'refund', 'money', 'price',
                'cost', 'bill', 'invoice', 'receipt', 'transaction',
                'failed', 'error', 'issue', 'problem', 'help'
            ],
            'phrases': [
                'payment failed',
                'payment issue',
                'refund',
                'my payment',
                'payment problem',
                'charge',
            ],
            'weight': 0.95
        },
        IntentType.RETURN_REQUEST: {
            'keywords': [
                'return', 'exchange', 'refund', 'broken', 'damaged',
                'wrong', 'incorrect', 'defective', 'issue', 'complaint',
                'send back', 'policy', 'process'
            ],
            'phrases': [
                'return policy',
                'how to return',
                'return request',
                'damaged product',
                'want to return',
                'exchange',
            ],
            'weight': 0.95
        },
        IntentType.GENERAL_QUERY: {
            'keywords': [
                'hello', 'hi', 'how', 'what', 'when', 'why', 'help',
                'about', 'tell', 'more', 'information', 'details'
            ],
            'phrases': [],
            'weight': 0.5
        }
    }
    
    def __init__(self):
        """Initialize classifier"""
        self.max_candidates = 3  # Return top-3 intent candidates
    
    def classify(self, text: str) -> Tuple[str, float, List[Dict]]:
        """
        Classify intent from text
        
        Args:
            text: User query text
        
        Returns:
            Tuple of (intent_name, confidence_score, candidate_list)
            where candidate_list = [{'intent': str, 'score': float}, ...]
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for classification")
            return IntentType.UNKNOWN.value, 0.0, []
        
        text = text.lower().strip()
        
        # Calculate scores for each intent
        scores = self._calculate_intent_scores(text)
        
        # Sort by score
        sorted_intents = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Get top intent and confidence
        top_intent, top_score = sorted_intents[0]
        confidence = min(top_score, 1.0)  # Cap at 1.0
        
        # Build candidate list
        candidates = [
            {'intent': intent.value, 'score': float(score)}
            for intent, score in sorted_intents[:self.max_candidates]
        ]
        
        logger.debug(
            f"Classification: {top_intent.value} (confidence: {confidence:.2f}), "
            f"text: '{text[:50]}...'"
        )
        
        return top_intent.value, confidence, candidates
    
    def _calculate_intent_scores(self, text: str) -> Dict[IntentType, float]:
        """Calculate scores for all intents"""
        scores = {}
        
        for intent_type, rules in self.INTENT_KEYWORDS.items():
            score = 0.0
            
            # Check phrases (exact matches, higher weight)
            for phrase in rules.get('phrases', []):
                if phrase in text:
                    score += 0.5
            
            # Check keywords (partial matches)
            keywords = rules.get('keywords', [])
            if keywords:
                keyword_matches = sum(1 for kw in keywords if kw in text)
                keyword_score = (keyword_matches / len(keywords)) * 0.5
                score += keyword_score
            
            # Apply weight
            score *= rules.get('weight', 1.0)
            scores[intent_type] = score
        
        return scores
    
    def get_intent_description(self, intent: str) -> str:
        """Get human-readable description of intent"""
        descriptions = {
            IntentType.ORDER_TRACKING.value: "Track your order status",
            IntentType.PRODUCT_SEARCH.value: "Search for products",
            IntentType.PAYMENT_ISSUE.value: "Payment or billing issue",
            IntentType.RETURN_REQUEST.value: "Return or exchange request",
            IntentType.GENERAL_QUERY.value: "General query",
            IntentType.UNKNOWN.value: "Unknown query type",
        }
        return descriptions.get(intent, "Unknown")


# Global classifier instance
_classifier = None


def get_classifier() -> IntentClassifier:
    """Get or create the intent classifier"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(text: str) -> dict:
    """
    Convenience function to classify intent
    
    Returns:
        {
            'intent': intent name,
            'confidence': confidence score,
            'candidates': [list of top candidates],
            'description': human-readable description
        }
    """
    classifier = get_classifier()
    intent, confidence, candidates = classifier.classify(text)
    
    return {
        'intent': intent,
        'confidence': float(confidence),
        'candidates': candidates,
        'description': classifier.get_intent_description(intent)
    }
