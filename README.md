# PydanticAI 텍스트 분석 

PydanticAI를 활용한 생성형 AI 실습 교안입니다.

## 환경 설정

### 필수 요구사항

| 항목 | 설명 |
|---|---|
| Python | 3.12+ |
| 패키지 관리 | `uv` 권장 |
| Node.js | MCP 서버 실행에 필요 (`npx`) |
| API 키 | `.env` 파일에 `GEMINI_API_KEY` 설정 |

### 설치

```bash
uv sync
```

### `.env` 파일 설정

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
YOUTUBE_API_KEY=your_youtube_api_key_here
```

---

## 기본 1. PydanticAI 기본 사용법

> 파일: `기본_1_PydanticAI_기본 사용법.ipynb`

PydanticAI의 핵심 개념과 기본 사용법을 단계별로 학습합니다.

### 실습 목표

1. PydanticAI의 **Agent 개념** 을 이해하고 기본 텍스트 생성을 수행할 수 있습니다.
2. **매개변수(temperature, max_tokens 등)** 를 조절하여 AI 응답을 제어할 수 있습니다.
3. **스트리밍, 멀티턴 대화, 도구 호출** 등 주요 기능을 활용할 수 있습니다.

### 실습 구성

| 섹션 | 주제 | 핵심 내용 |
|---|---|---|
| 환경 설정 | API 키 및 모델 설정 | `.env` 로드, 모델 ID 형식 (`google-gla:모델명`) |
| 1. 기본 텍스트 생성 | Single-turn 대화 | `Agent()` 생성, `agent.run()` 실행, 토큰 사용량 확인, `GoogleModelSettings` 매개변수 조절, Thinking 설정 |
| 2. 스트리밍 응답 | 실시간 응답 출력 | `agent.run_stream()`, `delta=True` 옵션 |
| 3. 멀티턴 대화 | 대화 맥락 유지 | `message_history` 전달, 스트리밍 + 멀티턴 결합 채팅 루프 |
| 4. 도구 (Tool) | 외부 함수 연동 | `@agent.tool_plain` 데코레이터, Wikipedia/YouTube API 연결, 도구 호출 내역 확인 |
| 5. 비동기 동시 호출 | 병렬 처리 | `asyncio.gather()`로 다중 요청 동시 실행, 순차 vs 동시 속도 비교 |

---

## 기본 2. PydanticAI 도구 심화 - MCP 서버 활용

> 파일: `기본_2_PydanticAI_MCP_도구_심화.py` (스크립트)

MCP(Model Context Protocol) 서버를 Agent에 연결하여 파일시스템, 웹, 코드 실행 등 다양한 외부 도구를 활용합니다.

### 실습 목표

1. **MCP의 개념** 을 이해하고 기존 MCP 서버를 Agent에 연결할 수 있습니다.
2. **파일시스템, 웹 가져오기, 코드 실행** MCP 서버를 활용할 수 있습니다.
3. 여러 MCP 서버를 **조합하여 복잡한 워크플로우** 를 구성할 수 있습니다.

### 추가 요구사항

| 항목 | 용도 | 설치 확인 |
|---|---|---|
| `pydantic-ai-slim[mcp]` | MCP 클라이언트 | `uv add "pydantic-ai-slim[mcp]"` |
| `npx` (Node.js) | JS 기반 MCP 서버 실행 | `npx --version` |
| `uvx` (uv) | Python 기반 MCP 서버 실행 | `uvx --version` |

### 실습 구성

| 섹션 | 주제 | 사용 MCP 서버 | 핵심 내용 |
|---|---|---|---|
| 1. MCP 서버 연결 기초 | 파일시스템 연결 | `server-filesystem` | `MCPServerStdio` 설정, `toolsets` 등록, 도구 호출 내역 확인 |
| 2. 파일시스템 MCP 활용 | 파일 생성/검색 | `server-filesystem` | AI가 보고서 작성 후 파일 저장, 확장자별 파일 검색 및 분석 |
| 3. 웹 가져오기 MCP 활용 | 웹페이지 요약 | `mcp-server-fetch` | 웹 내용 마크다운 변환, 파일시스템 + 웹 MCP 동시 연결 |

### Python 스크립트 실행 방법

Jupyter 노트북 대신 Python 스크립트로 실행할 수 있습니다.

```bash
python 기본_2_PydanticAI_MCP_도구_심화.py
```

- `main()` 함수에서 원하는 섹션만 주석 해제하여 선택 실행이 가능합니다.
- **CMD 또는 PowerShell에서 실행하세요.** Git Bash(mintty)는 MCP stdio 통신과 호환 문제가 있습니다.
