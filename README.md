# Genie Web App

> Databricks Genie를 웹과 모바일에서 사용할 수 있는 엔터프라이즈 인터페이스입니다.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-Genie-FF3621?style=flat-square&logo=databricks&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?style=flat-square&logo=googlecloud&logoColor=white)

---

## Overview

자연어로 질문하면 Databricks Genie가 SQL을 생성하고 데이터를 조회해서 결과를 보여주는 웹 인터페이스입니다.  
회원가입/로그인, 대화 히스토리, 대시보드 기능을 포함한 풀 SaaS 앱입니다.

---

## Features

| 기능 | 설명 |
|------|------|
| 🤖 자연어 채팅 | SQL 없이 한국어로 질문 → SQL 자동 생성 + 결과 반환 |
| 💬 대화 히스토리 | 모든 채팅 세션 자동 저장, 이어서 질문 가능 |
| 📊 대시보드 | 분석 결과를 타일로 저장, 막대/라인/파이 차트 지원 |
| 🔐 인증 | 회원가입 / 로그인 / 비밀번호 변경 / 회원탈퇴 |
| 📱 반응형 | 모바일 · 태블릿 · 데스크탑 완전 지원 |

---

## Architecture

```
사용자 브라우저 (PC / 모바일)
      ↓
Cloud Run
  └── FastAPI (uvicorn)
        ├── Jinja2 SSR 페이지 (HTML)
        ├── REST API (/api/*)
        │     └── 인증 (JWT · HttpOnly Cookie)
        │     └── 채팅, 히스토리, 대시보드
        └── SQLAlchemy ORM
              ├── 로컬: SQLite
              └── 프로덕션: Cloud SQL (PostgreSQL)
                    ↓
        Databricks Genie API
```

---

## Project Structure

```
genie-web-app/
├── app/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── config.py            # 환경변수 설정
│   ├── database.py          # SQLAlchemy 세팅
│   ├── models.py            # DB 모델 (User, ChatSession, Dashboard, ...)
│   ├── auth.py              # JWT 인증 유틸
│   ├── genie_client.py      # Databricks Genie API 클라이언트
│   ├── routes/
│   │   ├── auth_routes.py   # 회원가입/로그인/로그아웃/탈퇴
│   │   ├── chat_routes.py   # 채팅 페이지 + /api/ask
│   │   └── dashboard_routes.py  # 대시보드 CRUD
│   └── templates/
│       ├── base.html        # 공통 레이아웃 (사이드바, 탑바)
│       ├── landing.html     # 랜딩 페이지
│       ├── settings.html    # 계정 설정
│       ├── auth/            # login.html, register.html
│       ├── chat/            # index.html
│       ├── history/         # index.html
│       └── dashboard/       # index.html, create.html, view.html
├── static/
│   └── css/style.css
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Environment Variables

`.env.example`을 참고하여 `.env` 파일을 생성하세요.

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `DATABRICKS_HOST` | Databricks Workspace URL | ✅ |
| `DATABRICKS_TOKEN` | Databricks Personal Access Token | ✅ |
| `GENIE_SPACE_ID` | Databricks Genie Space ID | ✅ |
| `SECRET_KEY` | JWT 서명 비밀키 (32자 이상 랜덤 문자열) | ✅ |
| `DATABASE_URL` | SQLAlchemy DB URL (기본: SQLite) | 선택 |

> **GCP Secret Manager 연동**: Cloud Run에서 Secret Manager 시크릿을 환경변수로 마운트하면  
> 애플리케이션 코드 변경 없이 동일하게 `os.getenv()`로 읽힙니다.

---

## Getting Started

### 로컬 실행

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 실제 값 채우기

# 3. 서버 실행
uvicorn app.main:app --reload --port 8000
```

`http://localhost:8000` 접속 후 회원가입 → Genie 채팅 시작

### Cloud Run 배포

```bash
gcloud run deploy genie-web-app \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-secrets DATABRICKS_HOST=genie-databricks-host:latest \
  --set-secrets DATABRICKS_TOKEN=genie-databricks-token:latest \
  --set-secrets GENIE_SPACE_ID=genie-space-id:latest \
  --set-secrets SECRET_KEY=genie-web-secret-key:latest \
  --set-secrets DATABASE_URL=genie-web-db-url:latest
```

> **CI/CD**: `main` 브랜치 푸쉬 시 Cloud Build + Cloud Run 자동 배포를 설정하려면
> Cloud Build 트리거를 GitHub 레포에 연결하세요.

### 프로덕션 DB (Cloud SQL)

SQLite는 Cloud Run의 ephemeral 파일시스템에 저장되므로 **재시작 시 데이터가 사라집니다**.  
프로덕션에서는 Cloud SQL (PostgreSQL)을 사용하세요.

```bash
# requirements.txt에 추가
psycopg2-binary==2.9.9

# DATABASE_URL 형식
postgresql+psycopg2://USER:PASS@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

---

## Related

- [genie-slack-bot](https://github.com/Money-Digger/genie-slack-bot) — Slack Slash Command 기반 Genie 봇
- [airflow-etl-pipeline](https://github.com/Money-Digger/airflow-etl-pipeline) — 데이터 수집 파이프라인
