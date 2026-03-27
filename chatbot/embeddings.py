"""
Embeddings Module
-----------------
Handles product embeddings using SentenceTransformers and FAISS vector database.
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy loading for heavy libraries
_model = None
_faiss_index = None
_product_id_mapping = {}

# Paths for storing data
EMBEDDINGS_DIR = Path(settings.BASE_DIR) / 'chatbot' / 'data'
FAISS_INDEX_PATH = EMBEDDINGS_DIR / 'products.index'
MAPPING_PATH = EMBEDDINGS_DIR / 'product_mapping.json'
FAQ_INDEX_PATH = EMBEDDINGS_DIR / 'faq.index'
FAQ_MAPPING_PATH = EMBEDDINGS_DIR / 'faq_mapping.json'

# Model settings
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2


def get_embedding_model():
    """Lazy load the SentenceTransformer model"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def ensure_embeddings_dir():
    """Ensure the embeddings directory exists"""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


def generate_embedding(text: str) -> np.ndarray:
    """Generate embedding for a single text"""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.astype('float32')


def generate_embeddings_batch(texts: List[str]) -> np.ndarray:
    """Generate embeddings for multiple texts"""
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return embeddings.astype('float32')


def create_product_embedding_text(product) -> str:
    """Create the text representation for a product embedding"""
    parts = [
        product.name,
        product.description or '',
        product.short_description or '',
        product.category.name if product.category else '',
        product.brand.name if product.brand else '',
        product.material or '',
        dict(product.GENDER_CHOICES).get(product.gender, ''),
    ]
    # Add colors if available
    try:
        colors = product.variants.values_list('color__name', flat=True).distinct()
        parts.extend(colors)
    except:
        pass
    
    return ' '.join(filter(None, parts))


class ProductVectorStore:
    """FAISS vector store for products"""
    
    def __init__(self):
        self.index = None
        self.product_mapping = {}  # faiss_id -> product_id
        self.reverse_mapping = {}  # product_id -> faiss_id
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index and mapping"""
        ensure_embeddings_dir()
        
        try:
            import faiss
            
            if FAISS_INDEX_PATH.exists() and MAPPING_PATH.exists():
                self.index = faiss.read_index(str(FAISS_INDEX_PATH))
                with open(MAPPING_PATH, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to int
                    self.product_mapping = {int(k): v for k, v in data.items()}
                    self.reverse_mapping = {v: int(k) for k, v in data.items()}
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)  # Inner product (cosine similarity for normalized vectors)
                logger.info("Created new FAISS index")
        except ImportError:
            logger.warning("FAISS not installed. Vector search will not be available.")
            self.index = None
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            import faiss
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    
    def _save_index(self):
        """Save FAISS index and mapping to disk"""
        if self.index is None:
            return
        
        ensure_embeddings_dir()
        
        try:
            import faiss
            faiss.write_index(self.index, str(FAISS_INDEX_PATH))
            with open(MAPPING_PATH, 'w') as f:
                json.dump(self.product_mapping, f)
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    def add_product(self, product_id: int, embedding: np.ndarray) -> int:
        """Add a single product embedding"""
        if self.index is None:
            logger.warning("FAISS index not available")
            return -1
        
        # Normalize embedding for cosine similarity
        embedding = embedding.reshape(1, -1)
        embedding = embedding / np.linalg.norm(embedding)
        
        faiss_id = self.index.ntotal
        self.index.add(embedding)
        
        self.product_mapping[faiss_id] = product_id
        self.reverse_mapping[product_id] = faiss_id
        
        self._save_index()
        return faiss_id
    
    def add_products_batch(self, product_ids: List[int], embeddings: np.ndarray) -> List[int]:
        """Add multiple product embeddings"""
        if self.index is None:
            logger.warning("FAISS index not available")
            return []
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        
        start_id = self.index.ntotal
        self.index.add(embeddings)
        
        faiss_ids = []
        for i, product_id in enumerate(product_ids):
            faiss_id = start_id + i
            self.product_mapping[faiss_id] = product_id
            self.reverse_mapping[product_id] = faiss_id
            faiss_ids.append(faiss_id)
        
        self._save_index()
        return faiss_ids
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """Search for similar products"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search
        distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx in self.product_mapping:
                product_id = self.product_mapping[idx]
                results.append((product_id, float(dist)))
        
        return results
    
    def search_by_text(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Search for products using text query"""
        embedding = generate_embedding(query)
        return self.search(embedding, k)
    
    def has_product(self, product_id: int) -> bool:
        """Check if product is already in index"""
        return product_id in self.reverse_mapping
    
    def remove_product(self, product_id: int):
        """Remove product from index (requires rebuilding index)"""
        # Note: FAISS IndexFlatIP doesn't support removal
        # For now, we'll mark it and rebuild periodically
        if product_id in self.reverse_mapping:
            faiss_id = self.reverse_mapping[product_id]
            del self.reverse_mapping[product_id]
            del self.product_mapping[faiss_id]
    
    def rebuild_index(self, products):
        """Rebuild the entire index from products queryset"""
        import faiss
        
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.product_mapping = {}
        self.reverse_mapping = {}
        
        product_list = list(products)
        if not product_list:
            logger.info("No products to index")
            return
        
        texts = [create_product_embedding_text(p) for p in product_list]
        embeddings = generate_embeddings_batch(texts)
        
        product_ids = [p.id for p in product_list]
        self.add_products_batch(product_ids, embeddings)
        
        logger.info(f"Rebuilt index with {len(product_list)} products")


class FAQVectorStore:
    """FAISS vector store for FAQ documents"""
    
    def __init__(self):
        self.index = None
        self.faq_mapping = {}  # faiss_id -> faq_id
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index"""
        ensure_embeddings_dir()
        
        try:
            import faiss
            
            if FAQ_INDEX_PATH.exists() and FAQ_MAPPING_PATH.exists():
                self.index = faiss.read_index(str(FAQ_INDEX_PATH))
                with open(FAQ_MAPPING_PATH, 'r') as f:
                    self.faq_mapping = {int(k): v for k, v in json.load(f).items()}
            else:
                self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        except ImportError:
            self.index = None
        except Exception as e:
            logger.error(f"Error loading FAQ index: {e}")
            import faiss
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    
    def _save_index(self):
        """Save FAISS index"""
        if self.index is None:
            return
        
        ensure_embeddings_dir()
        
        try:
            import faiss
            faiss.write_index(self.index, str(FAQ_INDEX_PATH))
            with open(FAQ_MAPPING_PATH, 'w') as f:
                json.dump(self.faq_mapping, f)
        except Exception as e:
            logger.error(f"Error saving FAQ index: {e}")
    
    def rebuild_index(self, faq_documents):
        """Rebuild FAQ index"""
        import faiss
        
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.faq_mapping = {}
        
        docs = list(faq_documents)
        if not docs:
            return
        
        texts = [f"{doc.title} {doc.content}" for doc in docs]
        embeddings = generate_embeddings_batch(texts)
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        
        self.index.add(embeddings)
        
        for i, doc in enumerate(docs):
            self.faq_mapping[i] = doc.id
        
        self._save_index()
    
    def search(self, query: str, k: int = 3) -> List[int]:
        """Search FAQ documents"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        embedding = generate_embedding(query)
        embedding = embedding.reshape(1, -1)
        embedding = embedding / np.linalg.norm(embedding)
        
        distances, indices = self.index.search(embedding, min(k, self.index.ntotal))
        
        results = []
        for idx in indices[0]:
            if idx >= 0 and idx in self.faq_mapping:
                results.append(self.faq_mapping[idx])
        
        return results


# Global instances
_product_store = None
_faq_store = None


def get_product_store() -> ProductVectorStore:
    """Get the global product vector store instance"""
    global _product_store
    if _product_store is None:
        _product_store = ProductVectorStore()
    return _product_store


def get_faq_store() -> FAQVectorStore:
    """Get the global FAQ vector store instance"""
    global _faq_store
    if _faq_store is None:
        _faq_store = FAQVectorStore()
    return _faq_store
