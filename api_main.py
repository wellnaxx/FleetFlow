import logging

import uvicorn

from src.adapters.driven.logging.config import configure_logging

if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    configure_logging()

    host = "127.0.0.1"
    port = 8000
    reload = True

    logger.info("Starting FleetFlow API on http://%s:%d with reload=%s.", host, port, reload)

    uvicorn.run(
        "src.adapters.driving.http.app:app",
        host=host,
        port=port,
        reload=reload,
    )
