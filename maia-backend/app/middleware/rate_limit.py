from slowapi import Limiter
from slowapi.util import get_remote_address

# Limites generosos para dev. Produção: 60/min global, 20/min chat por usuário.
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])
