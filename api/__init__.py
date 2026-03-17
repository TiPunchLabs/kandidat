from apiflask import APIBlueprint

api_bp = APIBlueprint("api", __name__, url_prefix="/api")

from . import (  # noqa: E402
    candidatures,  # noqa: F401
    other_routes,  # noqa: F401
    settings,  # noqa: F401
)
