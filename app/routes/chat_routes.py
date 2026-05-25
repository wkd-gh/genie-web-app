from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.genie_client import GenieClient
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
genie_client = GenieClient()


# ── Pages ─────────────────────────────────────────────────────────────────────


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .limit(30)
        .all()
    )
    return templates.TemplateResponse(
        "chat/index.html",
        {
            "request": request,
            "user": user,
            "sessions": sessions,
            "current_session": None,
            "messages": [],
        },
    )


@router.get("/chat/{session_id}", response_class=HTMLResponse)
async def chat_session_page(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        return RedirectResponse("/chat", status_code=303)

    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .limit(30)
        .all()
    )
    return templates.TemplateResponse(
        "chat/index.html",
        {
            "request": request,
            "user": user,
            "sessions": sessions,
            "current_session": session,
            "messages": session.messages,
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "history/index.html",
        {"request": request, "user": user, "sessions": sessions},
    )


# ── API ───────────────────────────────────────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    session_id: int | None = None


@router.post("/api/ask")
async def ask(body: AskRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    question = body.question.strip()
    if not question:
        return JSONResponse({"error": "empty_question"}, status_code=400)

    session = None
    if body.session_id:
        session = (
            db.query(models.ChatSession)
            .filter(
                models.ChatSession.id == body.session_id,
                models.ChatSession.user_id == user.id,
            )
            .first()
        )

    # Save user message
    if session is None:
        session = models.ChatSession(user_id=user.id, title=question[:60])
        db.add(session)
        db.commit()
        db.refresh(session)

    user_msg = models.ChatMessage(
        session_id=session.id,
        role="user",
        content=question,
    )
    db.add(user_msg)
    db.commit()

    # Call Genie API
    try:
        if session.databricks_conversation_id:
            result = await genie_client.continue_conversation(
                session.databricks_conversation_id, question
            )
        else:
            result = await genie_client.start_conversation(question)
            if result.get("conversation_id"):
                session.databricks_conversation_id = result["conversation_id"]

        session.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        result = {
            "error": str(e),
            "text": None,
            "query": None,
            "query_result": None,
            "suggested_questions": [],
            "conversation_id": None,
        }

    # Save assistant message
    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=result.get("text"),
        query_sql=result.get("query", {}).get("sql") if result.get("query") else None,
        query_description=result.get("query", {}).get("description") if result.get("query") else None,
        query_result=result.get("query_result"),
        suggested_questions=result.get("suggested_questions"),
        error=result.get("error"),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {
        "session_id": session.id,
        "message_id": assistant_msg.id,
        "text": result.get("text"),
        "query": result.get("query"),
        "query_result": result.get("query_result"),
        "suggested_questions": result.get("suggested_questions", []),
        "error": result.get("error"),
    }


@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        return JSONResponse({"error": "not_found"}, status_code=404)

    db.delete(session)
    db.commit()
    return {"ok": True}
