# 클럽룸 리디자인 — 구현·검증 기록

사용자가 거부한 기존 민트/집 일러스트 중심 화면을, **크루 대화 → 다음 모임 참여 → 함께 만든 공간**으로 다시 구성했다. 색 변경만으로 끝내지 않고 진입·탐색·입력창·신청·공동 기념물 조작을 바꿨다. 새 미학은 trial이며 사용자 선택/수요 검증 완료를 뜻하지 않는다.

## 무엇을 어떤 근거로 바꿨나

[근거 복구](references.md)와 [패턴 메모리](patterns.md)에 사용자 발언, provisional taste, 부모가 확인한 공식 기능 자료, 이번 직접 접근403, 실제 로컬 관찰을 구분했다. Design Intelligence의 강한 계층·의도적 밀도, Frontend Design/Premium의 제품 맥락·공통 UI·복구 계약을 적용했다. Mobbin/Page Flows 등 목록을 특정 화면 선호로 추정하지 않았고 다른 프로젝트의 Apple 스타일도 가져오지 않았다.

| 화면 | 바뀐 경험 | 근거/반영 요소 |
|---|---|---|
| 진입 | 멤버 시작을 우선, 운영자 체험은 보조. 역할 선택·브라우저 저장 한계를 짧게 표시 | 약한 동등 CTA와 반복 집 그림 audit, 사용자 anti-AI 피드백 |
| 우리 공간 | 실제 최근 대화와 공지, 다음 모임의 즉시 참가/신청 상태, 공동 공간으로 연결 | 지속 대화 목표, Heylo 그룹 내 대화/이벤트 공식 기능 설명. 화면 복제 아님 |
| 대화 | 메시지 영역만 스크롤, 입력/전송이 화면 안에 유지. 모바일 공지는 별도 dialog | 화면 밖 입력창 P0 재현, 공통 확인·오류·초안 보존 계약 |
| 모임 | 모바일 장식 cover 제거, 날짜/장소/정원과 참가 동작을 앞쪽에 배치 | 첫 화면 CTA와 터치 접근 audit |
| 함께한 기록 | 기념물 선택→획득 조건 확인→운영자 배치→저장 피드백 | 사용자 공동 성장 비전, 공간 정체성·공동 해금 패턴. 유료재화/메시지 보상 없음 |

상단 설정·알림·계정, 네 개 주 탐색, 공통 Button/Dialog/Toast는 재사용한다. 배치 변경은 **브라우저 데모에서만** 동작하며 서버 모드에는 조회·출석 성장이 유지된다. 기존 Python/SQLite/PostgreSQL·준비 문서·하네스를 삭제하지 않았다.

## 전후 화면과 측정

| 화면 | 이전 로컬 렌더 (`2c79fea`) | 변경 후 로컬 렌더 |
|---|---|---|
| 모바일 진입 | [before](before/mobile-entry.png) | [after](after/mobile-entry.png) |
| 모바일 공간 | [before](before/mobile-space.png) | [after](after/mobile-space.png) |
| 모바일 대화 | [before](before/mobile-chat.png) | [after](after/mobile-chat.png) |
| 데스크톱 공간 | [before](before/desktop-space.png) | [after](after/desktop-space.png) |
| 데스크톱 대화 | [before](before/desktop-chat.png) | [after](after/desktop-chat.png) |
| 공동 배치 | 이전 직접 배치 없음 | [출석으로 얻은 벤치를 정원으로 이동](after/mobile-arranged.png) |

1180×757 입력창 시작은 **y844.77 → y652**, 높이52로 화면 안에 들어왔다. 390×844에서는 **y805.02 → y705**, 끝757로 하단 탐색 시작778보다 위다. 320×780 입력창 끝693, 탐색 시작714; 390×500 짧은 화면 입력창 끝413, 탐색 시작434. [측정 원본](after/metrics.json). 홈 참가 버튼은 모바일 y669.22~713.22, 데스크톱 y423.13~467.13에 위치한다. iPhone 소프트 키보드를 실제로 열어 측정한 결과가 아니다.

## 검증 상태

2026-10-30 최종 코드에서 **데모 13/13, 서버 연결 10/10 통과**. [기계 판독 검증 기록](verification.json), [strict audit](premium-audit.json). 기존 8개 데모/9개 서버 동작을 보존하고 새 배치·뷰포트·실패 회귀를 추가했다. ESLint/TypeScript/토큰/두 build/strict audit Pass.

- 정적 데모: 기존 8개 + 리디자인 5개. 저장/새로고침/탭 재열기, API 요청0, 독립 브라우저, 저장 차단/실패/손상, 초기화 취소/Escape/확인, 모임·정원·대기·출석, 공지·권한·동시 탭, 입력·전송 위치, 키보드 포커스/스크롤, 기존 v1 데이터, 배치 저장/권한/잠금/충돌/잘못된 요청.
- 서버 모드: 기존 9개 + 홈 성장 갱신 실패/재시도 1개. 기존 권한/초대/탈퇴/차단/초안/중복 요청·모임/출석·개인정보 공개 선택을 회귀 확인한다.
- ESLint, TypeScript, 생성 토큰 일치, 정적 demo build, 정상 웹 build, strict Premium audit. 하네스 lint는 기존 경고3(테스트 길이1/제3자 코드2)이며 신규 오류 없음.
- 실제 Chromium 렌더와 axe, 가로 넘침·44px 주요 조작·키보드 포커스 확인. 독립 리뷰 지적 두 건(짧은 화면 저장 경고, 홈 성장 갱신 오류)을 수정하고 재검토했다. 남은 차단 사항 없음.

Python 서버는 변경하지 않아 기존97개 통과를 이번 재실행 결과로 적지 않는다. 실제 다중 사용자, 외부 로그인, 폰 푸시, 오프라인 첫 로딩/PWA, iPhone Safari 실기기는 미연결 또는 미검증이다.

## 실행·배포 인계

로컬: `npm --prefix web ci`, `npm --prefix web run build:demo`, `npm --prefix web run preview:demo` → `http://127.0.0.1:4174`.

기존 Vercel **ourcommunity-demo** (`prj_0aK3ZL9IqOuz62EdvNgvXDQr2zDA`)에서 rootDirectory=`web`, framework=`vite`, installCommand=`npm ci`, buildCommand=`npm run build:demo`, outputDirectory=`dist-demo`. 비밀정보·환경변수 불필요. 기존 root `vercel.json`의 Python 배포 설정과 구분한다. 사용자 승인 범위의 기능 브랜치 push/PR1 갱신 후 부모가 정확한 SHA로 배포한다. main 병합·Supabase 변경·결제·권한 확대 없음.

현재 공개 주소 `https://ourcommunity-demo.vercel.app`는 기준 SHA `2c79feace2fedae0b9ea86082ada87b205e0eee8`의 별도 프로젝트 production 체험이다. 이 문서 작성만으로 새 리디자인이 공개됐다는 뜻은 아니다. 기존 READY/alias는 부모 connector 확인, 기존 공개 화면 audit는 부모 executor 확인이다. 이 실행 환경의 공개 접속은 프록시403/DNS/tunnel 제한으로 실패했으므로 로컬 결과와 구분한다. 배포 후 SHA와 URL을 확인하고 접근 가능한 브라우저에서 공개 QA를 이어간다.
