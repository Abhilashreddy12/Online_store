import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
django.setup()

import catalog.routing

application = ProtocolTypeRouter({
	'http': get_asgi_application(),
	'websocket': SessionMiddlewareStack(
		AuthMiddlewareStack(
			URLRouter(
				catalog.routing.websocket_urlpatterns
			)
		)
	),
})
