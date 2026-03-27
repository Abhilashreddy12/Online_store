"""
Signals Module
--------------
Django signals for automatic embedding generation when products are created/updated.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def generate_product_embedding(product):
    """Generate embedding for a single product"""
    try:
        from .embeddings import (
            get_product_store, 
            create_product_embedding_text, 
            generate_embedding
        )
        from .models import ProductEmbedding
        
        store = get_product_store()
        
        # Check if already exists
        if store.has_product(product.id):
            logger.debug(f"Product {product.id} already has embedding")
            return
        
        # Generate embedding
        text = create_product_embedding_text(product)
        embedding = generate_embedding(text)
        
        # Add to FAISS
        faiss_id = store.add_product(product.id, embedding)
        
        # Store metadata
        ProductEmbedding.objects.update_or_create(
            product_id=product.id,
            defaults={
                'faiss_id': faiss_id,
                'embedding_text': text[:500]  # Store truncated text for reference
            }
        )
        
        logger.info(f"Generated embedding for product {product.id}: {product.name}")
        
    except Exception as e:
        logger.error(f"Failed to generate embedding for product {product.id}: {e}")


@receiver(post_save, sender='catalog.Product')
def product_saved(sender, instance, created, **kwargs):
    """
    Signal handler for when a product is created or updated.
    Generates embedding for new products.
    """
    if created and instance.is_active:
        # Use a small delay to ensure product is fully saved
        try:
            from django.db import transaction
            transaction.on_commit(lambda: generate_product_embedding(instance))
        except:
            # Fallback to direct call
            generate_product_embedding(instance)


@receiver(post_delete, sender='catalog.Product')
def product_deleted(sender, instance, **kwargs):
    """
    Signal handler for when a product is deleted.
    Note: FAISS IndexFlatIP doesn't support removal, so we just clean up metadata.
    Index should be rebuilt periodically.
    """
    try:
        from .models import ProductEmbedding
        from .embeddings import get_product_store
        
        ProductEmbedding.objects.filter(product_id=instance.id).delete()
        
        store = get_product_store()
        store.remove_product(instance.id)
        
        logger.info(f"Removed embedding metadata for product {instance.id}")
        
    except Exception as e:
        logger.error(f"Failed to clean up embedding for deleted product: {e}")
