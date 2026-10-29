# App Store and Google Play compliance standard

목표는 승인 보장이 아니라 반려 위험을 줄이고, 증거 없는 제출을 막는 것이다. 정책은 바뀌므로 모든 모바일 앱 개발과 제출에서 공식 원문을 실행 시점에 다시 확인한다.

## 세 개의 게이트

### Store-impact gate

로그인·회원가입·계정 삭제, 개인정보·분석·광고·AI SDK, 권한, 결제·구독, UGC, 아동·의료·금융 등 규제 영역, 스토어 제출/업데이트가 있으면 `store_compliance`를 호출한다. 기능별 데이터, SDK, 권한, 결제, 연령·콘텐츠, 계정 삭제와 iOS/Android 차이를 `store requirement matrix`로 만든다.

### Implementation consistency gate

다음이 서로 일치해야 한다.

```text
실제 코드 / SDK / 네트워크 동작
  = 개인정보처리방침
  = Apple App Privacy
  = Google Data safety
  = 권한 설명과 거부·철회 동작
  = 계정·데이터 삭제
  = 결제·구독·복원·취소
  = 스토어 설명과 스크린샷
```

### Pre-submission Hard Gate

제출할 정확한 IPA/AAB, build/version, signing, production backend, 실제 콘솔 상태를 기준으로 판단한다. 리뷰어 demo 계정/모드, MFA·OTP·지역·paywall 우회 설명, review notes, privacy/data safety, age/content rating, target audience/ads, 지원·삭제 URL, privacy manifest/required-reason API/SDK, merged permissions/target API, TestFlight·실기기·pre-launch report 증거를 확인한다.

판정은 `GO | CONDITIONAL GO | NO-GO`다. 콘솔 전용 항목이나 실제 artifact를 확인하지 못하면 GO가 아니다. 저장소 검사, artifact 검사, 콘솔 입력, 제출, 승인, 공개 상태를 서로 구분한다.

## 공통 반려 위험

- 계정 생성은 있지만 전체 계정과 관련 데이터 삭제 경로가 없음
- 개인정보처리방침·store declaration·실제 SDK/네트워크 동작 불일치
- 만료되거나 지역/MFA/paywall 때문에 사용할 수 없는 리뷰 계정
- 디지털 상품의 결제·복원·취소가 플랫폼 정책과 맞지 않음
- 필요 이상의 민감 권한, 불명확한 purpose/disclosure, 거부 시 기능 붕괴
- privacy manifest, required-reason API, SDK manifest/signature, target API 누락
- UGC 신고·차단·moderation, 연령/콘텐츠, 규제·권리 문서 누락
- 현재 빌드와 맞지 않는 설명·스크린샷, 불안정한 backend, 미완성 기능

## 현재 공식 기준

아래는 기준선이며 제출 날짜에 재조회한다.

- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Apple account deletion](https://developer.apple.com/help/app-review/guideline-reference/5-1-1-account-deletion/)
- [Apple user privacy and data use](https://developer.apple.com/app-store/user-privacy-and-data-use/)
- [Apple third-party SDK requirements](https://developer.apple.com/support/third-party-SDK-requirements/)
- [Apple submit an app](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app)
- [Google Play Developer Program Policy](https://support.google.com/googleplay/android-developer/answer/18258653?hl=en)
- [Google Data safety](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en)
- [Google account deletion](https://support.google.com/googleplay/android-developer/answer/13327111?hl=en)
- [Google prepare for review](https://support.google.com/googleplay/android-developer/answer/9859455?hl=en)
- [Google target API requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
