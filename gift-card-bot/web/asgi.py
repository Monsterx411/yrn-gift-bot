"""
ASGI entry point for uvicorn/gunicorn.
Run with: uvicorn web.asgi:app --host 0.0.0.0 --port 8443
Or:      gunicorn -k uvicorn.workers.UvicornWorker web.asgi:app
"""
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.server import app

# For direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web.asgi:app",
        host=os.getenv("WEBHOOK_LISTEN", "0.0.0.0"),
        port=int(os.getenv("WEBHOOK_PORT", "8443")),
        reload=True,
        log_level="info",
    )