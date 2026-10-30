# PostgreSQL 공유 체험 준비

2026-10-30 UTC. **로컬 구현·검증 준비이며 외부 연결 승인은 아직 대기 중**이다. 외부 Supabase DDL·권한·비밀키·Auth·Vercel 환경변수·배포를 실행하지 않았다. 기존 SQLite 개발 모드와 [단일 프로세스 체험](preview-deployment.md)은 유지한다. 이 문서가 승인이나 공개 URL 발급의 증거는 아니다.

## 대상과 최소 변경

관리 작업이 기존 Supabase 프로젝트 `vgabkqvxotfmofhaijwz`의 서울 리전·PostgreSQL 17·`public.crews`, `public.profiles` 등 기존 테이블을 읽어 확인했다. 기존 데이터는 다른 제품의 데이터로 취급한다. 우리 코드는 Supabase Auth/API 키를 사용하지 않고 전용 PostgreSQL login role로만 연결하도록 준비했다.

공유 모드의 원본 저장소는 PostgreSQL이다. guest token 해시, 만료, 요청 예산, 진행 요청 lease, 사용자/세션/메시지/모임/출석/기념물 데이터가 모두 전용 스키마에 있다. 프로세스 메모리 registry·로컬 SQLite·서버리스 `/tmp`의 수명에 의존하지 않는다. UI는 이 모드에서 서버 재시작 시 초기화된다는 문구를 표시하지 않는다.

코드 경계:

- `community/postgres.py`: 고정된 서버 SQL의 플레이스홀더·행·RETURNING·ON CONFLICT 어댑터와 TLS/역할/권한 preflight.
- `community/postgres_preview.py`: 공유 guest 생성·예산·만료/lease 및 tenant 트랜잭션.
- `community/database.py`: 검증된 guest에 따라 PostgreSQL 트랜잭션을 선택. 기존 SQLite 경로 유지.
- `migrations/001_preview_postgres.sql`: 별도 검토 후 한 번 실행하는 초기 DDL. 앱 시작 중 자동 migration은 없다. 이름 충돌 시 실패하며 기존 스키마를 덮어쓰지 않는다.
- `api/index.py`, `requirements.txt`, `.python-version`, `vercel.json`: Python 3.12 ASGI·정적 자산 포함·30초 함수 예산의 배포 후보 설정. 실제 Vercel 빌드/라우팅은 미검증이다.

## 최소 권한 경계

| 대상 | 허용 / 금지 |
|---|---|
| `ourcommunity_preview_owner` | 스키마 소유 전용 NOLOGIN. runtime에 membership을 주지 않음 |
| `ourcommunity_preview_runtime` | 초기 NOLOGIN, 승인 후 별도 비밀정보로 LOGIN. NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS, 연결 한도 8 |
| `ourcommunity_preview` | runtime USAGE + 필요한 테이블 SELECT/INSERT/UPDATE/DELETE, identity sequence USAGE. gate 행은 SELECT·created_at UPDATE만. DDL·TRUNCATE·소유권·새 역할 부여 없음 |
| 기존 public/Auth/다른 스키마 | 기존 테이블·정책·함수·Auth·API exposed schema를 변경하지 않음. 광범위 service_role·anon·프로젝트 관리자 키를 앱에 저장하지 않음 |
| 연결 | 전용 role의 current_user와 session_user 일치. 외부 호스트는 `sslmode=verify-full` 필수; 신뢰 CA는 `sslrootcert=system` 또는 확인한 CA bundle. TLS 검사를 끄지 않음 |

DDL 실행자에게 새 owner 역할을 잠시 SET할 수 있게 하는 membership만 트랜잭션 안에서 부여하고 끝에 회수한다. 기존 관리자 권한을 영구 확대하는 단계가 아니다. 실제 Supabase의 DDL 권한과 역할 생성 지원 여부는 승인 후 확인해야 한다.

`NOINHERIT`는 `PUBLIC`의 기존 권한을 없애지 않는다. `scripts/check_preview_postgres.py`는 다른 스키마의 유효한 테이블·sequence·함수 권한, schema CREATE, role membership, runtime 객체 소유, 도메인 RLS를 읽기 검사한다. `pgsodium`처럼 `pg`로 시작하지만 시스템 `pg_` 접두사가 아닌 스키마도 검사한다. 앱도 첫 연결에 검사하고 실패하면 비밀정보 없는 503을 반환한다. 이 검사는 권한 변경을 지속 감시하는 시스템은 아니므로 운영 변경 후 다시 실행해야 한다.

다른 제품의 PUBLIC grant 때문에 이 역할에도 데이터/함수 권한이 생기면 **중단**한다. 한 역할에만 PUBLIC 권한을 거부하는 PostgreSQL DENY는 없다. 기존 권한을 임의로 회수하지 않고, 별도 데이터베이스/프로젝트 또는 정확히 범위를 정한 후속 승인이 필요하다. DB catalog와 기본 내장 기능 접근까지 사라지는 계정이라고 주장하지 않는다.

## 테넌트·동시성·수명

모든 도메인 테이블은 `tenant_id`를 가지며 PK/UNIQUE/FK와 충돌 처리에도 tenant를 포함한다. ENABLE/FORCE RLS의 USING/WITH CHECK는 트랜잭션 안의 `ourcommunity.tenant_id`와 행을 비교한다. 이 값은 클라이언트 입력에서 받지 않고 검증된 guest token 해시의 DB 조회 결과로만 설정한다. RLS는 조건 누락 방어다. runtime 자격증명 탈취나 임의 SQL 실행까지 테넌트를 분리하는 인증 수단은 아니다.

업무 트랜잭션은 guest 행을 FOR UPDATE로 잠근 뒤 DB 시각으로 만료를 다시 검사한다. GET도 대기 제안을 변경할 수 있어 같은 경계를 따른다. 요청 허용/횟수 예산은 업무 트랜잭션과 별도로 먼저 커밋하므로 잘못된 CSRF 등 실패 요청도 예산을 소비한다. 전체 생성 상한은 공유 gate 행 잠금으로 직렬화한다.

진행 요청은 90초 lease다. 함수가 종료되어 release를 못 해도 영구 카운터가 남지 않는다. SQL/락/유휴 트랜잭션 시간은 각각 5/3/10초로 제한한다. Python 전역 커넥션 풀과 prepared statement를 쓰지 않으며 `prepare_threshold=None`, 트랜잭션 한정 SET을 사용한다. 실제 Supavisor transaction pool 지원·TLS·사용자 형식·latency·연결 한도는 외부 검증이 남아 있다.

기본 체험 수명은 1시간이다. 만료 즉시 API 접근을 거절하고, **물리 삭제는 다음 새 guest 할당 시** 만료 lease를 정리한 뒤 실행한다. 트래픽이 없으면 만료 행이 더 오래 남을 수 있다. 정확한 삭제 시한·DB 백업의 보관까지 완료했다고 말하지 않는다. 엄격한 회수 주기가 필요하면 승인된 스케줄러를 별도 설계해야 한다. 실제 개인정보는 입력하지 않는 합성 데이터 체험이다. `persistent: false`는 장기 보관 제품이 아니라는 뜻이며, PostgreSQL 모드에서는 프로세스 재시작 후에도 남은 체험 시간 동안 상태를 이어간다.

## 로컬 재현

Docker와 Python 개발 의존성이 준비된 저장소 루트에서:

```bash
.venv/bin/python -m pip install -r requirements-app.txt -r requirements-dev.txt
.venv/bin/python scripts/local_postgres_preview.py
OURCOMMUNITY_TEST_POSTGRES=1 .venv/bin/python -m pytest -q
```

Docker 설정 디렉터리가 읽기 전용인 이 클라우드에서는 첫 스크립트에 `DOCKER_CONFIG=/tmp/ourcommunity-docker-config`를 지정했다. 스크립트는 loopback `127.0.0.1:55432`의 전용 테스트 컨테이너와 tmpfs DB만 만든다. 로컬 비밀번호는 추적 제외된 `.harness/postgres-local.json`에 mode 0600으로 저장한다. 기존 설정 파일이 있으면 덮어쓰지 않는다. 이 DB에는 다른 제품을 모사한 sentinel 한 행만 있으며 외부 데이터를 가져오지 않는다.

PostgreSQL 테스트는 명시적 `OURCOMMUNITY_TEST_POSTGRES=1`이 없으면 integration 항목을 skip한다. 활성화하면 위 로컬 테스트 DB의 ourcommunity 데이터만 초기화한다. 외부 DSN을 받아 migration을 자동 실행하는 테스트가 아니다. 외부 저장소의 읽기 전용 preflight 명령은 승인된 서버 환경에서 `.venv/bin/python -m scripts.check_preview_postgres`이며 URL/비밀번호를 출력하지 않는다.

## 승인 후 필요한 최소 외부 단계

1. **대상과 권한 확인:** 지정된 Supabase 프로젝트·별도 스키마 이름 충돌·현재 PUBLIC grant·DDL 실행자 권한·전용 role 연결 및 TLS 경로를 읽기 확인한다. 기존 제품 접근이 상속되면 연결을 진행하지 않는다.
2. **전용 영역과 연결정보:** 검토한 migration을 권한 있는 관리 경로로 한 번 적용하고 runtime만 LOGIN 가능하게 한다. 전용 role 비밀번호는 승인된 비밀정보 입력 경로에서 생성·전달하며 채팅/저장소/로그에 남기지 않는다. 소유자·postgres·service_role 연결정보는 Vercel에 저장하지 않는다.
3. **Vercel preview 설정·검증:** 기존 승인된 Hobby 팀에서 ourcommunity preview 대상에 서버 전용 `PREVIEW_MODE=1`, `PREVIEW_DATABASE_URL`을 저장한다. 정확한 `PUBLIC_ORIGIN`을 지정하거나 플랫폼의 `VERCEL_URL`로부터 해당 배포의 HTTPS origin 하나를 사용한다. 요청 Host/Forwarded 헤더로 허용 origin을 결정하지 않는다. `VERCEL=1`에서 공유 DSN이 없으면 로컬 SQLite로 대체하지 않고 시작을 거부한다. 실제 함수 번들·정적 자산·TLS·콜드스타트/다중 인스턴스·쿠키·핵심 흐름을 공개 URL에서 검증한 뒤 URL을 전달한다.

우리 기능 브랜치 코드 게시와 새 지속 연결 승인은 별개다. main 병합, 기존 public/Auth 설정 변경, 신규 과금, 새 외부 계정은 위 단계에 자동 포함되지 않는다. 철회할 때는 먼저 preview 라우팅과 runtime LOGIN/서버 비밀정보를 끄는 범위를 검토하며, 기존 데이터나 스키마를 자동 삭제하지 않는다.

## 검증 상태

| 검사 | 최종 결과 / 한계 |
|---|---|
| Python 전체 | **96 passed** = 기존 79 + PostgreSQL 관련 17(실제 로컬 DB 10, 설정 경계 7). 기존 Starlette/httpx deprecation 경고 1 |
| PostgreSQL | **17.11** Docker의 실제 제한 runtime 계정으로 검증. 새 DB 초기 migration·소유자 임시 membership 회수(잔여 0)·preflight Pass |
| 기존 브라우저 회귀 | **9 passed**, 실제 Chromium. 기존 SQLite 개발 흐름 유지 |
| 공유 체험 브라우저 | **2 passed**, 로컬 ASGI 진입점의 **2 worker** + PostgreSQL. 모바일/데스크톱·메시지/새로고침·신청·역할 전환·출석/성장·별도 방문자 격리 |
| 린트/타입/빌드 | ESLint·TypeScript·Vite·토큰 검사 Pass. 하네스 오류 0·기존 제3자 경고 2, UI strict audit 오류/경고 0 |
| 문서·설정 | 상대 링크·YAML/JSON·변경 공백 Pass. Vercel 공식 JSON schema의 직접 조회는 실패하여 호스트 설정 수용 여부는 미검증 |
| 독립 검토 | 코드/권한 검토 후 접두사 검사 수정, 외부 sequence·소유권 검사와 알림 event 복합 FK 보강. 정적 재검토에서 추가 HTTP 누출/정원 차단 결함 미발견 |

실제 DB 테스트는 앱 인스턴스 교체 후 같은 session 유지, 다른 방문자의 세션 혼용/직접 ID 거부, 생성 상한 경합, 동시 정원·중복 재시도·취소/대기 수락, 출석 중복/정정, 탈퇴 후 접근, RLS INSERT/UPDATE·복합 FK, commit/rollback 뒤 tenant 미설정 상태, 죽은 요청 lease 회수, 실패 요청 예산 유지, 다른 제품 sentinel 무변경을 다룬다. PUBLIC 함수/sequence 권한 탐지 테스트의 대상도 외부가 아닌 로컬 모조 스키마다.

로그인 응답을 기다리지 않고 다음 요청/페이지 이동을 하던 체험 테스트를 수정해, 인증 완료 화면을 확인한 뒤 진행하도록 했다. 로컬 초기화 스크립트도 빈 fixture에서 실제 실행해 검증했다. [모바일 증거](screenshots/postgres-mobile-memories.png), [데스크톱 증거](screenshots/postgres-desktop-space.png)는 합성 데이터와 로컬 Chromium 화면이다.

**남은 검증:** 실제 Supabase의 유효 권한·TLS/CA·Supavisor 풀러, Vercel의 `icn1` 배치·Python 빌드/함수 번들/rewrites/Host 보존, 공개 HTTPS·실기기 iPhone·부하/가용성. 이번 PostgreSQL 버전의 Docker 이미지 재빌드나 외부 배포는 하지 않았다. 공개 URL·배포 revision은 없다.
