# Competitive product and design research

신규 제품, 큰 사용자 여정, 카테고리 재포지셔닝, 중요한 디자인 방향을 승인하기 전에 현재 상위 제품과 직접·인접 비교군을 조사한다. `market_researcher`가 시장·차트·표본을 정하고 `competitive_pattern_researcher`가 제품·UX·디자인 패턴을 깊게 분석한다.

## Evidence pack

모든 관찰은 국가, 플랫폼, 차트/카테고리와 순위 정의, `observed_at`, 원본 URL, 가능한 경우 앱 버전/업데이트일, observed fact/review signal/inference 구분, freshness와 재현 한계를 포함한다. 차트는 7일, listing·가격·기능은 30일이 지나면 재조회하고 정책은 제출 세션에서 다시 확인한다.

직접 경쟁과 인접 우수 제품을 함께 보며 한 회사·한 비즈니스 모델에 치우치지 않는다. 제품 job/value proposition, first-run과 activation, 정보 구조, 주요 상태, 개인화와 다음 행동, 신뢰·프라이버시·안전, 수익화 시점, 알림·협업·콘텐츠·habit loop, 시각 계층·타이포·색상 역할·컴포넌트·접근성, 균형 잡힌 리뷰 표본을 비교한다.

세 개 이상의 독립 제품에서 반복될 때만 공통 패턴으로 부른다. 각 권고는 `Adopt principle | Adapt to product | Avoid | Test first`로 분류하고 근거, 우리 제품에 적용할 이유, 의도적인 차별점 하나 이상을 포함한다. 순위만으로 유지율·매출·품질을 추론하지 않으며 브랜드 자산, 고유 문구·일러스트, 정확한 화면 배치나 interaction sequence를 복제하지 않는다.

권장 경로:

```text
docs/research/evidence-packs/YYYY-MM-DD-market-category-slug/
  manifest.yaml
  rankings.md
  product-pattern-matrix.md
  design-pattern-matrix.md
  review-signals.md
  recommendations.md
```

## 2026-10-10 KR iPhone Business snapshot

Apple 대한민국 무료 비즈니스 차트에서 관찰한 상위 15개는 고용24, 알바몬, 사람인, 엔카, 마이클, Zoom Workplace, 잡코리아, 쿠펀치, 알바천국, 스마트 위택스, 토스 비즈니스, 모바일팩스 i, 하우머치, 나이스 아이핀, 리멤버였다. 이 목록은 시점 스냅샷이며 다시 조사하지 않고 현재 순위처럼 재사용하면 안 된다.

이 순위만으로 activation, navigation, retention, 신뢰 또는 디자인 패턴을 결론 내리지 않는다. 그런 결론은 제품별 실제 화면·플로우·리뷰 표본을 기록한 evidence pack에서 세 개 이상의 독립 제품을 교차 확인한 뒤에만 채택한다.

- [Apple 대한민국 iPhone 비즈니스 무료 차트](https://apps.apple.com/kr/iphone/charts/6000?chart=top-free)
