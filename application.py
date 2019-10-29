import os

from finance import create_app


if __name__ == "__main__":
    application = create_app()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8002))
    debug = bool(os.environ.get("DEBUG", False))

    application.run(host=host, port=port, debug=debug)
