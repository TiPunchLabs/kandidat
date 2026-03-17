import os

from app import create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=port)  # nosec B201
