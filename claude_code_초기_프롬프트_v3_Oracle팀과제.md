# Claude Code 첫 프롬프트 — 무드픽(MoodPick) Oracle+FastAPI 팀 과제 버전 (v3)

아래 내용을 그대로 Claude Code에 붙여넣으면 됩니다.

---

## 프롬프트

```
너는 지금부터 "무드픽(MoodPick)"이라는 웹앱 프로젝트의 초기 스캐폴딩을
맡는다. 이 프로젝트는 두 가지 요구사항이 결합된 팀 실습 과제다:
(1) 대화 기반 개인화로 영화/도서를 추천하는 챗봇
(2) Oracle DB 설계 → 데이터 임포트/전처리 → 챗봇-DB 연동 →
    자연어(NL2SQL) 질의 → 시각화/지도/리포트 생성

여러 명이 협업하고 앞으로 계속 기능이 늘어날 예정이므로, 이번 첫 세팅은
"지금 당장 동작하는 것"보다 "팀원이 각자 기능을 붙이기 쉽고, QC(버그
재현/테스트)가 쉬운 구조"를 만드는 게 최우선이다.

# 프로젝트 개요
- 이름: 무드픽 (MoodPick)
- 프론트: Next.js (App Router) + React + TypeScript, Vercel 배포
- 백엔드: FastAPI (Python), Oracle DB와 상시 연결되는 서버로 별도 배포
- DB: Oracle (SQL Developer로 팀원이 공동 관리), python-oracledb(Thin 모드)로 연결
- 핵심 기능 두 갈래:
  1) 개인화 추천: 온보딩 + 대화 신호 + 👍👎 피드백을 결합한 하이브리드
     스코어링으로 영화/도서 추천
  2) NL2SQL: 사용자의 자유 질문을 LLM이 SQL로 변환해 Oracle에서 조회,
     결과를 자연어 요약 + 시각화(차트)/지도로 응답
- 하나의 채팅 인터페이스에서 두 기능이 공존하며, 발화 분류(라우팅)로 구분한다

# 아키텍처 원칙 (반드시 지킬 것)
1. **프론트/백엔드 명확히 분리**: Next.js는 UI와 API 호출만 담당한다.
   Oracle 연결, LLM 프롬프트 조립, SQL 생성/검증 로직은 전부 FastAPI에 둔다.
   프론트에서 Oracle이나 LLM API를 직접 호출하지 않는다.
2. **발화 라우팅을 명시적 단계로 분리**: 사용자 발화가 [추천 요청] /
   [NL2SQL 조회] / [시각화 요청] / [일반 대화] 중 무엇인지 분류하는 로직을
   `routers/classify.py` 같은 별도 모듈로 분리한다. 분류 결과에 따라 서로
   다른 서비스 함수를 호출하는 구조로 만들고, 분류와 실행 로직을 한
   함수에 섞지 않는다.
3. **추천 스코어링은 순수 함수로 분리**: cosine similarity, confidence
   계산, learning rate 업데이트 등은 `core/scoring/`에 부수효과(DB 접근,
   API 호출) 없는 순수 함수로 작성한다. 입력(벡터/프로필) → 출력(점수)만
   다룬다. Python이면 pytest로 테스트 가능한 형태를 반드시 유지한다.
4. **NL2SQL은 반드시 안전장치를 거친다**: LLM이 생성한 SQL 문자열을
   그대로 실행하지 않는다. `nl2sql/validator.py`에서 (a) SELECT 문으로만
   시작하는지, (b) 화이트리스트된 테이블/컬럼만 참조하는지, (c) 위험
   키워드(INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE)가 없는지 확인한 뒤에만
   실행 함수로 넘긴다. 이 검증을 우회하는 코드 경로를 만들지 않는다.
5. **Oracle 접근은 Repository 레이어로만**: SQLAlchemy 쿼리를 라우터
   핸들러에 직접 쓰지 않는다. `repositories/`에 함수로 모은다
   (예: userProfileRepository, itemRepository, interactionRepository,
   catalogQueryRepository).
6. **데이터 카탈로그를 코드로 관리**: NL2SQL 프롬프트에 넣을 테이블/컬럼
   설명을 하드코딩된 문자열로 흩어놓지 않고, `nl2sql/catalog.py` 또는
   JSON 파일 하나로 관리해서 팀원이 스키마 바뀔 때마다 한 곳만 수정하면
   되게 한다.
7. **외부 API 클라이언트는 인터페이스로 추상화**: TMDB / 카카오도서 /
   LLM(Gemini or Claude) / Kakao Map 클라이언트를 각각 별도 모듈로
   분리해서 목(mock) 테스트가 가능하게 한다.
8. **타입/스키마 우선**: Pydantic 모델로 API 요청/응답 스키마를 먼저
   정의하고 시작한다. 프론트의 TypeScript 타입도 이 스키마와 이름을
   맞춰서 혼선을 줄인다.
9. **에러는 명시적으로 처리**: Oracle 연결 실패, LLM 응답 파싱 실패,
   SQL 검증 실패 등은 각각 구분되는 예외 클래스로 만들어서 프론트에서
   원인을 구분해 표시할 수 있게 한다.

# 이번 단계에서 만들어야 할 것 (1단계 스캐폴딩)
1. Next.js(App Router) + TypeScript 프론트 프로젝트 생성, Tailwind 설정
2. FastAPI 백엔드 프로젝트 생성, 아래 폴더 구조로 정리:
   ```
   backend/
     app/
       main.py
       routers/
         chat.py           # 발화 수신 → 분류 → 라우팅
         classify.py       # 발화 분류 로직
       core/
         scoring/           # 추천 스코어링 순수 함수
       nl2sql/
         catalog.py         # 데이터 카탈로그 정의
         generator.py       # LLM에 SQL 생성 요청
         validator.py       # SELECT-only, 화이트리스트 검증
         executor.py        # 검증된 SQL만 Oracle에 실행
       repositories/
         user_profile_repo.py
         item_repo.py
         interaction_repo.py
         catalog_query_repo.py
       db/
         oracle_client.py   # python-oracledb 커넥션 풀
         models.py           # SQLAlchemy 모델
       api_clients/
         tmdb.py
         kakao_books.py
         llm_client.py
         kakao_map.py
       schemas/               # Pydantic 요청/응답 모델
   ```
3. 프론트 폴더 구조:
   ```
   src/
     features/
       chat/
       onboarding/
       recommendation/
       visualization/
     shared/
       components/
     lib/
       api/                  # FastAPI 호출 클라이언트
   ```
4. Oracle 연결 테스트용 최소 엔드포인트 (`/health/db`) — python-oracledb로
   접속 확인만 하는 수준
5. SQLAlchemy로 6장 DDL 기반 모델 정의 (user_taste_profile, items,
   interactions, onboarding_signals, conversation_signals, movies, books)
   — 정확한 컬럼은 첨부한 제안서(v3)의 6장 참고
6. `/chat` 엔드포인트 최소 구현: 아직 실제 분류/추천/NL2SQL 로직은
   비워두더라도, 요청을 받아서 더미 분류 결과를 반환하는 수준까지
7. 프론트에서 `/chat`을 호출해 응답을 화면에 표시하는 최소 채팅 UI 하나
   (엔드투엔드 연결 확인용)
8. pytest 세팅 — `core/scoring/`과 `nl2sql/validator.py`에 대한 예시
   테스트 파일 (검증 로직은 특히 반드시 테스트 필요: SELECT 통과,
   DELETE 차단, 화이트리스트 밖 테이블 차단 케이스)
9. `.env.example` 작성 — 아래 항목을 최소한으로 포함해 팀원이 각자
   `.env`로 채우도록 안내 (실제 키/비번은 커밋 금지):
   - Oracle 접속정보 (host/port/service_name/user/password 등)
   - TMDB API 키
   - 카카오 도서 검색 API 키
   - LLM API 키 (Gemini 또는 Claude — 팀 확정 전이면 둘 다 자리만 비워둠)
   - Kakao Map API 키
10. `PROJECT_SUMMARY.md` 작성 — 프로젝트 개요, 폴더 구조, DB 스키마
    요약, 최근 변경 이력 섹션을 포함한다. `CLAUDE_v3_Oracle팀과제.md`가
    세션 시작 시 이 파일을 먼저 읽으라고 지시하므로, 1단계 스캐폴딩
    완료 시점에 반드시 존재해야 한다.

# 하지 말아야 할 것
- 실제 추천 스코어링 로직, NL2SQL 프롬프트 세부 튜닝, 시각화 컴포넌트는
  이번 단계에서 완성하지 않는다. 구조만 잡는다.
- LLM이 생성한 SQL을 검증 없이 실행하는 코드 경로를 절대 만들지 않는다.
- 프론트에서 Oracle/LLM API에 직접 접근하는 코드를 넣지 않는다.
- Oracle 접속 정보나 API 키를 코드에 하드코딩하지 않는다.

# 진행 방식
- 참고: `CLAUDE_v3_Oracle팀과제.md` 5장에는 "확인 없이 5개 이상 파일 동시
  대량 수정 금지" 규칙이 있다. 이번 1단계 스캐폴딩은 폴더 구조 승인을
  받은 뒤 다수 파일을 한 번에 생성하는 것이 목적이므로 이 규칙의 예외로
  취급한다 (승인 자체가 대량 생성에 대한 사전 동의). 스캐폴딩 이후의
  일반 작업에서는 5개 파일 제한이 그대로 적용된다.
- 폴더 구조를 먼저 제안하고 내 확인을 받은 뒤 파일 생성을 시작해줘.
- 각 레이어(routers/core/nl2sql/repositories/db)가 왜 이렇게 나뉘는지
  주석이나 README로 짧게 설명을 남겨줘 — 팀원들이 참고할 수 있게.
- 완료되면 프론트(`npm run dev`)와 백엔드(`uvicorn`) 둘 다 실행 확인하고,
  `/health/db`로 Oracle 연결이 실제로 되는지도 확인해줘 (Oracle 접속정보는
  내가 별도로 `.env`에 채워둘게).
```

---

## 참고
- 이 프롬프트는 제안서 v3(Oracle+팀과제 통합)의 4장(스택), 5장(NL2SQL
  파이프라인), 6장(데이터 모델)을 전제로 합니다. Claude Code 세션에 제안서
  파일을 같이 첨부하면 스키마·검증 규칙을 다시 설명할 필요가 없습니다.
- 2단계(데이터 임포트/전처리), 3단계(NL2SQL 실제 구현+검증셋 테스트),
  4단계(개인화 스코어링), 5단계(시각화/지도)는 1단계 결과물을 보고
  이어서 짜는 게 정확도가 높습니다.
