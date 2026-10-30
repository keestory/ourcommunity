# ourcommunity

비공개 그룹 대화와 운동 참여가 함께 키우는 공간으로 이어지는 스포츠 커뮤니티의 **로컬 초기 제품**입니다. 한국어 러닝 크루와 2D 클럽하우스를 첫 구현 가정으로 사용합니다. 실제 고객 검증·외부 인증·푸시·배포를 완료한 서비스는 아닙니다.

기존 `kee_agent` 하네스는 유지합니다. 하네스 안내는 [AGENTS.md](AGENTS.md)와 [Codex 가이드](docs/CODEX_HARNESS.md), 제품 준비 자료는 [준비 패키지](docs/product-specs/ourcommunity/README.md), 구현 범위는 [로컬 제품 기록](docs/implementation/local-product.md)을 참고하세요.

## 로컬 실행

Python 3.12와 Node 24에서 검증합니다. 저장소 루트에서 의존성을 설치합니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements-app.txt
npm --prefix web ci
```

첫 번째 터미널에서 API를 실행합니다.

```bash
DEMO_MODE=1 .venv/bin/uvicorn community.app:app --host 127.0.0.1 --port 8000
```

두 번째 터미널에서 화면을 실행하고 Vite가 출력하는 로컬 주소를 브라우저에서 엽니다.

```bash
npm --prefix web run dev -- --host 127.0.0.1
```

화면의 체험 로그인으로 가상 운영자·회원 역할을 바꿔 테스트합니다. 실제 개인정보를 입력하지 마세요. 직접 만든 로컬 계정도 세션과 비밀번호로 반복 로그인할 수 있습니다. 새 계정은 운영자가 발급한 초대 링크로 그룹에 가입합니다. 서버가 꺼져 있으면 화면에 연결 오류가 표시됩니다.

채팅·신청·출석은 `.harness/community.sqlite3`에 저장되어 재시작 후에도 남습니다. 샘플은 처음 한 번만 생성하므로 기존 시험 데이터가 재시작으로 덮어써지지 않습니다. 새 시연이 필요하면 기존 DB를 삭제하는 대신 `COMMUNITY_DB=/tmp/ourcommunity-new-demo.sqlite3`처럼 새로운 파일을 지정해 API를 실행하세요. `DEMO_MODE=1`을 생략하면 체험 로그인과 샘플 생성을 끕니다. 이 모드 변경만으로 실제 서비스 보안·운영 준비가 완료되지는 않습니다.

## 첫 사용 흐름

1. 가상 회원으로 들어가 그룹 공간, 공지와 비공개 대화를 확인하고 메시지를 보냅니다.
2. 모임에 참가 신청하거나 취소합니다. 정원이 차면 대기하고 자리가 생겼을 때 명시적으로 수락합니다.
3. 가상 운영자로 전환해 모임을 만들고, 지난 모임의 다른 회원 출석을 확인합니다.
4. 확인된 참여가 공동 기념물에 반영되는 것을 봅니다. 채팅 수는 기여 점수가 되지 않습니다.
5. 설정에서 공개 공간과 개인 집계 참여 동의를 각각 확인합니다. 기본은 비공개이며 작은 그룹의 활기는 표시하지 않습니다.

## 검증

```bash
.venv/bin/python -m pytest -q
.venv/bin/python run.py --lint
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix web run test:e2e
```

브라우저 테스트에는 `/usr/bin/chromium`이 필요합니다. 이 클라우드 환경의 시스템 Chromium을 사용하며, 실제 iOS/Android 기기 시험이나 OS 푸시 검증을 대신하지 않습니다. 실행 중인 데모 서버가 있으면 재사용해 시험용 메시지·모임을 만듭니다. 서버가 없으면 테스트 전용 `.harness/browser-tests.sqlite3`를 사용해 실행합니다. 최초 구현 결과는 [검증 기록](docs/implementation/verification.md), 후속 체험 모드 검증은 [배포 준비 기록](docs/implementation/preview-deployment.md)에 있습니다. 코드는 [초안 PR #1](https://github.com/keestory/ourcommunity/pull/1)에서 검토합니다. main 병합과 공개 배포는 하지 않았습니다.

## 방문자별 체험 컨테이너

[Docker 실행 방법과 호스팅 조건](docs/implementation/preview-deployment.md)에 따라 API와 화면을 함께 실행할 수 있습니다. `PREVIEW_MODE=1`은 방문자마다 합성 데이터 공간을 만들고 실제 가입·외부 초대·공개 공유를 제한합니다. 역할 전환은 실제 인증이 아니며 첫 방문 1시간 뒤 또는 서버 재시작 시 초기화됩니다. 위 로컬 개발 DB와 별개입니다.

현재 컨테이너 검증은 통과했지만 공개 체험 URL은 없습니다. 단일 인스턴스 장기 실행 호스트가 필요하며, 현재 메모리 세션·임시 SQLite 구조를 Vercel 함수에 그대로 배포하면 재시작·다중 인스턴스에서 체험이 끊깁니다.

빌드한 화면으로 별도 체험 테스트를 실행할 수 있습니다.

```bash
npm --prefix web run build
cd web
npx playwright test --config playwright.preview.config.ts
```

이미 실행 중인 검증용 체험 컨테이너에는 `PREVIEW_TEST_EXTERNAL=1 PREVIEW_TEST_ORIGIN=http://127.0.0.1:8088`을 지정합니다. 이 테스트는 해당 체험 공간에 가상 메시지·신청·출석을 기록합니다.
