from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from . import (  # noqa: E402
    candidatures,  # noqa: F401
    other_routes,  # noqa: F401
    settings,  # noqa: F401
)
