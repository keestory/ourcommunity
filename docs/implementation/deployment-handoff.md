# 승인된 배포 실행 인계

> **보류됨 (2026-10-30):** 사용자의 “supabase 없이 일단 줘” 요청에 따라 아래 DB 연결 절차는 실행하지 않는다. 현재 배포는 [브라우저 단독 정적 체험](browser-demo.md)을 따른다.

승인 근거: 2026-10-30 01:00 UTC 사용자의 “ㅇㅇ”. 대상은 Supabase `vgabkqvxotfmofhaijwz`의 ourcommunity 전용 영역과 Vercel Hobby 팀 `team_jr2EoWExoCNDX3AFRs9fZxKh`의 체험 배포다. public/Auth/다른 앱 데이터 변경, service_role, 추가 결제, main 병합은 제외한다.

이 실행 환경에는 Supabase/Vercel connector가 없다. 관리 작업의 connector가 아래 순서를 실행하고, 비밀정보를 제외한 결과·배포 URL/revision을 이 작업에 전달한다. 스키마·환경변수·배포의 실제 실행 상태는 도구 결과를 받은 후에만 갱신한다.

## 1. 변경 전 읽기 검사

지정 Supabase 프로젝트의 SQL 읽기 도구로 [000_preview_preflight.sql](../../migrations/000_preview_preflight.sql)을 실행한다. 앱 데이터 행이나 비밀정보를 읽지 않는다.

- `executor`: PostgreSQL 버전·역할 생성 및 schema 생성 권한을 확인한다.
- `name_collision`: 나오면 기존 객체의 소유·상태부터 확인한다. DROP/덮어쓰기/중복 migration을 하지 않는다.
- `public_*`: 새 runtime도 상속할 수 있는 기존 PUBLIC 권한이다. 결과의 schema/객체/권한 종류를 먼저 검토한다. 기존 권한을 회수하거나 service_role로 우회하지 않는다.
- 문제가 없는 경우에만 2단계를 실행한다. 넓은 권한 변경이 필요한 결과이면 해당 항목과 이유만 전달한다.

## 2. 전용 migration과 권한 확인

이 브랜치의 [001_preview_postgres.sql](../../migrations/001_preview_postgres.sql) 원문을 승인된 관리 SQL 경로로 한 번 실행한다. 객체 이름이나 권한을 임의로 넓히지 않는다. runtime은 아직 **NOLOGIN**이며 비밀번호도 없다. migration은 기존 public/Auth를 참조하거나 수정하지 않는다.

그다음 [002_preview_privilege_check.sql](../../migrations/002_preview_privilege_check.sql)을 실행한다. 정상은 `role_configuration` 한 행이며 login/superuser/createdb/createrole/replication/bypassrls가 모두 false, connection_limit가 8이다. 다른 행이나 빈 결과는 검토 대상이다. 현재 객체 존재 여부와 migration 성공도 함께 확인한다.

## 3. 전용 연결정보의 안전한 저장

권한 검사가 통과한 뒤 승인된 비밀정보 처리 경로에서 runtime만 LOGIN 가능하게 하고 충분히 무작위인 전용 비밀번호를 설정한다. 비밀 값·전체 DSN·SQL 비밀번호 리터럴을 채팅/로그/커밋/PR로 출력하지 않는다. connector가 값을 비공개로 전달·저장하는 방식을 먼저 확인한다. 안전한 전달이 불가능하면 기능/필드 단위의 제약을 보고하며 넓은 키로 대체하지 않는다.

대시보드/공식 연결정보에서 **해당 프로젝트의 확인된 호스트**를 사용한다. 호스트를 추정하지 않는다. transaction pool을 쓰면 전용 사용자 형식은 공급자가 제공한 `ourcommunity_preview_runtime.<project-ref>` 형태인지 확인하고 실제 `current_user/session_user`가 전용 role인지 검증한다. 직접 연결도 네트워크에서 지원되고 동일한 최소 권한이면 가능하다. `sslmode=verify-full`, 확인된 CA(`sslrootcert=system` 등)를 사용하고 TLS 검사를 끄지 않는다.

관리자/postgres/service_role 연결정보는 Vercel에 저장하지 않는다. 필요 서버 환경변수는:

| 변수 | 값 / 범위 |
|---|---|
| `PREVIEW_MODE` | `1`, 해당 프로젝트 preview 환경 |
| `PREVIEW_DATABASE_URL` | 전용 runtime만의 연결정보, **encrypted server env**, preview 환경만. `VITE_` 접두사 금지 |
| `PUBLIC_ORIGIN` | 안정된 정확한 HTTPS 주소를 쓰는 경우에만 지정. 생략 시 플랫폼 `VERCEL_URL`에서 해당 배포 origin 하나를 구성 |

프로젝트 연결 범위를 keestory/ourcommunity로 한정한다. GitHub 계정 전체 접근 확대나 다른 프로젝트 환경변수 재사용을 하지 않는다. 기존 프로젝트가 있으면 먼저 확인해 중복 생성하지 않는다.

## 4. Vercel preview 실행

검증된 기능 브랜치 `feat/sports-community-prototype`의 정확한 SHA로 **preview**를 만든다. PR은 기존 [#1](https://github.com/keestory/ourcommunity/pull/1)을 갱신한다. [vercel.json](../../vercel.json)은 Python 3.12/FastAPI·서울 `icn1`·30초 함수·web/dist 포함 설정이다. FastAPI 기본 라우팅이 원래 요청 경로를 유지하므로 별도 catch-all rewrite를 추가하지 않는다. 공식 Python 빌더의 로컬 패키징은 통과했으며 실제 호스트 적용은 별도 확인한다. GitHub 원격 main을 병합하거나 production target으로 배포하지 않는다.

실제 호스트가 설정을 거부하거나 정적 자산을 누락하면 빌드/런타임 로그에서 비밀 값 없이 원인을 전달한다. 설정 변경·브랜치 수정으로 해결하고 새 SHA를 검증한다. 이 설정 파일 존재만으로 Vercel에서 빌드됐다고 말하지 않는다.

## 5. 공개 검증

전달할 정보는 `deployment URL / deployment ID / git SHA / build 상태 / 권한 점검 결과`이며 비밀 값은 제외한다. 이 작업에서 그 URL에 다음 검증을 수행한다.

- `/api/health`가 PostgreSQL 체험이며 noindex/no-store·origin 경계가 유지됨.
- 모바일/데스크톱 렌더링, 로그인 대신 가상 역할 표시, API 도달과 오류 처리.
- 채팅→새로고침→모임 신청→운영자 출석→공동 성장, 다른 브라우저 데이터 분리.
- 콜드스타트/여러 함수 인스턴스에서도 세션 유지. 실제 iPhone은 별도 실기기 검증으로 구분.

현재 브라우저 시험은 해당 URL이 체험 모드임을 먼저 확인한 뒤 합성 데이터만 작성한다. 실행 예시는 web 디렉터리에서 `PREVIEW_TEST_EXTERNAL=1 PREVIEW_TEST_ORIGIN=https://<확인된-배포-host> npx playwright test --config playwright.preview.config.ts`다.

진행 기록: 외부 권한/스키마/자격증명/배포는 아직 실행 확인을 받지 않았다. 사용자 승인과 실제 변경 완료를 구분한다.
