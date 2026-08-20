"""
짚어드림 - 백엔드 서버 (FastAPI + Gemini API)
=============================================
할 일:
  1. https://aistudio.google.com/apikey 에서 무료 API 키 발급
  2. .env 파일에 GEMINI_API_KEY 를 넣는다 (.env.example 참고)
  3. pip install -r requirements.txt
  4. uvicorn main:app --reload
  5. Render에 배포할 때는 대시보드의 Environment Variables에 등록
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
DB_PATH = os.getenv("DB_PATH", "history.db")

app = FastAPI(title="짚어드림 API (Gemini)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                screen_type TEXT NOT NULL,
                question TEXT NOT NULL,
                steps TEXT NOT NULL,
                tts_text TEXT NOT NULL
            )
        """)

init_db()


class AnalyzeRequest(BaseModel):
    image_base64: str
    media_type: str = "image/png"
    question: str = "이 화면에서 무엇을 눌러야 하는지 알려주세요."


class StepItem(BaseModel):
    text: str
    x: float = 50
    y: float = 50


class AnalyzeResponse(BaseModel):
    id: int
    timestamp: str
    screen_type: str
    steps: list[StepItem]
    tts_text: str


SYSTEM_PROMPT = """당신은 디지털 기기 사용이 어려운 어르신을 돕는 안내자입니다. 사용자가 올린 화면 캡처를 분석해서 반드시 아래 JSON 형식으로만 답하세요.

{
  "screen_type": "키오스크" 또는 "모바일 앱" 또는 "공공서비스" 또는 "기타" 중 하나,
  "steps": [
    {"text": "1단계 설명", "x": 50, "y": 20},
    {"text": "2단계 설명", "x": 30, "y": 45}
  ],
  "tts_text": "steps를 자연스럽게 이어붙인 음성 안내용 문장"
}

규칙:
1) x, y는 각 단계에서 눌러야 할 버튼/요소가 이미지 안에서 위치한 지점을 퍼센트 좌표로 표시 (x: 왼쪽 기준 0~100, y: 위쪽 기준 0~100)
2) 어려운 용어는 풀어서 설명
3) steps는 3~5개, 각 항목 text는 한 문장으로 짧게
4) 존댓말과 다정한 말투
5) 화면이 불명확하면 steps 첫 항목에 다시 가까이서 찍어달라고 안내하고 x,y는 50,50으로, screen_type은 '기타'로"""


@app.get("/")
def root():
    return {"status": "ok", "service": "짚어드림 API (Gemini)"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_screen(req: AnalyzeRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="서버에 GEMINI_API_KEY가 설정되지 않았습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    resp = None
    last_error_text = ""

    for attempt in range(5):
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"content-type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"inline_data": {"mime_type": req.media_type, "data": req.image_base64}},
                                {"text": req.question},
                            ],
                        }
                    ],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
        if resp.status_code == 200:
            break
        last_error_text = resp.text[:500]
        print(f"[Gemini 재시도 {attempt + 1}/5] status={resp.status_code} body={last_error_text}")
        if resp.status_code in (429, 500, 502, 503):
            await asyncio.sleep(3 * (attempt + 1))
            continue
        else:
            break

    if resp is None or resp.status_code != 200:
        is_busy = resp is not None and resp.status_code == 429
        status = 429 if is_busy else 502
        detail = "지금 이용자가 많아 잠시 처리 못했어요." if is_busy else f"AI 호출 실패: {last_error_text}"
        raise HTTPException(status_code=status, detail=detail)

    data = resp.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raw = "{}"
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"screen_type": "기타", "steps": [{"text": raw, "x": 50, "y": 50}], "tts_text": raw}

    screen_type = parsed.get("screen_type", "기타")
    raw_steps = parsed.get("steps") or [{"text": "안내를 가져오지 못했어요. 다시 시도해주세요.", "x": 50, "y": 50}]
    steps = []
    for s in raw_steps:
        if isinstance(s, str):
            steps.append(StepItem(text=s, x=50, y=50))
        else:
            steps.append(StepItem(text=s.get("text", ""), x=s.get("x", 50), y=s.get("y", 50)))
    tts_text = parsed.get("tts_text") or " ".join(s.text for s in steps)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO history (timestamp, screen_type, question, steps, tts_text) VALUES (?, ?, ?, ?, ?)",
            (
                timestamp, screen_type, req.question,
                json.dumps([s.model_dump() for s in steps], ensure_ascii=False),
                tts_text,
            ),
        )
        new_id = cur.lastrowid

    return AnalyzeResponse(
        id=new_id, timestamp=timestamp, screen_type=screen_type, steps=steps, tts_text=tts_text
    )


@app.get("/api/history")
def get_history(screen_type: str | None = None):
    with get_db() as conn:
        if screen_type and screen_type != "전체":
            rows = conn.execute(
                "SELECT * FROM history WHERE screen_type = ? ORDER BY id DESC LIMIT 50", (screen_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 50").fetchall()

    return [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "screen_type": r["screen_type"],
            "question": r["question"],
            "steps": json.loads(r["steps"]),
            "tts_text": r["tts_text"],
        }
        for r in rows
    ]


@app.delete("/api/history/{item_id}")
def delete_history(item_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
    return {"deleted": item_id}
