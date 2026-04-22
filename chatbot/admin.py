from django.contrib import admin
from .models import ChatLog, ProductEmbedding, FAQDocument


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'response_type', 'timestamp']
    list_filter = ['response_type', 'timestamp']
    search_fields = ['message', 'response', 'session_id']
    readonly_fields = ['user', 'session_id', 'message', 'response', 'response_type', 'metadata', 'timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

@admin.register(ProductEmbedding)
class ProductEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'faiss_id', 'created_at', 'updated_at']
    search_fields = ['product_id', 'embedding_text']
    readonly_fields = ['product_id', 'faiss_id', 'embedding_text', 'created_at', 'updated_at']


@admin.register(FAQDocument)
class FAQDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_active', 'updated_at']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'content']
    list_editable = ['is_active']
