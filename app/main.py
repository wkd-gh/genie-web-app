from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_db, init_db
from app.auth import get_current_user
from app.routes.auth_routes import router as auth_router
from app.routes.chat_routes import router as chat_router
from app.routes.dashboard_routes import router as dashboard_router

app = FastAPI(title="Genie Web App")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    db = next(get_db())
    user = get_current_user(request, db)
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        "landing.html", {"request": request, "user": user, "msg": msg}
    )


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(dashboard_router)
