# Genie Web App

> Databricks Genie를 웹과 모바일에서 사용할 수 있는 인터페이스입니다.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-Genie-FF3621?style=flat-square&logo=databricks&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?style=flat-square&logo=googlecloud&logoColor=white)

---

## Overview

자연어로 질문하면 Databricks Genie가 SQL을 생성하고 데이터를 조회해서 결과를 보여주는 웹 인터페이스입니다.
데스크탑과 모바일 모두 지원합니다.

---

## Architecture

```
사용자 브라우저 (PC / 모바일)
      ↓
Cloud Run
  └── FastAPI (uvicorn)
        ├── GET /           → 웹 UI (HTML/CSS/JS, 반응형)
        └── POST /api/ask   → Genie API 호출 → 결과 반환
                ↓
        Databricks Genie API
```

---

## Project Structure

```
genie-web-app/
├── app/
│   ├── main.py           # FastAPI 엔트리포인트 & 라우터
│   └── genie_client.py   # Databricks Genie API 클라이언트
├── static/
│   ├── css/              # 스타일시트 (반응형)
│   └── js/               # 클라이언트 스크립트
├── templates/
│   └── index.html        # 메인 페이지 (반응형 레이아웃)
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Environment Variables

`.env.example`을 참고하여 `.env` 파일을 생성하세요.

| 변수명 | 설명 |
|--------|------|
| `DATABRICKS_HOST` | Databricks Workspace URL (`dbc-xxxx.cloud.databricks.com`) |
| `DATABRICKS_TOKEN` | Databricks Personal Access Token (`dapi...`, `genie` 스코프) |
| `GENIE_SPACE_ID` | Databricks Genie Space ID |

---

## Getting Started

### 로컬 실행

```bash
# 1. 레포 클론
git clone https://github.com/Money-Digger/genie-web-app.git
cd genie-web-app

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 실제 값 채우기

# 4. 서버 실행
uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속

### Cloud Run 배포

```bash
gcloud run deploy genie-web-app \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars DATABRICKS_HOST=...,DATABRICKS_TOKEN=...,GENIE_SPACE_ID=...
```

---

## 반응형 지원

| 환경 | 지원 |
|------|------|
| 데스크탑 (1024px+) | ✅ |
| 태블릿 (768px+) | ✅ |
| 모바일 (320px+) | ✅ |

---

## Related

- [airflow-etl-pipeline](https://github.com/Money-Digger/airflow-etl-pipeline) — 데이터 수집 및 Databricks 적재 파이프라인
- [genie-slack-bot](https://github.com/Money-Digger/genie-slack-bot) — Slack Slash Command or Mention 기반 Genie 봇