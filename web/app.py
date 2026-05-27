import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

web_dir = Path(__file__).parent

app = FastAPI(title="Tradeyuk Web", version="0.2.5")

app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(web_dir / "templates"))

from web.routes import analysis, prices

app.include_router(analysis.router)
app.include_router(prices.router)


def main():
    import uvicorn

    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
