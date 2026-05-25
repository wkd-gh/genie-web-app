from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/chat", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": error})


@router.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse("/login?error=invalid", status_code=303)
    if not user.is_active:
        return RedirectResponse("/login?error=inactive", status_code=303)

    token = create_access_token(user.id)
    response = RedirectResponse("/chat", status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/chat", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse("auth/register.html", {"request": request, "error": error})


@router.post("/auth/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(models.User).filter(models.User.email == email).first():
        return RedirectResponse("/register?error=email_exists", status_code=303)
    if db.query(models.User).filter(models.User.username == username).first():
        return RedirectResponse("/register?error=username_exists", status_code=303)
    if len(password) < 8:
        return RedirectResponse("/register?error=password_short", status_code=303)

    user = models.User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    response = RedirectResponse("/chat", status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.post("/auth/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    msg = request.query_params.get("msg")
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "settings.html", {"request": request, "user": user, "msg": msg, "error": error}
    )


@router.post("/auth/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not verify_password(current_password, user.hashed_password):
        return RedirectResponse("/settings?error=wrong_password", status_code=303)
    if len(new_password) < 8:
        return RedirectResponse("/settings?error=password_short", status_code=303)

    user.hashed_password = hash_password(new_password)
    db.commit()
    return RedirectResponse("/settings?msg=password_changed", status_code=303)


@router.post("/auth/delete-account")
async def delete_account(
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not verify_password(password, user.hashed_password):
        return RedirectResponse("/settings?error=wrong_password", status_code=303)

    db.delete(user)
    db.commit()
    response = RedirectResponse("/?msg=account_deleted", status_code=303)
    response.delete_cookie("access_token")
    return response
