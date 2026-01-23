ACTION_REGISTRY = {}


def action(name: str, description: str, app: str = None):
    """Decorator to register a function as an action."""
    def decorator(func):
        ACTION_REGISTRY[name] = {
            'func': func,
            'name': name,
            'description': description,
            'app': app,
        }
        return func
    return decorator
