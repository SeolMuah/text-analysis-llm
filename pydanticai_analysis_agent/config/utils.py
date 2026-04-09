# =============================================================================
# utils.py - 설정 로딩, 재시도 헬퍼, MCP 서버 정의
# =============================================================================

import os
import sys
import random
import asyncio
from pathlib import Path

import yaml
from dotenv import load_dotenv          # .env 파일에서 API 키 등 환경변수를 로드
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio          # MCP: 외부 프로세스(Python 인터프리터)와 통신하는 프로토콜
from pydantic_ai.models.google import GoogleModelSettings  # Gemini 모델 전용 설정 (temperature, thinking 등)

# =============================================================================
# 설정 로딩
# =============================================================================
# .env 파일에서 GEMINI_API_KEY 등 민감 정보를 환경변수로 로드
load_dotenv()

# __file__은 현재 파일(utils.py)의 경로 → .parent는 config/ 디렉터리
CONFIG_DIR = Path(__file__).parent


def load_settings() -> dict:
    """config/settings.yaml에서 설정을 로드합니다."""
    with open(CONFIG_DIR / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompts(path: str | None = None) -> dict:
    """config/prompts.yaml에서 단계별 프롬프트 템플릿을 로드합니다."""
    if path is None:
        path = str(CONFIG_DIR / "prompts.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("prompts", {})


# 설정 상수 — settings.yaml의 값을 Python 상수로 변환
SETTINGS = load_settings()

# PydanticAI 모델 ID 형식: "provider:model_name" (예: "google-gla:gemini-3.1-flash-lite-preview")
MODEL_ID = f"{SETTINGS['model']['provider']}:{SETTINGS['model']['name']}"
TEMPERATURE = SETTINGS["model"]["temperature"]       # 0=결정적(동일 입력→동일 출력), 1=창의적(매번 다른 출력)
PARALLEL = SETTINGS["pipeline"]["parallel"]
MAX_CONCURRENT = SETTINGS["pipeline"]["max_concurrent"]  # 병렬 시 최대 동시 API 호출 수
VERBOSE = SETTINGS["pipeline"]["verbose"]
STEP_DELAY = SETTINGS["pipeline"]["step_delay"]       # Step 간 대기 — API rate limit 방지
TASK_DELAY = SETTINGS["pipeline"]["task_delay"]        # 과제 간 대기 — 순차 모드에서 API 부하 분산
MAX_RETRIES = SETTINGS["retry"]["max_retries"]         # 재시도 횟수 (초기 시도 미포함)
BASE_RETRY_DELAY = SETTINGS["retry"]["base_delay"]     # 지수 백오프 기본 대기 시간 (초)
MAX_RETRY_DELAY = SETTINGS["retry"]["max_delay"]       # 백오프 상한 — 아무리 실패해도 이 이상 기다리지 않음

# Step별 Thinking Level 설정
# google_thinking_config: Gemini의 "생각하는 깊이"를 조절
#   - "low":    빠르고 저비용. 단순 지시 수행에 적합
#   - "medium": 대부분의 작업에 균형잡힌 사고
#   - "high":   복잡한 판단에 적합 (느리지만 정확)
STEP_SETTINGS = {
    "step_1": GoogleModelSettings(temperature=TEMPERATURE, google_thinking_config={"thinking_level": SETTINGS["thinking"]["step_1_schema"]}),
    "step_2": GoogleModelSettings(temperature=TEMPERATURE, google_thinking_config={"thinking_level": SETTINGS["thinking"]["step_2_plan"]}),
    "step_3": GoogleModelSettings(temperature=TEMPERATURE, google_thinking_config={"thinking_level": SETTINGS["thinking"]["step_3_codegen"]}),
    "step_4": GoogleModelSettings(temperature=TEMPERATURE, google_thinking_config={"thinking_level": SETTINGS["thinking"]["step_4_execute"]}),
    "step_5": GoogleModelSettings(temperature=TEMPERATURE, google_thinking_config={"thinking_level": SETTINGS["thinking"]["step_5_report"]}),
}

# 프롬프트
PROMPTS = load_prompts()


# =============================================================================
# MCP 서버 정의
# =============================================================================
# MCP(Model Context Protocol)란?
#   LLM이 외부 도구(여기서는 Python 인터프리터)를 호출할 수 있게 해주는 프로토콜입니다.
#   Agent가 "이 코드를 실행해줘"라고 요청하면, MCP 서버가 실제로 Python을 실행하고 결과를 돌려줍니다.
#
# .venv 탐색: 프로젝트 폴더 → 상위 폴더 순으로 찾음
_venv_dir = Path(__file__).parent.parent / ".venv"
if not _venv_dir.exists():
    _venv_dir = Path(__file__).parent.parent.parent / ".venv"
# Windows는 Scripts/python.exe, Mac/Linux는 bin/python 경로가 다름
_venv_python = str(
    _venv_dir / "Scripts" / "python.exe" if sys.platform == "win32"
    else _venv_dir / "bin" / "python"
)

# MCPServerStdio: 표준입출력(stdin/stdout)으로 MCP 서버와 통신
# uvx: uv 패키지 매니저의 실행 도구 (npx와 유사한 역할)
python_mcp = MCPServerStdio(
    "uvx",
    args=["mcp-python-interpreter", "--python", _venv_python],
    timeout=60,  # MCP 서버 응답 대기 최대 60초
)

# =============================================================================
# 지수 백오프(Exponential Backoff) 재시도 헬퍼
# =============================================================================
# 지수 백오프란?
#   API 호출이 실패했을 때 바로 재시도하지 않고, 점점 더 오래 기다리며 재시도하는 전략입니다.
#   대기 시간이 2배씩 늘어나므로 "지수(exponential)" 백오프라고 부릅니다.
#
#   대기 시간 예시 (base_delay=3초, max_retries=3):
#     초기 시도 → 실패 → 3초 대기 → 재시도1 → 실패 → 6초 대기 → 재시도2 → 실패 → 12초 대기 → 재시도3

async def run_with_retry(
    agent: Agent,
    prompt: str | list,
    step_name: str = "",
    model_settings: GoogleModelSettings | None = None,
):
    """
    agent.run()을 지수 백오프로 재시도합니다.

    Args:
        prompt: 텍스트 문자열 또는 멀티모달 리스트 [BinaryContent, ..., "텍스트"]

    - ValidationError 등 재시도 불가능한 오류는 즉시 raise
    - 429/5xx 등 일시적 오류만 지수 백오프로 재시도

    총 시도 횟수 = 초기 1회 + MAX_RETRIES회
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = await agent.run(prompt, model_settings=model_settings)
            return result.output

        # 재시도해도 해결 불가능한 오류 → 즉시 중단
        except (ValidationError, TypeError, KeyError):
            raise

        # 그 외 오류 (429, 503 등 일시적 오류) → 재시도 대상
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"\n   [{step_name}] 최대 재시도 횟수({MAX_RETRIES}) 초과: {e}")
                raise

            # 지수 백오프: base * 2^attempt + jitter
            backoff = min(BASE_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
            jitter = random.uniform(0, backoff * 0.3)
            delay = backoff + jitter

            print(
                f"\n   [{step_name}] 재시도 {attempt + 1}/{MAX_RETRIES} "
                f"| {delay:.1f}초 후 | {e}"
            )
            await asyncio.sleep(delay)
