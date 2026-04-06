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
# npx라는 키워드로 Node.js프로그램을 실행할 수 있다!
# @modelcontextprotocol/server-filesystem : mcp 도구이름! 


# 만약 Notion에 접근해서 Notion의 페이지를 쓰고 읽고 수정하고 이러고 싶다!
# 

# Model Context Protocol(규칙)
# 우리도 MCP에 입각해서 도구를 만들 수있음 (fastmcp 프레임워크 이용하면됨!)
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

# 프롬프트 엔지니어링 ! : 내가원하는 답변을 얻기 위해서 프롬프트를 개선~!
# 프롬프트 엔지니어링의 중요성이 떨어졌다! 
# 이유 : 추론 모드 (Thinking) --> 내가 개떡같이 말해도! Thingking토대로 찰떡같이 소화를 하를 함! <-- 프롬프트 엔지니어링을 THinking 소화!!

# AI에게 일을 잘 시키기 위해서 중요한것! (26.4.3 기준)
# - 비싼 모델 쓰기
# - 모델의 특징을 이해하자! (내 작업에 적합한 모델을 선정!)
# - LLM 일을 잘 할 수 있는 환경을 마련해주는 것을 (하네스 엔지니어링!)
# --> 내 작업에 적합한 모델을 선정! 
  # --> 다른 AI 모델도 같이 씀 (CODEX, GEMINI)
# --> MCP 툴을 잘 쥐어주는 것
# --> 메모리 관리 (대화 관리)
# --> 내 작업에 대한 CONTEXT 파일 및 지침 파일 관리
# --> 프롬프트 엔지니어링 


# AX는 회사 내부에서 저것을 만들어주는 직업인가요?
# 내 회사와 업무에 맞는 하네스 엔지니어링이 구축이 되어야 AI를 실제 비서처럼 활용할 수 있음! (내 회사와 업무에 적합하게!)
# 신뢰성!

# CLAUDE CODE <--(1위 비쌈!!)
# CLAUDE CODE (안쓰는 회사가 없다! --> 회사에서 적극 비용지원!!!)
# OPENAI - CODEX (2위 <-- 일반 PRO 조금 많이 사용할 수 있어서!  )

# [ModelRequest]
#   [텍스트] 당신은 파일 시스템 관리 도우미입니다. 한국어로 답변해주세요....
#   [텍스트] 'C:\Users\tjfan\Desktop\text-analysis-llm\mcp_workspace' 디렉토리에 어떤 파일들이 있는지 알려주세요. 각 파일의 내용을 읽고 간단히 요약해주세요....

# [ModelResponse]
#   [도구 호출] list_directory({'path': 'C:\\Users\\tjfan\\Desktop\\text-analysis-llm\\mcp_workspace'})

# [ModelRequest]
#   [도구 응답] list_directory => {'content': '[FILE] ai_trend_report.md\n[FILE] memo.txt\n[FILE] project_ideas.txt\n[FILE] pydanticai_summary.md\n[FILE] sales_2024.csv'}

# [ModelResponse]
#   [도구 호출] read_multiple_files({'paths': ['C:\\Users\\tjfan\\Desktop\\text-analysis-llm\\mcp_workspace/ai_trend_report.md', 'C:\\Users\\tjfan\\Desktop\\text-analysis-llm\\mcp_workspace/memo.txt', 'C:\\Users\\tjfan\\Desktop\\text-an...)
# Users\\tjfan\\Desktop\\text-an...)

# [ModelRequest]
#   [도구 응답] read_multiple_files => {'content': 'C:\\Users\\tjfan\\Desktop\\text-analysis-llm\\mcp_workspace/ai_trend_report.md:\n# 2024-2025 AI 기술 트렌드\n\n### 1. LLM 발전\n대규모 언어 모델(LLM)은 더 적은 파라미터로도 높은 효율을 내는 경량화 기술이 발전하고 있으며, 추론 성능과 문맥 처리 능력이 획기적으로 개선되고 있습니다. 이는 복잡한 논리적 과업을 수행하는 데 있어 정확도와 속도를 동시에 높여줍니다.\n\n### 2. AI Agent\n단순히 질문에 답하는...

# [ModelResponse]
#   [텍스트] 요청하신 `C:\Users\tjfan\Desktop\text-analysis-llm\mcp_workspace` 디렉토리의 파일 목록과 각 파일의 요약 내용은 다음과 같습니다.

# ### 1. `ai_trend_report.md`
# *   **요약**: 2024-2025년 ...


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
        "피카츄와 파이리의 재밌는 모험이야기를 10줄로 만들어줘!"
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


# --- [섹션 3] 실습 (5) 웹페이지 요약 ---
# PydanticAI에 대한 요약입니다.

# 1. **PydanticAI란:** FastAPI가 웹 개발에 혁신을 가져왔듯, Pydantic의 강력한 검증 기능을 활용하여 생성형 AI(GenAI) 애플리케이션과 에이전트를 쉽고 안정적으로 구축할 수 있도록 설계된 파이썬 프레임워크입니다.
# 2. **주요 특징:** OpenAI, Anthropic, Gemini 등 다양한 LLM 모델을 범용적으로 지원하며, 강력한 타입 안전성, 실시간 모니터링(Logfire), 복잡한 워크플로우를 위한 그래프 지원 등을 제공합니다.
# 3. **핵심 가치:** 에이전트 구축 시 생산성을 극대화하기 위해 설계되었으며, 모델 컨텍스트 프로토콜(MCP), 인간 개입이 필요한 워크플로우, 구조화된 출력 스트리밍 등 실무용 에이전트 개발에 필요한 다양한 도구와 기능을 갖추고 있습니다.


# --- [섹션 3] 저장된 파일 내용 ---
# PydanticAI 주요 특징

# PydanticAI는 생성형 AI를 활용한 프로덕션급 애플리케이션 및 워크플로우를 빠르고 안정적으로 구축하기 위해 설계된 Python 에이전트 프레임워크입니다. FastAPI가 웹 개발에 혁신을 가져왔듯, AI 개발에서도 동일한  생산성과 사용자 경험을 제공하는 것을 목표로 합니다.

# ## 주요 특징

# 1.  **Pydantic 팀이 개발**: Pydantic 유효성 검사(Validation)를 기반으로 하여 신뢰성이 높습니다.
# 2.  **모델 무관성(Model-agnostic)**: OpenAI, Anthropic, Gemini, DeepSeek, Grok, Ollama, Bedrock 등 거의 모든 주요 모델 및 공급자를 지원합니다.
# 3.  **원활한 관측 가능성(Seamless Observability)**: Pydantic Logfire와 긴밀하게 통합되어 실시간 디버깅, 성능 모니터링, 추적 및 비용 추적을 지원합니다.
# 4.  **완벽한 타입 안전성(Fully Type-safe)**: IDE 및 AI 코딩 에이전트가 풍부한 문맥을 이해할 수 있도록 설계되어, 런타임 오류를 줄이고 생산성을 높입니다.
# 5.  **강력한 평가 기능(Powerful Evals)**: 구축한 에이전트 시스템의 성능과 정확성을 체계적으로 테스트하고 평가할 수 있습니다.
# 6.  **확장 가능한 설계**: 도구, 후크, 지침 등을 포함한 재사용 가능한 모듈을 통해 에이전트를 쉽게 구축할 수 있습니다.
# 7.  **MCP, A2A 및 UI 지원**: 모델 컨텍스트 프로토콜(MCP), 에이전트 간 통신(Agent2Agent), 스트리밍 이벤트 등을 지원하여 외부 도구 및 타 에이전트와 연동이 가능합니다.
# 8.  **Human-in-the-Loop 도구 승인**: 특정 도구 호출 시 사용자 승인을 요구하는 워크플로우를 쉽게 구현할 수 있습니다.
# 9.  **내구성 있는 실행(Durable Execution)**: API 오류나 프로세스 재시작 시에도 워크플로우가 중단되지 않도록 하여 안정성을 보장합니다.
# 10. **스트리밍 출력**: 구조화된 데이터를 즉각적인 유효성 검사와 함께 지속적으로 스트리밍할 수 있습니다.
# 11. **그래프 지원**: 복잡한 제어 흐름을 가진 애플리케이션을 위해 타입 힌트를 사용한 그래프 정의 기능을 제공합니다.

# ---
# *자세한 내용은 [PydanticAI 공식 문서](https://ai.pydantic.dev/)를 참고하세요.*

# mcp연결할때 공식 문서처럼 공식서버가 있나요 개인서버가 있나요? 둘다 있으면 공식을 우선해야하나요??
# 파일시스템 MCP - 내컴퓨터에서 서버코드를 다운로드해서 실행! (내컴퓨터가 서버가된다!)
# 웹 내용 가져오는 mcp - 내컴퓨터에서 서버코드를 다운로드해서 실행! (내컴퓨터가 서버가된다!)

# 노션 MCP 
# - 내 컴퓨터가 서버 X
# - 노션 회사의 MCP 서버가 있음! HTTP 요청으로 
# MCP CLIENT (나! -> )  ==> 노션 회사의 MCP 서버

#--------
# LLM에 도구를 많이 쥐어줄 수록 다양한 역할 할 수 있음!!
# --> 많이 도구를 등록하는게 좋을까? 안좋을까?
# 토큰 소모도 크고, 에러도 발생 할 수 있다
# mcp 서버 1개당 도구가 여러개 등록
# 도구가 많아 질 수록
# ai가 어떤 도구를 호출해야할지 판다하는게 쉬울까? 어려울까?
# 내 업무에 딱맞는 MCP만 넣어주는게 중요하다!
# 하네스 엔지니어링 중 하나의 역할!

# 

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
    # await run_section_1()  # 1. MCP 서버 연결 기초 - 파일시스템 MCP 서버 연결
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
