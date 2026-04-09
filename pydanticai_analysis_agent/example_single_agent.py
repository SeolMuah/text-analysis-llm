# =============================================================================
# example_single_agent.py - 단일 Agent 데이터 분석 예시 (교육용)
# =============================================================================
#
# 하나의 Agent가 사용자 질문에 따라 알아서 판단합니다:
#   - SQLite MCP → DB 테이블 조회, 스키마 확인
#   - Python MCP → 코드 실행, 계산, 시각화
#
# 사용자는 자연어로 질문만 하면 됩니다.
# Agent가 어떤 도구를 쓸지 스스로 결정합니다.
#
# 실행: uv run python example_single_agent.py
# =============================================================================

import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.google import GoogleModelSettings

load_dotenv()

# =============================================================================
# 설정
# =============================================================================

# 모델 (config/settings.yaml 대신 직접 지정 — 예시이므로 단순하게)
MODEL_ID = "google-gla:gemini-3.1-flash-lite-preview"

# 프로젝트 폴더 기준 절대 경로
_PROJECT_DIR = Path(__file__).parent
DB_PATH = str(_PROJECT_DIR / "data" / "chinook.db")
OUTPUTS_DIR = str(_PROJECT_DIR / "outputs" / "charts")

# .venv 탐색: 현재 폴더 → 상위 폴더 순으로 찾음
_venv_dir = Path(__file__).parent / ".venv"
if not _venv_dir.exists():
    _venv_dir = Path(__file__).parent.parent / ".venv"
VENV_PYTHON = str(
    _venv_dir / "Scripts" / "python.exe" if sys.platform == "win32"
    else _venv_dir / "bin" / "python"
)


# =============================================================================
# MCP 서버 정의 (2개)
# =============================================================================

# 1) SQLite MCP — DB 테이블 조회, SQL 실행
#    도구: read_query, write_query, list_tables, describe_table 등
sqlite_mcp = MCPServerStdio(
    "uvx",
    args=["mcp-server-sqlite", "--db-path", DB_PATH],
    timeout=30,
)

# 2) Python MCP — 코드 실행 (pandas 분석, matplotlib 시각화 등)
#    도구: run_python_code
#
#    --python 옵션으로 .venv의 Python을 지정합니다.
#    Agent가 코드를 실행할 때 아래 설정을 시스템 프롬프트에서 강제합니다:
#
#    [execution_mode]
#      - subprocess: .venv Python을 별도 프로세스로 실행 → pandas/matplotlib 접근 가능
#      - inline:     MCP 서버 내부에서 eval() 실행 → .venv 패키지 접근 불가 (사용 금지)
#
#    [environment]
#      - default: .venv Python (uv sync로 설치한 패키지 사용 가능)
#      - system:  uv 캐시의 시스템 Python (패키지 없음, 사용 금지)
python_mcp = MCPServerStdio(
    "uvx",
    args=["mcp-python-interpreter", "--python", VENV_PYTHON],
    timeout=60,
)


# =============================================================================
# Agent 정의 (단 1개)
# =============================================================================
# 2개의 MCP 서버를 toolsets에 함께 등록하면,
# Agent가 질문에 따라 어떤 도구를 쓸지 스스로 판단합니다.

agent = Agent(
    MODEL_ID,
    system_prompt=(
        "당신은 데이터 분석 전문가입니다.\n\n"
        "도구 선택 규칙:\n"
        "1. DB 조회(SELECT, 집계, 정렬 등)는 반드시 SQLite 도구(read_query)를 사용하세요.\n"
        "   Python으로 sqlite3.connect()를 직접 하지 마세요.\n"
        "2. Python 도구는 차트 생성, 복잡한 데이터 가공 등 SQL만으로 불가능한 작업에만 사용하세요.\n\n"
        "run_python_code 호출 시 필수 파라미터:\n"
        "  execution_mode: 'subprocess'\n"
        "  environment: 'default'\n"
        "이 두 파라미터 없이 호출하면 실패합니다.\n\n"
        f"DB 경로: {DB_PATH}\n"
        "한국어로 답변해주세요."
    ),
    toolsets=[sqlite_mcp, python_mcp],
)


# =============================================================================
# 실행
# =============================================================================
# 표시 옵션
SHOW_TOOL_CALLS = True # 도구 호출/결과 표시

# Gemini 모델 설정
MODEL_SETTINGS = GoogleModelSettings(
    temperature=0.1,
    google_thinking_config={
        "thinking_level": "medium",
    },
)


async def ask(question: str) -> str:
    """질문을 Agent에 보내고, 전체 과정을 시간순으로 출력합니다."""
    from pydantic_ai.messages import (
        TextPart, ToolCallPart, ToolReturnPart,
    )

    print(f"\n{'='*60}")
    print(f"질문: {question}")
    print("=" * 60)

    # 답변 실시간 스트리밍
    print("\n[답변]")
    async with agent.run_stream(question, model_settings=MODEL_SETTINGS) as stream:
        async for chunk in stream.stream_text(delta=True):
            print(chunk, end="", flush=True)
        output = await stream.get_output()
        messages = stream.all_messages()
    print("\n")

    # 전체 메시지 시간순 출력 
    print(f"{'─'*60}")
    print("[전체 실행 과정]")
    print(f"{'─'*60}")
    for msg in messages:
        for part in msg.parts:
            if SHOW_TOOL_CALLS and isinstance(part, ToolCallPart):
                args_str = str(part.args)
                print(f"\n  [도구 호출] {part.tool_name}({args_str[:300]}{'...' if len(args_str) > 300 else ''})")

            elif SHOW_TOOL_CALLS and isinstance(part, ToolReturnPart):
                content = str(part.content)
                print(f"  [도구 결과] {part.tool_name}")
                print(f"  {content[:300]}{'...' if len(content) > 300 else ''}")

    return output


async def main():
    print("Chinook DB 분석 Agent (종료: q 또는 exit)")
    print()
    print("[SQL 질문] — SQLite MCP가 직접 쿼리 실행")
    print("  - 테이블 목록 알려줘")
    print("  - 매출 상위 5개 국가는?")
    print("  - 고객당 평균 구매액과 구매 빈도를 계산하고, VIP 고객 10명 뽑아줘")
    print("  - 직원별 담당 고객 수와 해당 고객들의 총 매출을 비교해줘")
    print()
    print("[Python 질문] — Python MCP로 코드 실행 (pandas, matplotlib)")
    print("  - 장르별 트랙 수와 평균 곡 길이(분)를 분석해줘")
    print(f"  - 연도별 매출 추이를 차트로 그려서 {OUTPUTS_DIR}/yearly_sales.png로 저장해줘")
    print(f"  - 장르별 매출 비중을 파이 차트로 그려서 {OUTPUTS_DIR}/genre_pie.png로 저장해줘")

    while True:
        question = input("\n질문> ").strip()
        if not question:
            continue
        if question.lower() in ("q", "quit", "exit"):
            print("종료합니다.")
            break
        try:
            await ask(question)
        except Exception as e:
            print(f"\n[오류] {e}\n다시 시도해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
