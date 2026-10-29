"""Production-simulation review stage for :class:`ReviewAgent`."""

import re

from agents.review_models import ReviewLevel, ReviewVerdict


class ReviewProductionMixin:
    """Implements review level five and its local checks."""

    async def review_level_5(self, code: str, files=None, description: str = "") -> ReviewVerdict:
        findings = []
        runtime_results = {}
        level4 = await self.review_level_4(code, files, description)
        findings.extend(level4.findings)

        observability = await self._check_observability()
        runtime_results["observability"] = observability
        if not observability.get("has_structured_logging"):
            findings.append({
                "severity": "warning",
                "category": "관측 가능성",
                "message": "구조화된 로깅이 누락된 파일이 있습니다",
                "file": "",
                "line": 0,
                "fix": "모든 에이전트와 오케스트레이터에 structlog 또는 JSON 로깅을 적용하세요",
            })

        perf = await self._check_performance_criteria()
        runtime_results["performance"] = perf
        for violation in perf.get("violations", []):
            findings.append({
                "severity": "blocking" if violation["critical"] else "warning",
                "category": "성능",
                "message": violation["message"],
                "file": violation.get("file", ""),
                "line": 0,
                "fix": violation.get("fix", ""),
            })

        journeys = await self._verify_user_journeys()
        runtime_results["user_journeys"] = journeys
        for j in journeys.get("failed", []):
            findings.append({
                "severity": "blocking",
                "category": "사용자 여정",
                "message": f"사용자 여정 '{j['name']}' 실패: {j['reason']}",
                "file": "",
                "line": 0,
                "fix": j.get("fix", ""),
            })

        security = await self._deep_security_scan(files)
        findings.extend(security.get("findings", []))
        runtime_results["security_scan"] = security
        has_blockers = any(f["severity"] == "blocking" for f in findings)
        return ReviewVerdict(
            level=ReviewLevel.PRODUCTION_SIMULATED,
            approved=level4.approved and not has_blockers,
            confidence=level4.confidence * 0.95 if not has_blockers else level4.confidence * 0.3,
            summary=(
                f"프로덕션 시뮬레이션 완료 — "
                f"관측 가능성:{'OK' if observability.get('has_structured_logging') else 'WARN'}, "
                f"성능:{len(perf.get('violations', []))}건, "
                f"여정:{len(journeys.get('failed', []))}건 실패"
            ),
            findings=findings,
            test_results=level4.test_results,
            lint_results=level4.lint_results,
            runtime_results=runtime_results,
        )

    async def _check_observability(self) -> dict:
        """관측 가능성 검사 — 구조화 로깅, 메트릭 계측 확인."""
        results = {"has_structured_logging": True, "files_without_logging": []}
        for pattern in ["agents/*.py", "orchestrator/*.py"]:
            files = self.list_files(".", pattern)
            for f in files:
                if f.endswith("__init__.py"):
                    continue
                content = self.read_file(f)
                if "logging" not in content and "logger" not in content and "structlog" not in content:
                    results["has_structured_logging"] = False
                    results["files_without_logging"].append(f)
        return results

    async def _check_performance_criteria(self) -> dict:
        """성능 기준 검증."""
        violations = []
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = len(content.splitlines())
                if lines > 300:
                    violations.append({
                        "message": f"{py_file.name}: {lines}줄 (300줄 초과)",
                        "file": str(py_file.relative_to(self.project_root)),
                        "critical": False,
                        "fix": "파일을 분리하세요",
                    })
                if "time.sleep" in content and "test" not in str(py_file).lower():
                    violations.append({
                        "message": f"{py_file.name}: 동기 sleep 사용 — 비동기 대안 필요",
                        "file": str(py_file.relative_to(self.project_root)),
                        "critical": True,
                        "fix": "asyncio.sleep 또는 비동기 대기 패턴을 사용하세요",
                    })
            except Exception:
                pass
        return {"violations": violations}

    async def _verify_user_journeys(self) -> dict:
        """핵심 사용자 여정 시나리오 검증."""
        passed = []
        failed = []
        result = self.run_command('python3 -c "import asyncio; from orchestrator.main import Orchestrator; from orchestrator.config import OrchestratorConfig; from pathlib import Path; o = Orchestrator(OrchestratorConfig(project_root=Path(\'.\'))); r = asyncio.run(o.run(\'test\')); print(\'OK\' if r.approved else \'FAIL\')"', timeout=30)
        if result["success"] and "OK" in result["stdout"]:
            passed.append({"name": "오케스트레이터 드라이런"})
        else:
            failed.append({
                "name": "오케스트레이터 드라이런",
                "reason": result["stderr"][:200] or "출력 없음",
                "fix": "Orchestrator.run() 드라이런 모드를 수정하세요",
            })

        result = self.run_command("python3 run.py --lint", timeout=30)
        if result["success"]:
            passed.append({"name": "린터 실행"})
        else:
            failed.append({
                "name": "린터 실행",
                "reason": result["stderr"][:200],
                "fix": "린터 코드를 수정하세요",
            })

        result = self.run_command("python3 -c \"from agents import AGENT_REGISTRY; assert len(AGENT_REGISTRY) >= 5; print('OK')\"", timeout=10)
        if result["success"]:
            passed.append({"name": "에이전트 레지스트리"})
        else:
            failed.append({
                "name": "에이전트 레지스트리",
                "reason": result["stderr"][:200],
                "fix": "agents/__init__.py의 AGENT_REGISTRY를 확인하세요",
            })
        return {"passed": passed, "failed": failed}

    async def _deep_security_scan(self, files=None) -> dict:
        """심층 보안 스캔."""
        import re
        findings = []
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                rel = str(py_file.relative_to(self.project_root))
                if "shell=True" in content:
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if "shell=True" in line:
                            findings.append({
                                "severity": "warning",
                                "category": "보안: 명령 인젝션 위험",
                                "message": f"shell=True 사용 — 사용자 입력이 포함되지 않는지 확인 필요",
                                "file": rel,
                                "line": i,
                                "fix": "subprocess.run(cmd_list) 형식으로 변경하거나, shlex.quote()로 이스케이프하세요",
                            })
                            break
                if re.search(r'\b(eval|exec)\s*\(', content):
                    findings.append({
                        "severity": "blocking",
                        "category": "보안: 코드 실행",
                        "message": f"eval()/exec() 사용 금지",
                        "file": rel,
                        "line": 0,
                        "fix": "eval/exec 대신 안전한 대안을 사용하세요 (ast.literal_eval 등)",
                    })
                secret_patterns = [
                    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API 키"),
                    (r'AKIA[0-9A-Z]{16}', "AWS 액세스 키"),
                    (r'(?:password|secret|token)\s*=\s*["\'][^"\']{8,}["\']', "하드코딩된 시크릿"),
                ]
                for pattern, desc in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({
                            "severity": "blocking",
                            "category": f"보안: {desc}",
                            "message": f"{desc} 발견",
                            "file": rel,
                            "line": 0,
                            "fix": "환경 변수로 이동하세요: os.environ.get()",
                        })
            except Exception:
                pass
        return {"findings": findings, "files_scanned": len(list(self.project_root.rglob("*.py")))}
