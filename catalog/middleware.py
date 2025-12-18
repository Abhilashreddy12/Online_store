from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack

# Use SessionMiddlewareStack for session access in consumers
LiveViewMiddlewareStack = lambda inner: SessionMiddlewareStack(AuthMiddlewareStack(inner))
