from django.db import models
from django.contrib.auth.models import User


class ChatLog(models.Model):
    """Store chat history for conversation memory and analytics"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chat_logs',
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=100, db_index=True)
    message = models.TextField()
    response = models.TextField()
    response_type = models.CharField(max_length=50, default='text')  # text, product_list, cart, order, etc.
    metadata = models.JSONField(null=True, blank=True)  # Store additional data like product IDs, filters used, etc.
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['session_id', 'timestamp']),
        ]

    def __str__(self):
        return f"Chat {self.id} - {self.user or 'Anonymous'} at {self.timestamp}"


class ProductEmbedding(models.Model):
    """Track product embeddings metadata (vectors stored in FAISS)"""
    product_id = models.IntegerField(unique=True, db_index=True)
    faiss_id = models.IntegerField(unique=True, db_index=True)
    embedding_text = models.TextField()  # The text that was embedded
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Embedding for Product {self.product_id}"


class FAQDocument(models.Model):
    """Knowledge base documents for RAG"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=100, db_index=True)  # shipping, returns, payment, etc.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'title']

    def __str__(self):
        return f"{self.category}: {self.title}"
