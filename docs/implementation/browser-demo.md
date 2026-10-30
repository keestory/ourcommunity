# Supabase 없이 여는 브라우저 체험

2026-10-30 사용자 요청 “supabase 없이 일단 줘”에 따라 추가한 정적 체험 모드다. 기존 Python/SQLite/PostgreSQL 구현과 준비 문서는 보존한다. Supabase 조직·프로젝트·권한·연결정보 작업은 보류하며 이번 배포는 해당 서비스에 접근하지 않는다.

## 직접 해볼 흐름

1. 가상 멤버로 들어가 대화를 남기고 새로고침해 확인한다.
2. 모임에서 참가 신청·취소를 해본다. 정원이 찬 별도 시연 모임에서는 대기 신청을 해볼 수 있다.
3. 계정 버튼에서 역할을 바꿔 운영자로 들어간다. 지난 모임의 지호 출석을 확인하면 공동 벤치가 생긴다. 출석을 정정하면 공동 기록도 되돌아간다.
4. 공지·모임 생성, 풍경 색감, 신고함·차단도 같은 브라우저 안에서 체험한다.
5. 상단 **체험 초기화**에서 취소하거나, 명시적으로 확인해 샘플로 돌아간다.

가상 인물과 시연 대화다. 로그인, 실제 회원 간 채팅, 다른 기기와 동기화, 외부 초대·공개 공유, 신고 전달, 푸시 알림은 연결되지 않았다. 역할별 제어는 체험 로직이며 서버 인증/보안 경계가 아니다. 실제 개인정보를 입력하지 않는다. 대화 원문 분석이나 메시지 수 보상은 없고, 최근 활기는 실제 집계처럼 꾸미지 않고 숨긴다. 영구 기념물은 이 브라우저의 시연 출석으로만 변한다.

## 저장과 복구

`web/src/demo/storage.ts`가 이 origin 전용 IndexedDB `ourcommunity-browser-demo-v1`에 합성 상태를 저장한다. read/write 트랜잭션으로 여러 탭의 변경을 직렬화하고, commit 이후에만 성공을 표시한다. 새로고침/탭 재열기에도 이어지지만 브라우저 데이터 정리·비공개 모드 종료·저장소 회수·사용자 초기화 시 사라질 수 있다. URL(origin)이 바뀌면 별도 저장소이며 자동 이전하지 않는다.

저장소 자체를 열 수 없으면 **현재 화면에서만 유지되는 임시 체험**으로 전환하고 상시 경고를 표시한다. 저장 실패는 성공으로 처리하지 않으며 입력을 유지한다. 잘못된 버전의 기록은 덮어쓰지 않고 복구 안내와 초기화 경로를 제공한다. 메시지 500개·모임 60개·상태 약 1백만 문자 제한을 두며 과거 기록을 몰래 삭제하지 않는다. 초기화는 이 앱의 상태 한 건만 샘플로 바꾼다.

## 배포 설정 — 관리 작업에서 실행

| 항목 | 값 |
|---|---|
| 팀 | `team_jr2EoWExoCNDX3AFRs9fZxKh` (기존 Hobby) |
| 저장소 / 브랜치 | `keestory/ourcommunity` / `feat/sports-community-prototype` |
| 배포 종류 | static **preview**, main 병합 없음 |
| rootDirectory | `web` |
| framework | `vite` |
| installCommand | `npm ci` |
| buildCommand | `npm run build:demo` |
| outputDirectory | `dist-demo` (web 기준) |
| Node | 24.x 권장, 로컬 검증 버전 |
| 환경변수 / 비밀정보 | **불필요**. Supabase/Python용 변수를 넣지 않는다. |
| 설정 파일 | `web/vercel.json` |

기존 root `vercel.json`은 Python 서버 배포 설정이다. **rootDirectory=web**으로 분리해야 한다. Node/Vite 빌드만 실행하며 Python이나 DB를 시작하지 않는다. 기존 ourcommunity 프로젝트가 있으면 먼저 상태를 읽고 정적 체험 프로젝트와 혼동하지 않게 설정한다. 비용/권한 확대는 하지 않는다. 배포 SHA는 최종 인계의 정확한 커밋을 사용한다.

라우트 새로고침은 `index.html`로 연결한다. `noindex/nofollow`, `nosniff`, `no-referrer` 및 CSP `connect-src 'none'`로 API·분석·외부 연결을 차단한다. 자체 호스팅 폰트/스크립트만 사용하며 외부 CDN은 없다. Vercel preview 보호 설정 때문에 iPhone에서 접근할 수 없는 주소라면 공개 접근 가능 여부를 따로 확인해야 한다.

`/demo-build.json`은 `mode=browser-only-demo`, `api=false`, 플랫폼이 제공한 `VERCEL_GIT_COMMIT_SHA`를 기록한다. 비밀정보는 포함하지 않는다. 공개 URL의 이 파일과 실제 Vercel deployment git SHA를 비교한다. 빌드 환경에 SHA가 없으면 `local-build`로 표시하므로 플랫폼의 deployment SHA로 확인해야 한다.

## 검증

2026-10-30 로컬 결과: 브라우저 체험 **8 passed**, 기존 서버 모드 브라우저 **9 passed**, ESLint/TypeScript/토큰/정적·서버용 웹 build Pass, strict UI audit 오류·경고 0. 하네스 린터 오류 0·기존 경고 3. Python 서버 코드는 이번에 변경하지 않아 이전 97개 결과를 재실행 결과로 주장하지 않는다. 독립 검토의 탈퇴자 신규 출석/집계 미연동 안내 두 지적을 수정하고 정적 재검토 완료.

실제 화면: [모바일 기록](screenshots/browser-demo-mobile.png), [데스크톱 공간](screenshots/browser-demo-desktop.png). [UI audit](browser-demo-audit.json).

- `npm --prefix web run lint`, `typecheck`, `tokens:check`, `build:demo`; 기존 `build`.
- `cd web && npx playwright test --config playwright.demo.config.ts`: 정적 배포 결과에 실제 Chromium으로 접근. API 호출 0, CSP 적용, 모바일/데스크톱, 접근성, 대화/재열기/독립 브라우저, 신청/취소/대기승격, 출석/벤치, 공지/모임, 저장 실패/차단/손상 복구, 초기화 취소/Escape/확인, 두 탭 동시 저장.
- `npm --prefix web run test:e2e`: 기존 Python 연결 모드의 브라우저 회귀.
- strict premium UI audit 및 상대 링크/설정/공백 검사.

공개 배포 후 `DEMO_TEST_ORIGIN=https://<확인된-host> npx playwright test --config playwright.demo.config.ts`로 같은 검증을 이어간다. 테스트는 이 origin의 브라우저 저장소 안에만 합성 데이터를 쓴다. 데스크톱 Chromium의 모바일 viewport는 실제 iPhone Safari 검증이 아니다. 네트워크가 끊긴 상태의 첫 로딩/새로고침을 보장하는 service worker/PWA는 구현하지 않는다.

현재 공개 URL과 배포 revision은 **미확인**이다. 로컬 통과를 공개 배포 성공으로 기록하지 않는다.
