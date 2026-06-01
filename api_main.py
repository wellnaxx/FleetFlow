import uvicorn

from src.adapters.driven.logging.config import configure_logging

if __name__ == "__main__":
    configure_logging()
    uvicorn.run(
        "src.adapters.driving.http.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
