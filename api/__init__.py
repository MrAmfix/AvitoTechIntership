from .pull_request import pr_router
from .team import t_router
from .user import u_router


routers = [pr_router, t_router, u_router]


__all__ = ['routers', 'pr_router', 't_router', 'u_router']
