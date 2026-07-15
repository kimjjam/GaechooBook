# MoodPick 배포 구조

## 권장 구성

1. **Frontend**: Vercel의 `frontend/` 프로젝트
2. **API**: OCI Always Free Ampere VM에서 Docker Compose로 FastAPI 상시 실행
3. **DB**: OCI Always Free Autonomous Transaction Processing
4. **HTTPS**: API 도메인을 OCI VM에 연결하고 Caddy가 인증서를 자동 관리

Vercel에는 비공개 환경 변수 `BACKEND_URL=https://api.example.com`만 설정한다.
브라우저는 `/api/backend/*`를 호출하고 Next.js Route Handler가 API로 전달하므로
로그인 쿠키는 Vercel 사이트의 first-party 쿠키로 유지된다.

## OCI VM 실행

서버의 프로젝트 루트에서:

```bash
export API_DOMAIN=api.example.com
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml ps
```

`restart: unless-stopped` 때문에 VM이나 Docker가 재시작돼도 API와 Caddy가 자동으로 다시 올라온다.

운영용 `backend/.env`에서는 최소한 다음을 확인한다.

```env
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
ORACLE_POOL_MAX=3
SQLALCHEMY_POOL_SIZE=3
SQLALCHEMY_MAX_OVERFLOW=2
```

OCI 방화벽/보안 목록에는 외부에서 `80`, `443`만 열고 Oracle 포트와 API의 `8000`은 공개하지 않는다.
