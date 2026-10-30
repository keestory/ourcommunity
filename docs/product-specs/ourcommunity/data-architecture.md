# 개념 데이터 모델과 기술 ADR 초안

상태: 미승인 설계 대안 · 2026-10-29 · 구현/스키마/서비스 계정 없음

현재 [저장소 아키텍처](../../../ARCHITECTURE.md)는 에이전트 하네스다. 아래 모델은 미래 소비자 서비스의 제안이며 기존 Python 오케스트레이터를 백엔드로 간주하거나 수정하지 않는다. 실제 타입·DB·인증·클라우드 공급자는 결정하지 않았다.

## 1. 개념 모델

| 엔터티 | 핵심 속성·관계 | 제약과 개인정보 |
|---|---|---|
| Account | id, auth_subject, display_name, state, deletion_requested_at | 인증 비밀은 별도 제공자에 위임; 표시명은 실명 필수 아님 |
| Group | id, sport_kind, owner_id, visibility, policy_version | running/crossfit은 분류 예시; 운영자 접근은 group 범위 |
| Membership | group_id, account_id, epoch, role, state, joined_at, history_from_seq | 동일 group/account 활성 가입 1개. 탈퇴 후 재가입은 새 epoch |
| Invite | group_id, token_hash, expires_at, max_uses, uses, revoked_at | 원문 토큰 로그 금지. 원자적으로 사용 횟수·대상·승인 정책 검증 |
| Conversation | id, group_id, kind, next_seq | MVP 기본 그룹 방. private DM 구조는 구현 범위 아님 |
| Message | id, conversation_id, author_membership, client_message_id, server_seq, body, revision, state | sender/epoch/client ID 유일성. 본문 분석 로그 금지; DB에서 순서 부여 |
| ReadCursor | account_id, conversation_id, epoch, last_read_seq | 사용자별 단조 증가; 알림 전송을 읽음으로 기록하지 않음 |
| Announcement | group_id, author_id, body, version, pinned_at, state | 공식 정보. 수정/철회 이력; 일반 메시지와 권한·알림 정책 분리 |
| EventOccurrence | group_id, starts_at_utc, ends_at_utc, timezone, location_visibility, capacity, deadline, version, state | 회차별 원장. UTC 저장·IANA timezone 보존, 표시 기본 가정 Asia/Seoul |
| MessageEventLink | message_id, occurrence_id, referenced_version | 대화 카드에서 원본 일정을 조회; 낡은 본문을 상태 원장으로 사용하지 않음 |
| Registration | occurrence_id, account_id, status, wait_seq, offer_expires_at, version | 회차/계정 1행. confirmed+offered ≤ capacity를 트랜잭션으로 보장 |
| Attendance | registration_id, status, marked_by, revision, reason_code | 1신청 1현재 상태; 수정 이력 별도, 개인 공개 기본 안 함 |
| NotificationPreference / Device | account_id, group_id, mute_until, channel_opt_in, private_device_token | 토큰 비공개·폐기 가능. 개인별/그룹별 설정과 OS 허용 상태 구분 |
| Outbox / Delivery | event_id, recipient_id, channel, dedup_key, state, attempts | DB 변경과 알림 의도를 동일 트랜잭션에 기록. provider ACK ≠ 사람에게 읽힘 |
| Block / Report / ModerationCase | actor_id, target_id, object_id, reason, status, retention_policy | 차단과 그룹 강퇴는 별개. 신고 증거는 일반 콘텐츠와 분리 접근 |
| AuditEvent | actor_id, group_or_case_scope, action, object_id, old/new state refs, timestamp | 권한/출석/운영 처분 변경 추적. 메시지 본문·토큰을 감사 로그에 복제하지 않음 |
| Attachment (조건부) | message_id, private_object_key, scan_state, derivatives, expires/deleted_at | 포함 시 원본/파생본/EXIF/백업 관리. 정책 미확정이면 업로드 금지 |

회원은 여러 그룹에 속할 수 있고 그룹에는 여러 일정과 메시지가 있다. 본인 활동 이력은 신청/출석에서 권한 검사를 거쳐 조회한다. 영구적인 공개 ‘출석 프로필’ 복제 테이블은 기본으로 만들지 않는다.

## 2. 실시간 메시지 계약

1. 서버가 인증과 `Membership.active`, 방 권한, 차단/제재, 길이·속도 제한을 확인한다. 클라이언트의 group ID·role 주장을 신뢰하지 않는다.
2. 메시지 영속화, 방별 sequence 부여, outbox를 원자적으로 커밋한다. `(author_membership, client_message_id)` 유일 키로 중복 탭/재시도를 1건으로 만든다. ACK 분실 후 재시도하면 기존 결과를 반환한다.
3. 전송 채널은 적어도 한 번 전달을 가정한다. 클라이언트는 message ID/revision으로 중복 제거하고 `server_seq`로 정렬한다. ‘네트워크 exactly-once’를 약속하지 않는다. sequence 공백은 허용하되 cursor API로 누락을 복구한다.
4. 재접속 시 마지막 동기화 cursor 이후 변경·수정·삭제 tombstone을 재조회한다. 오래된 cursor는 권한 있는 범위의 snapshot으로 복구한다. 읽음 cursor와 수신 cursor는 서로 다른 값이다.
5. 오프라인 작성은 로컬 미전송 큐. 재접속 후 권한·정책을 다시 확인하고 사용자가 아직 전송 의사를 유지하는지 확인할 수 있게 한다. 탈퇴/강퇴 뒤 보류 메시지를 전송하지 않는다.
6. 탈퇴·강퇴는 API뿐 아니라 연결/구독·재생 토큰·백필·첨부에도 적용한다. **매 수신 배치와 재조회에 현재 권한 검증**을 수행하고 철회 이벤트로 연결을 종료한다. 만료 토큰만 기다리는 설계는 수용하지 않는다.
7. 삭제·수정 revision을 인용/검색/푸시 준비 큐/캐시에 전파한다. 이미 OS에 표시된 알림이나 외부 캡처를 회수한다고 보장하지 않는다. 원문을 숨긴 알림 기본값으로 노출을 줄인다.
8. 한 사용자 여러 기기의 읽음은 `max(old, new)`로 병합하되 접근 가능한 seq 범위를 검증한다. 삭제/차단 메시지가 안읽음 숫자에 어떻게 반영되는지도 동일한 서버 정의를 사용한다. 개인별 ‘읽은 사람’ 공개는 별도 정책이다.

채팅 부하·동시접속·최대 그룹 크기는 미정이다. 부하 시험 예산/목표가 정해지기 전 무제한 그룹·지연 보장·운영비 수치를 약속하지 않는다.

## 3. 정원·대기·일정의 원장

관계형 DB를 상태 원장으로 추천하되 공급자는 미정이다. 한 회차의 신청/취소/자리 제안/수락/만료는 잠금 또는 동등한 직렬화 가능한 트랜잭션 안에서 처리한다. `confirmed + offered`가 정원을 넘지 않아야 한다. 앱 화면·캐시·채팅 카드·알림 발송 결과는 원장 변경 권한이 없다.

- 중복 신청: `(occurrence_id, account_id)` 유일 제약과 요청 idempotency. 취소 후 재신청은 정책에 따라 새 대기순번을 부여하고 과거 이력을 감사로 남긴다.
- 자리 제안: 대기순서와 현재 가입 상태를 재확인하고 하나의 유효 offer만 만든다. 제안 TTL/신청 마감/시작 시점 중 빠른 기한에서 만료. 수락과 만료가 경합하면 한 결과만 커밋한다.
- 일정 취소: 대기/offer를 종료하고 신규 신청·승격 차단. 일정 변경은 optimistic version 검사와 audit/outbox를 함께 기록한다.
- 정원 축소: 이미 confirmed+offered보다 낮추는 요청은 거절하거나 명시적 재배정 플로우로 전환한다. 조용히 참석자를 밀어내지 않는다.
- 강퇴/탈퇴: 미래 참가를 취소할지 운영자 검토할지 정책을 확정해야 한다. 제안 기본은 향후 신청·offer 취소 및 동일 트랜잭션/일관된 후속 작업으로 자리 회수; 과거 출석은 개인정보 정책에 따라 유지/익명화한다.
- 출석 수정: 감사 이력과 지표 재계산 버전을 기록한다. 수정이 새로운 참여 이벤트로 중복 집계되지 않도록 한다.

박스가 기존 예약 원장을 쓰면 커뮤니케이션 이동과 수업 예약 이전을 분리한다. 연동 합의·API 권한·동기화 책임이 없으면 같은 수업의 예약을 두 시스템에서 받지 않는다. MVP 박스 대화 실험에서는 기존 예약 링크만 표시하고 ourcommunity가 정원 확정을 주장하지 않는 대안도 비교한다.

## 4. ADR-001 — 플랫폼은 미정

상태: Proposed. ‘모바일 웹 우선’은 확정하지 않는다. 한국은 준비용 지역 가정이며 실제 대상 기기·OS 분포는 아직 없다.

| 대안 | 장점 가설 | 위험·검증 | 선택 조건 |
|---|---|---|---|
| 모바일 웹/PWA | 링크 진입과 배포 단순성 | 홈화면 설치·브라우저/OS별 푸시·인증 복귀·오프라인 저장의 실제 제약 | 초대→설치→알림→방 복귀 과업과 반복 사용이 허용 기준을 만족 |
| 크로스플랫폼 네이티브(예: React Native/Expo 또는 Flutter) | 앱 설치·알림·백그라운드 복귀를 일관되게 다룰 가능성 | 스토어 제출·업데이트·SDK·deep link·OS 권한·실기기 운영 부담 | 팀 역량과 비용이 맞고 대상 기기의 전환/복귀 경험이 더 좋음 |
| iOS/Android 별도 네이티브 | 플랫폼별 깊은 통합 | 두 구현의 유지비·기능 동등성, 출시 심사 | 플랫폼 특화 요구와 팀 자원이 차이를 정당화 |

공식 WebKit 자료의 관리 작업 검토에 따르면 iOS Web Push는 홈화면 웹앱과 사용자 제스처 권한 요청 조건이 있다. 이것은 우리 기기에서 성공했다는 증거가 아니며 네이티브도 권한/OS 제약이 있다. 공식 출처·전달 경로는 [근거 기록](evidence-decisions.md)을 따른다.

**추천 결정 방법:** 동일한 핵심 과업을 각 후보의 작은 검증 프로토타입에서 비교한다. `초대 링크 → 인증·그룹 가입 → 설치/홈화면 추가 → 맥락 있는 알림 동의 → 백그라운드 메시지 → 정확한 방 복귀`를 실제 대상 OS에서 시험한다. 설치 안 함·권한 거절·뮤트·앱 종료·네트워크 전환도 포함한다. 공동 공간의 저성능 기기·접근성·정적 대체 표현도 함께 본다. 이번에는 프로토타입을 구현하지 않는다.

## 5. ADR-002 — 백엔드·실시간 스택 대안

| 대안 | 적합성 가설 | 결정 전 확인할 항목 |
|---|---|---|
| TypeScript API + PostgreSQL + 관리형 realtime/queue | 웹/앱과 계약 타입 공유, 관계형 예약 제약 | 팀 숙련도, revocation·backfill·outbox 보장, 요금·리전·백업 |
| Python(Django/FastAPI 등) + PostgreSQL + websocket/worker | Python 경험과 서버 중심 권한/관리 도구 | 앱 계약·socket 운영·작업 큐·배포 역량; 하네스 코드 재사용이 당연한 것은 아님 |
| BaaS(예: Supabase) + 별도 서버 경계 | 인증·DB·실시간 관리 업무 축소 가능성 | RLS/서버 트랜잭션, private channel, 즉시 권한 철회, 비용·리전·삭제/백업 의미 |
| 관리형 채팅 서비스 + 예약 API/DB | 동기화·읽음·알림 개발 부담 축소 가능성 | 데이터 이전/삭제·모더레이션·잠금효과·요금, 그룹 권한과 두 원장의 불일치 |

추천은 **제품 권한·메시지 동기화·정원 트랜잭션을 먼저 계약으로 고정하고 공급자를 고르는 것**이다. TypeScript/관계형 DB는 비교 출발점일 뿐 승인된 스택이 아니다. Supabase/Vercel 등 특정 계정·프로젝트·유료 리소스를 생성하거나 변경하지 않았다. 버전·가격·약관·할당량은 선택 시 최신 공식 자료로 다시 확인한다.

Gate 5 전 요구: 허용 스택/리전/예산, 데이터 처리자, 인증 공급자, 알림 채널, 운영 담당, retention/deletion, 복구 목표, 부하 가정. 인증·메시지·예약을 클라이언트 SDK 호출만으로 신뢰하지 않는다. 종단간 암호화는 설계하지 않았으므로 제공한다고 주장하지 않는다. 전송/저장 암호화 역시 선택된 공급자와 실제 설정에서 검증해야 한다.

## 6. ADR-003 — 개인정보·첨부·철회

인증 쿠키/토큰과 초대 토큰을 분리하고 최소 권한·만료·회수·속도 제한을 정의한다. 메시지 본문, 개인 연락처, 정확한 위치, 첨부 URL을 분석 이벤트에 복제하지 않는다. 탈퇴/강퇴 후 캐시 제거와 그룹 간 조회/쓰기 차단을 검증한다.

이미지를 포함한다면 비공개 격리 업로드→형식/크기/파일 검사→EXIF 제거/변환→안전 판정 후 메시지 연결 순서를 추천한다. 다운로드마다 권한을 확인하는 비공개 전달 경로를 우선 검토한다. 영구 공개 URL이나 오래 살아있는 서명 URL이 강퇴 후 접근 차단을 무력화하면 수용하지 않는다. CDN·앱 캐시·썸네일·원본·신고 증거·백업의 삭제 경로와 외부 저장본 회수 불가를 명시한다.

탈퇴 후 대화 보관, 개인정보 삭제 기간, 신고 증거 보관/열람, 연령 정책은 미승인이다. 운영자는 이용자 내용을 임의로 대량 내보내거나 본인 신고를 지울 수 없어야 한다. 정당한 증거 보존과 삭제 요구의 충돌은 정책 및 대상 지역의 적절한 전문가 검토 후 결정한다.

## 7. ADR-004 — 공동 기여와 공개 활기 경계

[공동 성장 모델](shared-growth.md)의 ContributionCandidate/Review, GroupGrowthLedger, AssetDefinition/GroupAsset, SharedSpace/LayoutRevision과 [공개 집계 계약](activity-patterns.md)의 ActivitySnapshot을 추가 개념으로 둔다. 실제 테이블/SDK는 만들지 않는다.

기여 원천은 서버가 이미 확인한 행동이며 이벤트 키·규칙 버전으로 중복을 막는다. 출석 정정·삭제·동의 철회는 보정 이벤트와 공간 revision에 반영한다. 영구 공동 자산을 최근 메시지 수에 연결해 감소시키지 않는다. 운영자의 꾸미기 권한·구성원 합의·독립 기여 검토는 서로 다른 권한이다.

공개 ActivitySnapshot은 소스 메시지와 분리된 읽기 모델로, 최소 메타데이터를 승인된 고정 집계창·지연·인원 기준으로 처리한 coarse 단계만 가진다. 본문/감정 분석, 개인 last-seen, 정확한 인원/건수/시각, 임의 기간 필터를 제공하지 않는다. 내부 원시 집계는 제한된 worker/평가 권한으로만 접근하며 외부 API와 캐시에 노출하지 않는다.

공개 선택·회원 고지/필요한 동의·정책 버전, 최소 서로 다른 기여자 `k_public`, 창 `W`, 지연 `D`, 갱신주기 `R`, 개인별 상한과 삭제/탈퇴 영향이 확정되지 않으면 외부 집계를 켜지 않는다. 작은 집단/기준 미달/철회 후에는 fail-closed로 숨긴다. 차분 추론 위협을 검증하고 보관·재계산·캐시 삭제를 정의한다. 메타데이터 집계가 자동으로 익명성이 된다고 주장하지 않는다.

## 8. 기술 진입 조건과 복구 계획 초안

DB 마이그레이션·메시지 fanout·알림·정원 처리는 각각 실패 지점과 재처리 키를 갖춘다. outbox 재시도·dead-letter, DB 백업 복원, 권한 철회 지연, 중복/누락 메시지, stale cursor, 푸시 실패를 관측할 계획이 필요하다. 백업 시점 이후 메시지 손실 허용치(RPO)와 복구 시간(RTO)은 아직 미정이다.

후속 배포는 별도 승인과 Gate 7 검증 대상이다. 스키마 롤백으로 삭제 데이터가 살아나거나 정원이 재중복되지 않도록 복원/재생 시나리오를 작성해야 한다. 이번에는 코드·DB·외부 서비스·배포 설정을 만들지 않았다.
