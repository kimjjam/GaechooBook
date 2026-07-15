# PROJECT_SUMMARY — 무드픽 (MoodPick)

> 세션 시작 시 이 파일을 먼저 읽는다. 상세 아키텍처 규칙은 `CLAUDE_v3_Oracle팀과제.md`, 기능 명세는 `개인화_추천챗봇_제안서_v3_Oracle팀과제.md` 참고.

## 개요
- 첫 방문 시 취향을 받고, 재방문 시 Oracle에 저장한 사용자 취향을 복원하여 TMDB의 최신 영화 후보를 개인화 추천하는 서비스.
- Oracle의 `movies/books`와 NL2SQL은 팀 과제용 데이터 탐색 기능으로 분리해 유지한다.
- 프론트: Next.js(App Router) + TypeScript + Tailwind, Vercel 배포 예정.
- 백엔드: FastAPI(Python), python-oracledb(Thin 모드)로 Oracle 상시 연결.
- 사용자 발화는 [추천 요청] / [NL2SQL 조회] / [시각화 요청] / [일반 대화] 중 하나로 분류되어 서로 다른 파이프라인으로 라우팅된다.

## 폴더 구조
```
개추북/
  frontend/                Next.js 앱
    src/app/                라우트 (page.tsx가 최소 채팅 UI)
    src/features/chat/       채팅 UI + 타입
    src/features/onboarding|recommendation|visualization/  (자리만, 추후 단계에서 구현)
    src/shared/components/   공용 UI 컴포넌트 (자리만)
    src/lib/api/chatClient.ts  FastAPI /chat 호출
  backend/                  FastAPI 앱
    app/
      main.py                 앱 조립, CORS
      routers/                 chat.py(분류→라우팅), classify.py(분류 로직), health.py(/health/db)
      core/scoring/            추천 스코어링 순수 함수 (부수효과 없음, pytest 가능)
      nl2sql/                  catalog.py(스키마 단일 소스), generator.py, validator.py(안전검증), executor.py
      repositories/            Oracle 접근은 이 레이어로만 (ORM 3개 + catalog_query_repo)
      db/                      oracle_client.py(커넥션 풀+SQLAlchemy engine), models.py(7개 테이블)
      api_clients/             tmdb.py, kakao_books.py, llm_client.py, kakao_map.py (모두 스텁)
      schemas/chat.py           Pydantic 요청/응답
    tests/                     core/scoring, nl2sql/validator 테스트
  PROJECT_SUMMARY.md (이 파일)
  CLAUDE_v3_Oracle팀과제.md
  개인화_추천챗봇_제안서_v3_Oracle팀과제.md
```

## DB 스키마 요약 (Oracle, 상세는 제안서 6장)
- **개인화용**: `users`, `user_taste_profile`, `interactions`, `onboarding_signals`, `conversation_signals`
- **NL2SQL 조회 대상 원본 데이터**: `movies`, `books`
- 컬럼 정의는 `backend/app/db/models.py`가 단일 소스. 스키마 변경은 팀 전체 상의 후 이 파일만 수정.
- NL2SQL 화이트리스트/설명은 `backend/app/nl2sql/catalog.py`가 단일 소스 (현재 movies, books만 노출).

## 환경 변수
- 백엔드: `backend/.env.example` 참고 (Oracle 접속정보, TMDB, 카카오도서, 네이버/알라딘/구글도서, Gemini, Kakao Map, FRONTEND_ORIGIN)
- 프론트: `frontend/.env.local.example` 참고 (`NEXT_PUBLIC_API_BASE_URL`)

## 로컬 Oracle 실행 (Docker)
팀원 각자 로컬에서 동일하게 재현하려면 (Docker Desktop 실행 후):
```
docker run -d \
  --name moodpick-oracle \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=<sys용 비밀번호> \
  -e APP_USER=moodpick \
  -e APP_USER_PASSWORD=<앱용 비밀번호> \
  -v moodpick-oracle-data:/opt/oracle/oradata \
  gvenzl/oracle-xe:21-slim
```
- 첫 부팅 완료까지 `docker logs -f moodpick-oracle`로 "DATABASE IS READY TO USE!" 확인.
- `.env`: `ORACLE_HOST=localhost`, `ORACLE_PORT=1521`, `ORACLE_SERVICE_NAME=XEPDB1`, `ORACLE_USER=moodpick`, `ORACLE_PASSWORD=<앱용 비밀번호>`
- 테이블 생성(최초 1회): `backend`에서 `python -c "from app.db.oracle_client import _get_engine; from app.db.models import Base; Base.metadata.create_all(_get_engine())"`
- 볼륨(`moodpick-oracle-data`)에 데이터가 남으므로 컨테이너를 지워도(`docker rm`) 데이터는 보존됨. 완전 초기화하려면 볼륨도 함께 삭제.

## 최근 변경 이력
- 2026-07-15: 보안 로그인 추가 — 익명 온보딩 취향을 회원가입 계정으로 승계하고 다른 기기 로그인에서 복원. Argon2id 비밀번호 해시, Oracle 서버 저장형 세션, HttpOnly/SameSite 쿠키, 세션별 CSRF 검증, 14일 만료, 사용자당 최대 5개 세션, 로그인 5회 실패 시 15분 잠금을 적용. 로그인 후 익명 토큰을 계정에서 분리해 로그아웃 우회 접근을 방지.
- 2026-07-15: 메인 사용자 흐름 재정렬 — 브라우저 방문자 토큰으로 신규/재방문 사용자를 구분하고, 최초 온보딩 결과와 피드백을 Oracle에 저장하도록 변경. 추천 영화 원본은 Oracle 시드가 아니라 TMDB 실시간 API를 사용하며, 개인화 스코어링 후 카드로 표시. `movies/books`와 NL2SQL은 과제용 데이터 탐색 기능으로 유지.
- 2026-07-15: 1단계 스캐폴딩 완료 — 프론트/백엔드 골격, 계층 분리(routers/core/nl2sql/repositories/db), `/health/db`, 더미 `/chat`, pytest 세팅, `.env.example` 작성.
- 2026-07-15: 검증 중 발화 분류 버그 발견·수정 — "보여줘"가 시각화로 오분류되어 제안서 2.2 NL2SQL 예시가 잘못 라우팅되던 것을 `classify.py` 키워드 정리로 해결, 회귀 테스트 추가(`tests/routers/test_classify.py`).
- 2026-07-15: 프론트 `next` 버전을 14.2.5 → 14.2.35로 패치 (critical 취약점 다수 해소). eslint/postcss 관련 잔여 moderate/high 취약점은 Next 16 breaking change가 필요해 보류.
- 2026-07-15: 로컬 Oracle XE(Docker, `gvenzl/oracle-xe:21-slim`) 신규 구축, `.env`에 실접속정보 반영, `/health/db` 200 확인, 7개 테이블 실제 생성 완료.
- 2026-07-15: `moodpick` DB 유저 비밀번호를 사용자 요청으로 변경(`ALTER USER`), `.env` 갱신 후 재연결 확인.
- 2026-07-15: TMDB/카카오도서 실API로 시드 데이터 수집(`app/scripts/import_seed_data.py`) — movies 30건(전역 인기작+한국 2010년대), books 47건 적재.
- 2026-07-15: DB 스키마 버그 수정 — `db/models.py`의 `Numeric` 컬럼(rating 등)에 scale을 안 줘서 Oracle이 `NUMBER(*,0)`으로 생성, 소수점이 정수로 잘리던 문제(예: 8.596→9) 발견·수정(`Numeric(4,2)` 등으로 명시). 영향받은 테이블 전체 재생성 후 시드 데이터 재적재.
- 2026-07-15: `/chat`의 recommend·nl2sql을 실제 파이프라인에 연결 — 최초에는 Oracle 인기순 추천으로 구현했으며, 이후 메인 영화 추천을 TMDB+사용자 프로필 방식으로 교체. NL2SQL은 `llm_client.py` → `generator.py` → `validator.py`/`executor.py` 흐름을 유지.
- 2026-07-15: Gemini API 키 반영, NL2SQL 파이프라인 실제 검증 완료 — "2010년대 한국 영화 평점 높은 순" 질의에 LLM이 생성한 SQL이 validator 통과 후 Oracle에서 실제 5건(기생충, 소원 등) 조회됨을 `/chat`으로 확인. 이 프로젝트는 `gemini-2.0-flash`/`gemini-2.5-flash` 무료 할당량이 0으로 막혀 있어 대체 모델로 전환.
- 2026-07-15: 사용자 요청으로 `GEMINI_MODEL`을 `gemini-3.5-flash`로 최종 확정(`.env`, `.env.example`, 코드 기본값 모두 반영). `/chat` 재검증 완료.
