# 개인화 영화·도서 추천 챗봇 프로젝트 제안서 (팀 과제 통합 버전)

**프로젝트명(가칭):** 무드픽 (MoodPick)
**작성일:** 2026-07-15 (v3 — 팀 실습 과제 요구사항 통합: Oracle DB + NL2SQL + 시각화)
**작성자:** 잼민 (팀 프로젝트)

---

## 1. 프로젝트 개요

### 1.1 한 줄 정의
사용자와의 대화, 명시적 피드백, 온보딩 설문을 결합한 하이브리드 개인화 알고리즘으로 영화·도서를 추천하고, 동시에 자유로운 자연어 질의(NL2SQL)와 시각화/리포트 생성까지 지원하는 웹 챗봇. Oracle DB를 데이터 저장소로 사용한다.

### 1.2 배경 — 두 요구사항의 결합
- **개인 프로젝트 시나리오**: 대화 기반으로 취향을 학습해 영화/도서를 추천하는 챗봇
- **팀 실습 과제 요구사항**: 데이터 모델 설계 → Oracle 테이블 생성 → 데이터 임포트/전처리 → 챗봇-DB 연동 → NL2SQL(자연어→SQL) → 시각화/지도/리포트 생성
- 두 요구사항이 "영화/도서 데이터를 다루는 챗봇"이라는 공통분모를 가지므로, 하나의 프로젝트로 통합해서 진행

### 1.3 목표
- 원래 개인화 추천 시나리오(온보딩 → 대화 → 피드백 → 프로필 갱신)를 그대로 구현
- 동일한 챗봇 창에서 자유 질의("2010년대 한국 영화 뭐가 인기였어?")에 NL2SQL로 즉석 응답
- "내 취향 분포 보여줘", "근처 서점 찾아줘" 같은 명령에 시각화/지도로 응답
- Oracle DB 설계·운영 경험을 실제 동작하는 서비스로 증명 (팀 과제 평가 기준 충족 + 포트폴리오 활용)

### 1.4 차별점
| 기존 서비스/과제 예시 | 이 프로젝트 |
|---|---|
| 단순 CRUD 챗봇 데모 | 개인화 추천 로직이 실제로 학습되는 챗봇 |
| NL2SQL만 단독 구현 | 추천 챗봇 + NL2SQL이 하나의 대화 인터페이스에 자연스럽게 공존 |
| 정적 리포트 생성 | 대화 명령으로 즉석 시각화/지도 생성 |

---

## 2. 사용자 시나리오

### 2.1 개인화 추천 흐름 (기존 시나리오, 유지)
1. 웹 접속 → 온보딩(선호작품 입력 → 양자택일 스와이프 → 무드 슬라이더 → 성향 미니퀴즈) → 초기 취향 프로필 생성 (Oracle에 저장)
2. "요즘 야근이 많아서 가볍게 웃을 수 있는 거 보고 싶어" 입력
3. 챗봇이 상황·취향 인식 → 코미디/힐링 장르 위주 3~5개 카드 추천
4. 👍👎 반응 → 프로필 즉시 갱신
5. 이후 대화부터 더 정교한 추천

### 2.2 NL2SQL 질의 흐름 (신규, 팀 과제 요구사항)
1. "2010년대 개봉한 한국 영화 중 평점 높은 순으로 5개 보여줘" 입력
2. 챗봇이 이 발화를 추천 요청이 아닌 데이터 조회 요청으로 라우팅
3. LLM이 데이터 카탈로그(테이블/컬럼 설명)를 참고해 SELECT 쿼리 생성
4. FastAPI가 Oracle에 쿼리 실행, 결과를 챗봇이 자연어로 요약해 응답

### 2.3 시각화/리포트 흐름 (신규, 팀 과제 요구사항)
1. "내 장르 취향 분포 보여줘" 입력 → 프로필 데이터 기반 차트 렌더링
2. "이 근처 도서관/서점 찾아줘" 입력 → 지도에 위치 마커 표시

---

## 3. 기능 명세

### 3.1 필수 기능 (MVP)
**개인화 추천**
- [ ] 온보딩 플로우 (4단계)
- [ ] 채팅 기반 추천 인터페이스
- [ ] 대화 중 선호 신호 자동 추출 (세션 종료 시 배치)
- [ ] 추천 카드 👍👎 피드백
- [ ] 개인화 스코어링 기반 추천 랭킹

**팀 과제 요구사항**
- [ ] Oracle 테이블 설계 및 생성 (요구사항 1)
- [ ] 외부 API(TMDB, 카카오도서)로 수집한 데이터 일괄 임포트 (요구사항 2)
- [ ] 데이터 전처리 - 중복/결측치/이상치 삭제·수정·삽입 (요구사항 3)
- [ ] 챗봇-Oracle DB 연동 검증 (요구사항 4)
- [ ] 프롬프트 엔지니어링으로 챗봇 제약/편의성 개선 (요구사항 5)
- [ ] 데이터 카탈로그 작성 (테이블/컬럼 설명, NL2SQL 정확도용) (요구사항 6)
- [ ] NL2SQL 결과 정합성 검증 (요구사항 7)
- [ ] 시각화(차트)·지도·리포트 생성 (요구사항 8)

### 3.2 선택 기능
- [ ] 추천 이유 설명
- [ ] MBTI 참고 정보 (계산 미반영)
- [ ] 취향 프로필 레이더 차트
- [ ] 다크모드

### 3.3 라우팅 규칙 — 추천 요청 vs NL2SQL 요청 구분
같은 채팅창에서 두 기능이 공존하므로, 사용자 발화를 분류하는 규칙이 필요함:

```
사용자 발화
   → LLM에 "이 발화가 [개인화 추천 요청] / [데이터 조회(NL2SQL)] /
     [시각화 요청] / [일반 대화] 중 무엇인지" 분류하도록 우선 요청
   → 분류 결과에 따라 서로 다른 파이프라인으로 라우팅
```
- 개인화 추천 요청 → 7장 스코어링 파이프라인
- 데이터 조회 → NL2SQL 파이프라인 (5장)
- 시각화 요청 → 조회 결과를 차트/지도 컴포넌트로 렌더링

---

## 4. 기술 스택

### 4.1 프레임워크
| 항목 | 선택 | 이유 |
|---|---|---|
| 프론트엔드 | Next.js (App Router) + TypeScript | 채팅 UI, 기존 계획 재사용 |
| 백엔드 | **FastAPI (Python)** | Oracle 연결 안정성, NL2SQL 후처리·시각화(pandas/plotly)에 강점, 기존 FastAPI 경험 재사용 |
| 스타일 | Tailwind CSS | 빠른 프로토타이핑 |

### 4.2 데이터
| 항목 | 선택 | 이유 |
|---|---|---|
| DB | **Oracle** (SQL Developer로 팀원 공동 설계/조회) | 과제 요구사항 |
| Oracle 드라이버 | **python-oracledb** (Thin 모드) | Instant Client 설치 없이도 연결 가능해 팀원 환경 세팅 부담 적음 |
| ORM | SQLAlchemy (Oracle dialect) | 팀원 간 쿼리 일관성, 마이그레이션 관리 |

### 4.3 외부 API
| 용도 | API |
|---|---|
| 영화 메타데이터 수집(초기 임포트용) | TMDB API |
| 도서 메타데이터 수집(초기 임포트용) | 카카오 도서 검색 API |
| 대화/선호추출/NL2SQL 생성 | Gemini Flash 또는 Claude API |
| 지도 표시 | Kakao Map API |

### 4.4 아키텍처 구조
```
Frontend (Next.js)
  └─ 채팅 UI, 추천 카드, 온보딩, 차트/지도 렌더링

Backend (FastAPI)
  ├─ /chat          → 발화 분류 후 라우팅 (추천 / NL2SQL / 시각화 / 일반대화)
  ├─ /recommend      → core/scoring 순수 함수 호출 + Oracle 조회
  ├─ /nl2sql          → LLM SQL 생성 + 화이트리스트 검증 + Oracle 실행
  ├─ /visualize       → 조회 결과 → 차트 데이터 가공
  └─ oracle_client.py → python-oracledb 커넥션 풀 관리

Oracle DB
  ├─ items, interactions, user_taste_profile, onboarding_signals,
  │  conversation_signals (개인화용 테이블)
  └─ movies, books (팀 과제용 원본 데이터 테이블, 조회 대상)
```

### 4.5 배포
- 프론트: Vercel
- 백엔드(FastAPI): 상시 구동 서버 필요 (Oracle 커넥션 풀 유지) — 학교/개인 서버, 또는 클라우드 VM(예: Oracle Cloud Free Tier — Oracle DB와 궁합 좋음)
- Oracle DB: 팀 로컬 Oracle XE 또는 Oracle Cloud Autonomous DB (Free Tier)

---

## 5. NL2SQL 파이프라인 (팀 과제 핵심)

### 5.1 데이터 카탈로그
LLM이 정확한 SQL을 생성하도록 스키마 설명을 프롬프트에 포함:
```json
{
  "movies": {
    "description": "영화 메타데이터",
    "columns": {
      "title": "영화 제목",
      "release_year": "개봉연도",
      "genre": "장르 (콤마구분)",
      "rating": "평균 평점 (0~10)",
      "country": "제작 국가"
    }
  },
  "books": { "...": "..." }
}
```

### 5.2 안전장치 (QC 필수)
- LLM이 생성한 SQL은 **SELECT문만 허용** — INSERT/UPDATE/DELETE/DROP/ALTER 키워드 감지 시 실행 차단
- 화이트리스트된 테이블/컬럼만 노출, 카탈로그에 없는 테이블 참조 시 거부
- 자동으로 `FETCH FIRST N ROWS ONLY` 등 결과 개수 제한
- 실행 전 EXPLAIN PLAN으로 비정상적으로 무거운 쿼리 여부 사전 체크 (선택)

### 5.3 검증 흐름 (요구사항 7)
- 생성된 SQL과 실행 결과를 로그로 남겨, 팀원이 의도한 질문과 실제 결과가 일치하는지 수동 검증 세트 구성 (예: 질문 20개 세트로 정확도 측정)

---

## 6. 데이터 모델 (Oracle DDL 개요)

```sql
-- 개인화용 테이블
CREATE TABLE user_taste_profile (
  id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  genre_weights  CLOB,   -- JSON 저장
  mood_weights   CLOB,
  novelty_pref   NUMBER,
  intensity_pref NUMBER,
  confidence_score NUMBER,
  mbti           VARCHAR2(4),
  updated_at     TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE items (
  id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  item_type    VARCHAR2(10) CHECK (item_type IN ('movie','book')),
  title        VARCHAR2(200),
  external_id  VARCHAR2(50),
  metadata     CLOB,
  tags         VARCHAR2(500)
);

CREATE TABLE interactions (
  id         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  item_id    NUMBER REFERENCES items(id),
  action     VARCHAR2(10) CHECK (action IN ('liked','disliked','skipped','watched')),
  rating     NUMBER,
  created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE onboarding_signals (
  id         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source     VARCHAR2(10) CHECK (source IN ('fav_item','swipe','slider','quiz')),
  raw_value  CLOB,
  created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE TABLE conversation_signals (
  id                    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id            VARCHAR2(50),
  extracted_preference  CLOB,
  raw_snippet           VARCHAR2(2000),
  created_at            TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- 팀 과제 조회 대상 원본 데이터 (NL2SQL용)
CREATE TABLE movies (
  id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title         VARCHAR2(200),
  release_year  NUMBER,
  genre         VARCHAR2(100),
  rating        NUMBER,
  country       VARCHAR2(50)
);

CREATE TABLE books (
  id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title    VARCHAR2(200),
  author   VARCHAR2(100),
  genre    VARCHAR2(100),
  pub_year NUMBER
);
```
> 실제 팀 데이터 모델 해석(요구사항 1)에 맞춰 컬럼은 조정 필요. JSON 필드는 Oracle 21c+ 라면 `JSON` 타입 사용 가능, 아니라면 CLOB + 애플리케이션 레벨 파싱.

---

## 7. 개인화 추천 알고리즘 (기존과 동일, 저장소만 Oracle로)

### 7.1 아이템 벡터화 / 프로필 업데이트 / 콜드스타트 / 스코어링
> 알고리즘 자체는 이전 버전과 동일 (순수 함수로 구현, 플랫폼 무관). 상세 공식은 이전 제안서 v2의 7장 참고.

```
final_score =
    confidence × (0.6 × cosine_sim(user_profile, item_vector) + 0.4 × recency_bonus)
  + (1 - confidence) × popularity_score
  - penalty(이미 소비함, 명시적 비선호와 유사)
```

---

## 8. 개발 일정 (팀 분업 고려, 3~4주)

| 단계 | 내용 | 기간 |
|---|---|---|
| 1단계 | Oracle 테이블 설계·생성, 팀원별 SQL Developer 세팅, FastAPI+Next.js 골격 | 3~4일 |
| 2단계 | TMDB/카카오도서 데이터 수집·임포트, 전처리 스크립트 | 3~4일 |
| 3단계 | 챗봇-DB 연동, 발화 라우팅(추천/NL2SQL/시각화), 데이터 카탈로그 작성 | 4~5일 |
| 4단계 | 개인화 스코어링 반영, 온보딩, 👍👎 | 3~4일 |
| 5단계 | 시각화·지도·리포트, NL2SQL 정확도 검증셋 테스트 | 3~4일 |
| 6단계 | 마감(에러 핸들링, 발표 준비, 배포) | 2~3일 |
| **합계** | | **약 3.5~4주** |

---

## 9. 리스크 및 대응

| 리스크 | 대응 |
|---|---|
| LLM이 잘못된 SQL 생성 (존재하지 않는 컬럼 등) | 데이터 카탈로그 정교화 + 화이트리스트 검증 |
| NL2SQL로 위험한 쿼리(DELETE 등) 생성 시도 | SELECT 전용 파서/키워드 필터링 |
| Oracle 커넥션 풀 고갈 (동시 접속 다수) | FastAPI에서 커넥션 풀 크기 제한, 타임아웃 설정 |
| 팀원 간 Oracle 환경 불일치 | python-oracledb Thin 모드로 통일, 접속 정보는 `.env`로 공유 |
| 추천 로직과 NL2SQL 라우팅 오분류 | 분류 프롬프트에 예시(few-shot) 다수 포함, 애매하면 "추천/조회 중 뭘 원하세요?" 되묻기 |

---

## 10. 성공 기준

- 팀 과제 8개 요구사항 전항목 충족 확인
- 개인화 추천이 실제로 대화·피드백에 따라 달라지는 것을 시연
- NL2SQL 질의 20개 세트 기준 정확도 측정 결과 제시
- 시각화/지도가 챗봇 명령 한 번으로 자연스럽게 렌더링

---

## 11. 다음 액션

- [ ] 팀원과 Oracle 테이블 컬럼 최종 확정 (6장 DDL 초안 기반 리뷰)
- [ ] SQL Developer로 각자 Oracle 계정/스키마 세팅
- [ ] TMDB/카카오도서 초기 데이터 수집 스크립트 작성
- [ ] FastAPI + python-oracledb 연결 테스트
- [ ] 데이터 카탈로그 초안 작성
