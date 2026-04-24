from django.test import TestCase
from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import VoiceQuery, VoiceQueryLog
from .intent import IntentClassifier, IntentType
from .services import VoiceServiceHandler


class IntentClassifierTestCase(TestCase):
    """Test case for intent classification"""
    
    def setUp(self):
        self.classifier = IntentClassifier()
    
    def test_order_tracking_intent(self):
        """Test order tracking intent detection"""
        test_cases = [
            "where is my order",
            "track my order",
            "order status",
            "when will i receive my package",
        ]
        
        for query in test_cases:
            intent, confidence, candidates = self.classifier.classify(query)
            self.assertEqual(intent, IntentType.ORDER_TRACKING.value)
            self.assertGreater(confidence, 0.3)
    
    def test_product_search_intent(self):
        """Test product search intent detection"""
        test_cases = [
            "find me a shirt",
            "show me blue dresses",
            "do you have sneakers",
            "search for winter jackets",
        ]
        
        for query in test_cases:
            intent, confidence, candidates = self.classifier.classify(query)
            self.assertEqual(intent, IntentType.PRODUCT_SEARCH.value)
            self.assertGreater(confidence, 0.3)
    
    def test_payment_issue_intent(self):
        """Test payment issue intent detection"""
        test_cases = [
            "payment failed",
            "refund my money",
            "payment issue",
        ]
        
        for query in test_cases:
            intent, confidence, candidates = self.classifier.classify(query)
            self.assertEqual(intent, IntentType.PAYMENT_ISSUE.value)
            self.assertGreater(confidence, 0.3)
    
    def test_return_request_intent(self):
        """Test return request intent detection"""
        test_cases = [
            "return policy",
            "how to return",
            "damaged product",
            "want to exchange",
        ]
        
        for query in test_cases:
            intent, confidence, candidates = self.classifier.classify(query)
            self.assertEqual(intent, IntentType.RETURN_REQUEST.value)
            self.assertGreater(confidence, 0.3)
    
    def test_empty_query(self):
        """Test handling of empty query"""
        intent, confidence, candidates = self.classifier.classify("")
        self.assertEqual(intent, IntentType.UNKNOWN.value)
        self.assertEqual(confidence, 0.0)


class VoiceServiceHandlerTestCase(TestCase):
    """Test case for voice service handler"""
    
    def setUp(self):
        self.handler = VoiceServiceHandler()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_order_tracking_handler_no_user(self):
        """Test order tracking without user"""
        result = self.handler.handle_order_tracking("track my order", user=None)
        self.assertFalse(result['success'])
    
    def test_product_search_handler_no_products(self):
        """Test product search with no results"""
        result = self.handler.handle_product_search("nonexistent product", user=self.user)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']['products']), 0)
    
    def test_payment_issue_handler(self):
        """Test payment issue handler"""
        result = self.handler.handle_payment_issue("payment failed", user=self.user)
        self.assertTrue(result['success'])
        self.assertIn('support_email', result['data'])
    
    def test_general_query_handler(self):
        """Test general query handler"""
        result = self.handler.handle_general_query("hello", user=self.user)
        self.assertTrue(result['success'])
        self.assertIn('response', result)


class VoiceQueryModelTestCase(TestCase):
    """Test case for VoiceQuery model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_voice_query(self):
        """Test creating a voice query"""
        query = VoiceQuery.objects.create(
            user=self.user,
            session_id='test-session-123',
            transcribed_text='track my order',
            intent='ORDER_TRACKING',
            confidence_score=0.95,
            response_message='Your order is on the way'
        )
        
        self.assertEqual(query.user, self.user)
        self.assertEqual(query.transcribed_text, 'track my order')
        self.assertEqual(query.confidence_score, 0.95)
    
    def test_confidence_level_calculation(self):
        """Test confidence level calculation"""
        # High confidence
        query = VoiceQuery(
            user=self.user,
            transcribed_text='test',
            intent='ORDER_TRACKING',
            confidence_score=0.9,
            response_message='test'
        )
        query.calculate_confidence_level()
        self.assertEqual(query.confidence_level, 'HIGH')
        
        # Medium confidence
        query.confidence_score = 0.65
        query.calculate_confidence_level()
        self.assertEqual(query.confidence_level, 'MEDIUM')
        
        # Low confidence
        query.confidence_score = 0.3
        query.calculate_confidence_level()
        self.assertEqual(query.confidence_level, 'LOW')
