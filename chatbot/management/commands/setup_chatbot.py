"""
Management command to set up the AI chatbot.
- Builds product embeddings
- Initializes FAQ documents
- Builds FAQ index
"""

from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up the AI chatbot: build embeddings, initialize FAQ, build indexes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products-only',
            action='store_true',
            help='Only rebuild product embeddings'
        )
        parser.add_argument(
            '--faq-only',
            action='store_true',
            help='Only rebuild FAQ index'
        )
        parser.add_argument(
            '--skip-embeddings',
            action='store_true',
            help='Skip building embeddings (useful if dependencies not installed)'
        )

    def handle(self, *args, **options):
        products_only = options.get('products_only')
        faq_only = options.get('faq_only')
        skip_embeddings = options.get('skip_embeddings')

        self.stdout.write(self.style.NOTICE('Setting up AI Chatbot...'))

        # Build product embeddings
        if not faq_only and not skip_embeddings:
            self.build_product_embeddings()

        # Build FAQ index
        if not products_only:
            self.build_faq_index(skip_embeddings)

        self.stdout.write(self.style.SUCCESS('AI Chatbot setup complete!'))

    def build_product_embeddings(self):
        """Build FAISS index for products"""
        self.stdout.write('Building product embeddings...')
        
        try:
            from catalog.models import Product
            from chatbot.embeddings import get_product_store
            
            products = Product.objects.filter(is_active=True)
            product_count = products.count()
            
            if product_count == 0:
                self.stdout.write(self.style.WARNING('No active products found'))
                return
            
            self.stdout.write(f'Found {product_count} active products')
            
            store = get_product_store()
            store.rebuild_index(products)
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully built embeddings for {product_count} products'
            ))
            
        except ImportError as e:
            self.stdout.write(self.style.WARNING(
                f'Cannot build embeddings: {e}\n'
                'Make sure sentence-transformers and faiss-cpu are installed'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error building embeddings: {e}'))

    def build_faq_index(self, skip_embeddings=False):
        """Initialize FAQ documents and build index"""
        self.stdout.write('Setting up FAQ knowledge base...')
        
        try:
            from chatbot.rag_pipeline import initialize_faq_documents, rebuild_faq_index
            from chatbot.models import FAQDocument
            
            # Initialize documents
            initialize_faq_documents()
            faq_count = FAQDocument.objects.filter(is_active=True).count()
            self.stdout.write(f'Initialized {faq_count} FAQ documents')
            
            # Build index
            if not skip_embeddings:
                rebuild_faq_index()
                self.stdout.write(self.style.SUCCESS('FAQ index built successfully'))
            else:
                self.stdout.write(self.style.WARNING('Skipped FAQ embedding index'))
            
        except ImportError as e:
            self.stdout.write(self.style.WARNING(
                f'Cannot build FAQ index: {e}\n'
                'FAQ keyword search will still work'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up FAQ: {e}'))



