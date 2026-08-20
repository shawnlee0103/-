# 짚어드림 — 실제 배포 가이드 (완전 무료 버전)

Gemini API 무료 티어를 사용해서 **비용 0원**으로 실시간 AI 분석까지 되는 서비스를 배포합니다.

```
1. Gemini API 키 발급받기 (무료, 카드 등록 불필요)     (5분)
2. GitHub에 코드 올리기                              (10분)
3. Render에 백엔드 배포하기                           (15분)
4. Vercel에 프론트엔드 배포하기                        (10분)
```
 
---
  
## 1단계. Gemini API 키 발급받기 (무료)

1. https://aistudio.google.com/apikey 접속 → 구글 계정으로 로그인
2. "Create API key" 클릭
3. 생성된 키를 복사해서 메모장에 저장 (`AIza...`로 시작)
4. **신용카드 등록 필요 없음** — 무료 티어 한도 내에서는 완전 무료로 사용 가능
5. 무료 티어 한도는 시기에 따라 바뀔 수 있으니, 발급 페이지에서 현재 한도를 한 번 확인해두세요

---

## 2단계. GitHub에 코드 올리기 (무료)

1. https://github.com 회원가입/로그인
2. **New repository** → 이름은 `jipeodeurim` 등 원하는 대로
3. **Public**으로 설정 → **Create repository**
4. `backend/`, `frontend/` 폴더를 통째로 업로드 (uploading an existing file)
5. **Commit changes**

---

## 3단계. Render에 백엔드 배포하기 (무료)

1. https://render.com → GitHub 계정으로 로그인
2. **New +** → **Web Service** → 방금 만든 저장소 선택
3. 설정값:
   | 항목 | 값 |
   |---|---|
   | Root Directory | `backend` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | `Free` |
4. **Environment Variables** 추가:
   - `GEMINI_API_KEY` = 1단계에서 발급받은 키
5. **Create Web Service** → 3~5분 대기
6. 완료되면 `https://xxx.onrender.com` 주소가 생김 → 이 주소 복사해두기
7. 그 주소로 접속해서 `{"status":"ok",...}`가 뜨면 성공

> ⚠️ Render 무료 플랜은 15분간 요청 없으면 잠들어요. 발표/촬영 직전에 한 번 미리 접속해서 깨워두세요.

---

## 4단계. Vercel에 프론트엔드 배포하기 (무료)

1. `frontend/index.html`을 열어서 이 줄을 찾기:
   ```js
   const BACKEND_URL = "http://localhost:8000";
   ```
2. 3단계에서 받은 Render 주소로 변경:
   ```js
   const BACKEND_URL = "https://xxx.onrender.com";
   ```
3. 수정한 파일을 GitHub에 다시 업로드
4. https://vercel.com → GitHub 계정으로 로그인
5. **Add New** → **Project** → 저장소 선택
6. **Root Directory**를 `frontend`로 지정 → **Deploy**
7. 1~2분 후 `https://프로젝트명.vercel.app` 링크 생성 → 완료!

---

## 확인 체크리스트

- [ ] Render 백엔드 주소로 브라우저 접속 시 `{"status":"ok"}` 확인
- [ ] Vercel 프론트엔드 주소로 접속 시 짚어드림 화면 정상 표시
- [ ] 실제 화면 캡처 업로드 → 분석 버튼 클릭 → 단계별 안내 + 핀 표시 확인
- [ ] 히스토리 탭에서 방금 분석한 기록이 보이는지 확인
- [ ] 팀원들에게 Vercel 링크 공유 → 각자 사용해보고 히스토리에 쌓이는지 확인

---

## 막혔을 때

| 증상 | 원인 | 해결 |
|---|---|---|
| "문제가 발생했어요" | BACKEND_URL이 아직 localhost | 4단계 1~2번 재확인 |
| CORS 에러 | 도메인 제한 문제 | Render 환경변수에 `FRONTEND_ORIGIN=*` 추가 후 재배포 |
| "GEMINI_API_KEY가 설정되지 않았습니다" | Render 환경변수 누락 | 3단계 4번 재확인 |
| 응답이 느림/타임아웃 | 무료 플랜 서버가 잠들어 있었음 | 몇 초 후 재시도 |
