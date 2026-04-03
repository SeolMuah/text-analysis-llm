"""
PydanticAI 도구 심화 - MCP 서버 활용 (Python 스크립트 버전)

실습 목표:
1. MCP(Model Context Protocol)의 개념을 이해하고 기존 MCP 서버를 Agent에 연결할 수 있습니다.
2. 파일시스템, 웹 가져오기, 코드 실행 MCP 서버를 활용할 수 있습니다.
3. 여러 MCP 서버를 조합하여 복잡한 워크플로우를 구성할 수 있습니다.

사용법:
  CMD 또는 PowerShell에서 Shift+Enter로 블록 단위 실행이 가능합니다.
  (Git Bash는 MCP stdio 통신과 호환 문제가 있으므로 CMD/PowerShell을 사용하세요.)
"""

import os
import platform
import shutil
import asyncio
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from utils import print_tool_calls


# ============================================================
# 환경 설정
# ============================================================

load_dotenv()

# API 키 설정
api_key = os.getenv('GEMINI_API_KEY')
gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
model_id = f'google-gla:{gemini_model}'

api_key_valid = api_key and 'YOUR_API_KEY' not in api_key
print(f"API 키 설정 확인: {'✓' if api_key_valid else '✗'}")
print(f"모델: {model_id}")

# npx 확인 (MCP 서버 실행에 필요합니다)
npx_path = shutil.which('npx')
print(f"npx 설치 확인: {'✓' if npx_path else '✗ (Node.js 설치 필요)'}")

# uvx 확인 (Python MCP 서버 실행에 필요합니다)
uvx_path = shutil.which('uvx')
print(f"uvx 설치 확인: {'✓' if uvx_path else '✗'}")

# 운영 체제 확인 (경로 처리에 사용합니다)
current_os = platform.system()
print(f"운영 체제: {current_os}")

# 작업 디렉토리 설정 (Windows와 Mac 모두 호환됩니다)
work_dir = Path.cwd() / 'mcp_workspace'
work_dir.mkdir(exist_ok=True)
work_dir_str = str(work_dir)
print(f"작업 디렉토리: {work_dir_str}")

# MCP 서버 간 대기 시간(초) - 무료 API 호출 제한을 피하기 위한 간격
MCP_SLEEP_SEC = 4



# ============================================================
# 1. MCP 서버 연결 기초
# ============================================================
# 공식 문서: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
# PydanticAI MCP 연동: https://ai.pydantic.dev/mcp/
#
# @modelcontextprotocol/server-filesystem 서버가 제공하는 주요 도구:
#   read_file      - 파일 내용 읽기
#   write_file     - 파일 생성/쓰기
#   list_directory - 디렉토리 목록 조회
#   search_files   - 파일 검색
#   get_file_info  - 파일 정보 조회
# ============================================================

# --- 실습 (1) 파일시스템 MCP 서버 연결 ---
# npx로 @modelcontextprotocol/server-filesystem을 실행합니다
# 허용할 디렉토리 경로를 인자로 전달합니다 (이 디렉토리 밖에는 접근할 수 없습니다)


# pip install pandas
# npx 
async def _run_fs_list():
    fs_server = MCPServerStdio(
        'npx',                      # MCP 서버를 실행할 명령어 (Node.js 패키지 러너)
        args=[                      # 명령어에 전달할 인자 목록
            '-y',                   # npx 설치 확인 프롬프트 자동 승인
            '@modelcontextprotocol/server-filesystem',  # 실행할 MCP 서버 패키지
            work_dir_str,           # 접근을 허용할 디렉토리 경로
        ],
        timeout=30,                 # 서버 시작 대기 시간(초). 첫 실행 시 패키지 다운로드로 오래 걸릴 수 있음
    )
    
    # Agent 생성 - toolsets에 MCP 서버를 등록합니다
    fs_agent = Agent(
        model_id,
        system_prompt=(
            "당신은 파일 시스템 관리 도우미입니다. "
            "한국어로 답변해주세요."
        ),
        toolsets=[fs_server],
    )
    # Agent 실행 - MCP 서버의 수명주기가 자동으로 관리됩니다
    return await fs_agent.run(
        f"'{work_dir_str}' 디렉토리에 어떤 파일들이 있는지 알려주세요. "
        "각 파일의 내용을 읽고 간단히 요약해주세요."
    )


# --- 실습 (2) Agent의 도구 호출 내역 확인 ---
# MCP 서버의 도구(list_directory, read_file 등)가 자동으로 호출된 것을 볼 수 있습니다
# detail=True: 메시지 타입과 내용 미리보기까지 상세 출력합니다

async def run_section_1():
    """1. MCP 서버 연결 기초 - 파일시스템 MCP 서버 연결 및 도구 호출 내역 확인"""
    print("\n" + "=" * 60)
    print("  [섹션 1] MCP 서버 연결 기초")
    print("=" * 60)

    # await: 비동기 함수(코루틴)의 완료를 기다립니다.
    # _run_fs_list()는 async def로 정의된 코루틴이므로 반드시 await로 호출해야 합니다.
    result = await _run_fs_list()

    print("\n--- [섹션 1] 실습 파일시스템 MCP 서버 응답 ---")
    print(result.output)

    print("\n--- [섹션 1] 실습 도구 호출 내역 ---")
    print_tool_calls(result, detail=True)


# ============================================================
# 2. 파일시스템 MCP 활용
# ============================================================

# --- 실습 (3) AI 트렌드 보고서 작성 및 파일 저장 ---

async def _run_fs_create_report():
    fs_server = MCPServerStdio(
        'npx',
        args=['-y', '@modelcontextprotocol/server-filesystem', work_dir_str],
        timeout=30,
    )
    fs_agent = Agent(
        model_id,
        system_prompt=(
            "당신은 파일 시스템 관리 도우미입니다. "
            "한국어로 답변해주세요."
        ),
        toolsets=[fs_server],
    )
    return await fs_agent.run(
        f"'{work_dir_str}' 디렉토리에 'ai_trend_report.md' 파일을 만들어주세요. "
        "내용은 '2024-2025 AI 기술 트렌드'라는 제목으로 "
        "3가지 핵심 트렌드(LLM 발전, AI Agent, 멀티모달 AI)를 "
        "각각 2-3줄로 정리해주세요. "
        "작성이 완료되면 파일 내용을 읽어서 확인해주세요."
    )


# --- 실습 (4) 파일 검색 및 분석 ---

async def _run_fs_search():
    fs_server = MCPServerStdio(
        'npx',
        args=['-y', '@modelcontextprotocol/server-filesystem', work_dir_str],
        timeout=30,
    )
    fs_agent = Agent(
        model_id,
        system_prompt=(
            "당신은 파일 시스템 관리 도우미입니다. "
            "한국어로 답변해주세요."
        ),
        toolsets=[fs_server],
    )
    return await fs_agent.run(
        f"'{work_dir_str}' 디렉토리에서 '.txt' 파일을 모두 찾아주세요. "
        "각 파일의 내용을 읽고 어떤 내용인지 한 줄로 요약해주세요."
    )


async def run_section_2():
    """2. 파일시스템 MCP 활용 - 보고서 작성 및 파일 검색"""
    print("\n" + "=" * 60)
    print("  [섹션 2] 파일시스템 MCP 활용")
    print("=" * 60)

    # 실습 (3) AI 트렌드 보고서 작성 및 파일 저장
    result = await _run_fs_create_report()
    print("\n--- [섹션 2] 실습 (3) AI 트렌드 보고서 작성 ---")
    print(result.output)

    await asyncio.sleep(MCP_SLEEP_SEC)  # 무료 API 호출 제한 대기

    # 실습 (4) 파일 검색 및 분석
    result = await _run_fs_search()
    print("\n--- [섹션 2] 실습 (4) 파일 검색 및 분석 ---")
    print(result.output)


# ============================================================
# 3. 웹 가져오기 MCP 활용
# ============================================================
# GitHub: https://github.com/modelcontextprotocol/servers/tree/main/src/fetch
# mcp-server-fetch는 웹페이지의 내용을 가져오는 공식 MCP 서버입니다.
# 웹페이지를 마크다운으로 변환하여 AI가 읽기 쉬운 형태로 제공합니다.
# ============================================================

# --- 실습 (5) 웹페이지 요약 ---

async def _run_fetch_summary():
    fetch_server = MCPServerStdio(
        'uvx',                      # Python 패키지 러너 (npx의 Python 버전)
        args=['mcp-server-fetch'],  # 실행할 MCP 서버 패키지명
        timeout=30,
    )
    fetch_agent = Agent(
        model_id,
        system_prompt=(
            "당신은 웹 리서치 전문가입니다. "
            "도구를 사용하여 웹페이지 내용을 가져오고, 핵심을 정리해주세요. "
            "한국어로 답변해주세요."
        ),
        toolsets=[fetch_server],
    )
    return await fetch_agent.run(
        "https://ai.pydantic.dev/ 페이지의 내용을 가져와서 "
        "PydanticAI가 무엇인지, 주요 기능은 무엇인지 3줄로 요약해주세요."
    )


# --- 실습 (6) 파일시스템 + 웹 가져오기 MCP 동시 연결 ---
# 여러 MCP 서버를 toolsets 리스트에 함께 전달하면 동시에 사용할 수 있습니다

async def _run_multi_fetch_save():
    fs_server = MCPServerStdio(
        'npx',
        args=['-y', '@modelcontextprotocol/server-filesystem', work_dir_str],
        timeout=30,
    )
    fetch_server = MCPServerStdio(
        'uvx',
        args=['mcp-server-fetch'],
        timeout=30,
    )
    # 두 MCP 서버를 모두 toolsets에 등록합니다
    multi_agent = Agent(
        model_id,
        system_prompt=(
            "당신은 웹 리서치 및 파일 관리 전문가입니다. "
            "웹에서 정보를 가져오고, 파일시스템에 저장하는 작업을 수행합니다. "
            "한국어로 답변해주세요."
        ),
        toolsets=[fs_server, fetch_server],
    )
    return await multi_agent.run(
        "https://ai.pydantic.dev/ 페이지에서 PydanticAI의 주요 특징을 가져와서 "
        f"'{work_dir_str}/pydanticai_summary.md' 파일로 저장해주세요. "
        "마크다운 형식으로 깔끔하게 정리해주세요."
    )


async def run_section_3():
    """3. 웹 가져오기 MCP 활용 - 웹페이지 요약 및 파일 저장"""
    print("\n" + "=" * 60)
    print("  [섹션 3] 웹 가져오기 MCP 활용")
    print("=" * 60)

    # 실습 (5) 웹페이지 요약
    result = await _run_fetch_summary()
    print("\n--- [섹션 3] 실습 (5) 웹페이지 요약 ---")
    print(result.output)

    await asyncio.sleep(MCP_SLEEP_SEC)  # 무료 API 호출 제한 대기

    # 실습 (6) 파일시스템 + 웹 가져오기 MCP 동시 연결
    result = await _run_multi_fetch_save()
    print("\n--- [섹션 3] 실습 (6) 웹 가져오기 + 파일 저장 ---")
    print(result.output)

    # 저장된 파일 확인
    summary_path = work_dir / 'pydanticai_summary.md'
    print("\n--- [섹션 3] 저장된 파일 내용 ---")
    if summary_path.exists():
        print(summary_path.read_text(encoding='utf-8'))
    else:
        print("파일이 아직 생성되지 않았습니다.")



async def main():
    """
    프로그램의 비동기 진입점(entry point)입니다.

    비동기 문법 핵심 정리:
    - async def: 비동기 함수(코루틴)를 정의합니다. 일반 함수와 달리 await를 사용할 수 있습니다.
    - await: 코루틴의 실행이 완료될 때까지 기다립니다. async def 안에서만 사용 가능합니다.
    - asyncio.run(): 코루틴을 실행하는 진입점입니다. 이벤트 루프를 만들고 코루틴을 실행한 뒤 루프를 닫습니다.

    흐름 예시:
        asyncio.run(main())          # 이벤트 루프 생성 + main() 실행
            └─ await run_section_1() # run_section_1 코루틴 완료 대기
    """

    # ── 하나씩 실행하기 (순차 실행) ──
    # 위에서 아래로 순서대로 실행됩니다.
    # 각 섹션 사이에 asyncio.sleep()으로 간격을 두어
    # 무료 API 호출 제한을 피하기 위해 섹션 사이에 대기합니다.
    await run_section_1()  # 1. MCP 서버 연결 기초 - 파일시스템 MCP 서버 연결
    # await asyncio.sleep(MCP_SLEEP_SEC)  # 무료 API 호출 대기
    # await run_section_2()  # 2. 파일시스템 MCP 활용 - 보고서 작성 및 파일 검색
    # await asyncio.sleep(MCP_SLEEP_SEC)  # 무료 API 호출 제한 대기
    # await run_section_3()  # 3. 웹 가져오기 MCP 활용 - 웹페이지 요약 및 파일 저장

    # ── 여러 섹션 동시에 실행하기 (병렬 실행) ──
    # asyncio.gather()는 여러 코루틴을 동시에(concurrently) 실행합니다.
    # 각 코루틴이 await로 대기하는 동안 다른 코루틴이 실행되어 전체 시간이 단축됩니다.
    # 단, print 출력이 섞일 수 있고 같은 파일에 동시 접근 시 충돌 가능성이 있습니다.
    #
    # await asyncio.gather(
    #     run_section_1(),
    #     run_section_2(),
    #     run_section_3(),
    # )


if __name__ == '__main__':
    # ============================================================
    # 메인 실행 블록
    # ============================================================
    # asyncio.run()은 프로그램 전체에서 딱 한 번만 호출하는 것이 원칙입니다.
    # 이유: asyncio.run()은 새 이벤트 루프를 생성 → 코루틴 실행 → 루프 종료를
    #       한 번에 처리하므로, 여러 번 호출하면 루프 충돌이 발생할 수 있습니다.
    #
    # 따라서 async def main() 안에서 모든 비동기 작업을 await로 호출하고,
    # asyncio.run(main())은 프로그램 진입점에서 단 한 번만 실행합니다.
    #
    # 실행하고 싶은 섹션의 주석을 해제하고 실행하세요.
    # ============================================================
    asyncio.run(main())
