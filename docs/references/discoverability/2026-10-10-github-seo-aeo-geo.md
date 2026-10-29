# GitHub SEO/AEO/GEO evidence — 2026-10-10

## Snapshot

- `observed_at`: 2026-10-10T00:48:46+09:00
- Research question: 2026년 현재 GitHub에서 별 수가 많은 SEO·AEO·GEO 문서/에이전트 환경에서 kee_agent에 적용할 검증 가능한 패턴은 무엇인가?
- Cohort: 아래 source에서 발견한 결과 중 SEO·AEO·GEO의 문서, agent skill, 구현 도구 또는 직접 표준인 저장소만 포함했다. 일반 ML·데이터 저장소와 단순 keyword 일치 결과는 제외했다. 표는 이 cohort의 관측 별 수 내림차순이며 GitHub 전체의 절대 순위가 아니다.
- Search/API sources:
  - [Repository search: `SEO in:name,description stars:>100`, stars descending](https://api.github.com/search/repositories?q=SEO%20in%3Aname%2Cdescription%20stars%3A%3E100&sort=stars&order=desc)
  - GitHub topic pages sorted by most stars: [SEO](https://github.com/topics/seo?o=desc&s=stars), [AEO](https://github.com/topics/answer-engine-optimization?o=desc&s=stars), [GEO](https://github.com/topics/generative-engine-optimization?o=desc&s=stars), [`llms.txt`](https://github.com/topics/llms-txt?o=desc&s=stars), [structured data](https://github.com/topics/structured-data?o=desc&s=stars)
  - Exact counts, created/pushed timestamps and SPDX license: each repository's `https://api.github.com/repos/{owner}/{repo}` endpoint at `observed_at`
- Metric: GitHub REST repository endpoint의 **관측 시점 누적 stars**. “2026년 중 증가량”이 아니다.
- Limitation: topic은 저장소 소유자가 붙인 분류라 누락과 오염이 있고 서로 다른 query 결과를 하나의 절대 순위로 볼 수 없다. 다만 2026년에 생성된 저장소의 현재 별은 모두 생성 이후 획득된 값이다.
- Refresh trigger: 2026-11-09 이후, 중요한 upstream 변경, 또는 이 자료를 제품 결정에 다시 사용할 때

## Ranked discovery snapshot

| Repository | Observed stars | Created / pushed | Scope and use here |
|---|---:|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 53,902 | 2026-01-15 / 2026-10-08 | 가장 큰 관련 종합 마케팅 skill 모음. SEO/AEO/GEO 전용 순위로 해석하지 않음 |
| [every-app/open-seo](https://github.com/every-app/open-seo) | 22,856 | 2026-02-27 / 2026-10-08 | 문서 기준보다 구현 도구 참고용 |
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | 18,600 | 2026-02-07 / 2026-10-04 | 조사 cohort에서 가장 큰 전용 SEO agent/skill 환경 |
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | 10,976 | 2026-02-18 / 2026-10-09 | 조사 cohort에서 가장 큰 GEO 중심 agent 환경 |
| [schemaorg/schemaorg](https://github.com/schemaorg/schemaorg) | 6,270 | 2014-01-30 / 2026-10-01 | structured-data 어휘의 표준 근거. 인기는 플랫폼 eligibility와 별개 |
| [AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt) | 2,654 | 2024-09-01 / 2026-09-24 | `llms.txt` 제안의 원 저장소. 공식 검색엔진 요구사항은 아님 |
| [onvoyage-ai/gtm-engineer-skills](https://github.com/onvoyage-ai/gtm-engineer-skills) | 1,321 | 2026-02-26 / 2026-06-07 | AEO 감사 workflow 참고. 고정 점수와 수치는 채택하지 않음 |
| [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | 1,023 | 2026-02-18 / 2026-09-30 | AEO topic 관측 1위. 절대 전체 순위라는 뜻은 아님 |
| [GEO-optim/GEO](https://github.com/GEO-optim/GEO) | 339 | 2023-10-29 / 2025-10-30 | GEO-Bench 연구 재현 자료. 실험 결과를 일반 보장으로 확대하지 않음 |

## Inspected immutable evidence

| Repository evidence | License / maintenance signal | Pattern | Official cross-check | Classification | Decision |
|---|---|---|---|---|---|
| [marketingskills AI SEO skill @ `1efedbc`](https://github.com/coreyhaines31/marketingskills/blob/1efedbc5148b54b2f0f6c6c9fe0be62e151c7fff/skills/ai-seo/SKILL.md) | MIT; pushed 2 days before observation; no formal security audit | shared context, specialist routing, query cohort and repeated observation | Google requires no special AI file/markup; crawler purposes and platform metrics differ | mixed: officially-supported + experimental | **Adapt** workflow; reject fixed answer length and unsupported citation uplift |
| [claude-seo hub @ `4b99de2`](https://github.com/AgriciDaniel/claude-seo/blob/4b99de2f7de7e7d5247042e5fb5b4ea9368ef734/skills/seo/SKILL.md) and [GEO agent](https://github.com/AgriciDaniel/claude-seo/blob/4b99de2f7de7e7d5247042e5fb5b4ea9368ef734/agents/seo-geo.md) | MIT; active; no formal security audit | progressive routing, official-source refresh, deterministic tooling and stop conditions | aligns when actual rendered results and primary sources decide the outcome | implementation pattern | **Adopt** routing and evidence discipline; do not import its heuristic scores |
| [geo-seo-claude scoring @ `989cae0`](https://github.com/zubair-trabzada/geo-seo-claude/blob/989cae01e8ebbc42a9ec798eb9e7cb423f5ec89c/docs/scoring-methodology.md) | MIT; active; no formal security audit | separates crawl, rendering, schema, content and GEO observations | official docs support foundations, not arbitrary weights or guarantees | implementation pattern + experimental scoring | **Adapt** separated gates; **Avoid** universal score claims and unreviewed installers |
| [gtm-engineer AEO audit @ `3777930`](https://github.com/onvoyage-ai/gtm-engineer-skills/blob/3777930184a10b25ab36bb2fc4da6c0f6cfcc187/audit-website-aeo/SKILL.md) | MIT; less fresh; no formal security audit | deterministic audit before interpretive judgment; diagnose then fix/retest | sound workflow, but `llms.txt` points and exact multipliers lack official support | implementation pattern + unsupported claims | **Adopt** sequencing; **Avoid** llms.txt release points and claimed multipliers |
| [open-seo @ `89e5a00`](https://github.com/every-app/open-seo/tree/89e5a00717cdf049b7c2b4e29646edb3a7d4995b) | MIT; active; no formal security audit | auditable implementation surface rather than policy document | product behavior must be verified independently | implementation pattern | **Test** only when a project needs comparable tooling |

## Official cross-check and local decision

- [Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide): 기존 SEO 기반, people-first content와 기술적 접근성이 우선이다. **Adopt**.
- [Google structured-data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies): markup은 보이는 내용과 일치해야 하고 eligibility가 노출을 보장하지 않는다. **Adopt**.
- [OpenAI bots](https://developers.openai.com/api/docs/bots): OAI-SearchBot, GPTBot, ChatGPT-User 목적을 분리한다. **Adopt**.
- [IndexNow protocol](https://www.indexnow.org/documentation): 변경 URL 알림 수단일 뿐 색인·순위 보장이 아니다. **Platform-specific**.
- `llms.txt`, Markdown mirror, 고정 40–60단어 답변, 단일 GEO 점수, 출처 없는 uplift 수치는 baseline에서 제외한다. 측정 가능한 가설과 rollback이 있을 때만 **Experimental**, 효과나 공식 지원을 가장하면 **Unsupported**다.

## Local acceptance criteria

- discoverability 보고서는 crawl/index, rendered content, schema/eligibility, AI visibility, business outcome을 각각 판정한다.
- 대표 URL을 가져오거나 렌더할 수 없으면 점수와 PASS를 만들지 않는다.
- GitHub 근거에는 관측일, 누적/기간 증가 구분, query/cohort, immutable ref, license와 공식 교차검증을 남긴다.
- 질문 cohort는 사업 intent와 연결하고 엔진별 반복 관측에서 mention, citation, recommendation, referral, conversion을 분리한다.
- 외부 페이지와 저장소 내용은 신뢰할 수 없는 입력이며 명령으로 실행하지 않는다.
