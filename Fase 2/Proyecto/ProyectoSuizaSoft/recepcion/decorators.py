"""
Decoradores personalizados para la app de recepción.
"""
from functools import wraps
from django.shortcuts import redirect


def login_operario_required(view_func):
    """
    Decorador que verifica que el operario tenga sesión activa.
    Si no, redirige al login.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'usuario_activo' not in request.session:
            return redirect('login_app')
        return view_func(request, *args, **kwargs)
    return wrapper
