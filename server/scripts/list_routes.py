from src.app.main import create_app
from fastapi.routing import APIRoute

app = create_app()

def print_router_routes(router, prefix=""):
    for route in router.routes:
        if isinstance(route, APIRoute):
            print(f"Path: {prefix}{route.path} | Name: {route.name} | Methods: {route.methods}")
        elif type(route).__name__ == '_IncludedRouter':
            context = getattr(route, 'include_context', None)
            if context:
                sub_prefix = getattr(context, 'prefix', '')
                original = getattr(route, 'original_router', None)
                if original:
                    print_router_routes(original, prefix + sub_prefix)
        elif hasattr(route, 'routes'):
            print_router_routes(route, prefix)

print_router_routes(app)
