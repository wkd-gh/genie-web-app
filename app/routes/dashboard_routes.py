from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ── Pages ─────────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    dashboards = (
        db.query(models.Dashboard)
        .filter(models.Dashboard.user_id == user.id)
        .order_by(models.Dashboard.updated_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "dashboard/index.html",
        {"request": request, "user": user, "dashboards": dashboards},
    )


@router.get("/dashboard/new", response_class=HTMLResponse)
async def create_dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "dashboard/create.html", {"request": request, "user": user}
    )


@router.post("/dashboard/new")
async def create_dashboard(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    dashboard = models.Dashboard(
        user_id=user.id,
        name=name.strip(),
        description=description.strip() or None,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return RedirectResponse(f"/dashboard/{dashboard.id}", status_code=303)


@router.get("/dashboard/{dashboard_id}", response_class=HTMLResponse)
async def view_dashboard(
    dashboard_id: int, request: Request, db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    dashboard = (
        db.query(models.Dashboard)
        .filter(
            models.Dashboard.id == dashboard_id,
            models.Dashboard.user_id == user.id,
        )
        .first()
    )
    if not dashboard:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        "dashboard/view.html",
        {"request": request, "user": user, "dashboard": dashboard},
    )


# ── API ───────────────────────────────────────────────────────────────────────


@router.get("/api/dashboards-list")
async def list_dashboards_api(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    dashboards = (
        db.query(models.Dashboard)
        .filter(models.Dashboard.user_id == user.id)
        .order_by(models.Dashboard.updated_at.desc())
        .all()
    )
    return {"dashboards": [{"id": d.id, "name": d.name} for d in dashboards]}


class AddTileRequest(BaseModel):
    title: str
    question: str | None = None
    query_sql: str | None = None
    query_result: list | None = None
    chart_type: str = "table"


@router.post("/api/dashboards/{dashboard_id}/tiles")
async def add_tile(
    dashboard_id: int,
    body: AddTileRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    dashboard = (
        db.query(models.Dashboard)
        .filter(
            models.Dashboard.id == dashboard_id,
            models.Dashboard.user_id == user.id,
        )
        .first()
    )
    if not dashboard:
        return JSONResponse({"error": "not_found"}, status_code=404)

    max_pos = max((t.position for t in dashboard.tiles), default=-1)
    tile = models.DashboardTile(
        dashboard_id=dashboard_id,
        title=body.title,
        question=body.question,
        query_sql=body.query_sql,
        query_result=body.query_result,
        chart_type=body.chart_type,
        position=max_pos + 1,
    )
    db.add(tile)
    db.commit()
    db.refresh(tile)
    return {"ok": True, "tile_id": tile.id}


@router.delete("/api/dashboards/{dashboard_id}/tiles/{tile_id}")
async def delete_tile(
    dashboard_id: int,
    tile_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    tile = (
        db.query(models.DashboardTile)
        .join(models.Dashboard)
        .filter(
            models.DashboardTile.id == tile_id,
            models.DashboardTile.dashboard_id == dashboard_id,
            models.Dashboard.user_id == user.id,
        )
        .first()
    )
    if not tile:
        return JSONResponse({"error": "not_found"}, status_code=404)

    db.delete(tile)
    db.commit()
    return {"ok": True}


@router.delete("/api/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int, request: Request, db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    dashboard = (
        db.query(models.Dashboard)
        .filter(
            models.Dashboard.id == dashboard_id,
            models.Dashboard.user_id == user.id,
        )
        .first()
    )
    if not dashboard:
        return JSONResponse({"error": "not_found"}, status_code=404)

    db.delete(dashboard)
    db.commit()
    return {"ok": True}
