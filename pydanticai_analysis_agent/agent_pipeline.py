# =============================================================================
# agent_pipeline.py - PydanticAI 기반 데이터 분석 자동화 Agent
# =============================================================================
#                   (Step 1)    (Step 2)   (Step 3)   (Step 4)   (Step 5)
# [데이터 + 요청] → 스키마 분석 → 과제 정의 → 코드 생성 → 코드 실행 → 보고서
# =============================================================================

import json
import asyncio
from pathlib import Path
from datetime import datetime

from pydantic_ai import Agent, BinaryContent

from schemas import SchemaAnalysisResult, TaskPlan, GeneratedCode, Report  # Pydantic 스키마 (LLM 출력 형식 정의)
from config.utils import (
    MODEL_ID, PARALLEL, VERBOSE, MAX_CONCURRENT, STEP_DELAY, TASK_DELAY,
    STEP_SETTINGS, PROMPTS, python_mcp, run_with_retry,
)


# Step 1: 스키마 분석 Agent
# - MCP로 pandas 코드를 실행하여 데이터 파일의 컬럼, 타입, 행수, 샘플 등을 탐색
schema_agent = Agent(
    MODEL_ID,
    output_type=SchemaAnalysisResult,
    system_prompt=(
        "당신은 데이터 엔지니어입니다. "
        "Python 코드를 실행하여 데이터를 탐색하고 스키마를 분석합니다. "
        "Python 코드 실행 시 반드시 execution_mode='subprocess', environment='default'를 사용하세요. "
        "한국어로 답변해주세요."
    ),
    toolsets=[python_mcp],               # 이 에이전트가 사용할 도구 (Python 코드 실행 MCP)
)

# Step 2: 과제 정의 Agent
# - 스키마 분석 결과 + 사용자 요청을 받아 3~5개의 분석 과제를 설계
# - 각 과제의 질문, 분석 방법, 출력 형태(chart/table/metric/text)를 결정
plan_agent = Agent(
    MODEL_ID,
    output_type=TaskPlan,
    system_prompt="당신은 데이터 분석가입니다. 분석 과제를 체계적으로 정의합니다.",
)

# Step 3: 코드 생성 Agent
# - 각 과제에 대해 실행 가능한 Python 코드를 생성
# - 차트 저장 경로, 한글 폰트 설정 등 실행 환경을 고려한 코드 작성
codegen_agent = Agent(
    MODEL_ID,
    output_type=GeneratedCode,
    system_prompt="당신은 Python 개발자입니다. 분석 과제에 대한 실행 가능한 코드를 생성합니다.",
)

# Step 4: 코드 실행 Agent (자가 치유 기능)
# - 생성된 .py 파일을 읽고 사전 검토 (경로, 컬럼명, import 등)
# - MCP로 코드를 실행하고, 오류 발생 시 원인 분석 → 코드 수정 → 재실행 (최대 3회)
# - 실행 결과(stdout, 차트 생성 여부)를 정리하여 보고
execute_agent = Agent(
    MODEL_ID,
    system_prompt=(
        "당신은 코드 검토 및 실행 전문가입니다. "
        "Python 코드를 검토하고 실행합니다. "
        "Python 코드 실행 시 반드시 execution_mode='subprocess', environment='default'를 사용하세요. "
        "한국어로 답변해주세요."
    ),
    toolsets=[python_mcp],
)

# Step 5: 보고서 생성 Agent
# - 모든 과제의 실행 결과를 종합하여 구조화된 보고서를 작성
# - Executive Summary, 핵심 발견사항, 과제별 인사이트, 종합 결론, 제언을 포함
report_agent = Agent(
    MODEL_ID,
    output_type=Report,
    system_prompt="당신은 비즈니스 분석가입니다. 분석 결과를 전문적인 보고서로 작성합니다.",
)


# =============================================================================
# Step 1: 스키마 분석
# =============================================================================
async def step1_analyze_schema(
    data_path: str,
    user_request: str,
    output_dir: str,
    verbose: bool = True,
) -> SchemaAnalysisResult:
    """MCP를 통해 Python 코드를 실행하여 데이터 스키마를 분석합니다.

    Agent가 데이터 파일을 읽고 컬럼명, 타입, 행수, 결측치 등을 탐색한 뒤,
    SchemaAnalysisResult 스키마에 맞는 구조화된 결과를 반환합니다.

    Args:
        data_path: 분석할 데이터 파일 또는 폴더 경로
        user_request: 사용자의 분석 요청 (프롬프트에 포함되어 탐색 방향을 안내)
        output_dir: 결과 JSON을 저장할 상위 디렉터리
        verbose: True면 분석 결과 요약을 콘솔에 출력

    Returns:
        SchemaAnalysisResult: 데이터 소스별 컬럼 정보, 행수, 품질 등이 담긴 객체
    """
    print("\n" + "=" * 60)
    print("[Step 1] 스키마 분석")
    print("=" * 60)

    code_dir = str(Path(output_dir) / "code")
    Path(code_dir).mkdir(parents=True, exist_ok=True)

    prompt = PROMPTS["schema"].format(
        user_request=user_request,
        data_path=data_path,
        code_dir=code_dir,
    )

    # MCP 도구 실행 + 구조화된 출력을 하나의 Agent가 동시에 처리
    schema_obj = await run_with_retry(
        schema_agent, prompt, step_name="Step 1",
        model_settings=STEP_SETTINGS["step_1"],
    )

    if verbose:
        print(f"   소스 수: {schema_obj.source_count}")
        print(f"   품질: {schema_obj.overall_quality}")
        for src in schema_obj.sources:
            print(f"   - {src.source_name}: {src.row_count}행 x {src.column_count}열")

    # 결과 저장
    temp_dir = Path(output_dir) / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    with open(temp_dir / "step1_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema_obj.model_dump(), f, ensure_ascii=False, indent=2)

    print("\n[Step 1] 완료")
    return schema_obj


# =============================================================================
# Step 2: 과제 정의
# =============================================================================
async def step2_define_tasks(
    schema_result: str,
    user_request: str,
    data_path: str,
    output_dir: str,
    verbose: bool = True,
) -> TaskPlan:
    """스키마 분석 결과를 바탕으로 3~5개의 분석 과제를 설계합니다.

    LLM이 사용자 요청과 데이터 구조를 고려하여 각 과제의 질문, 분석 방법,
    출력 형태(chart/table/metric/text)를 결정합니다.

    Args:
        schema_result: Step 1에서 생성된 스키마 분석 결과 (JSON 문자열)
        user_request: 사용자의 분석 요청
        data_path: 데이터 파일/폴더 경로
        output_dir: 결과 저장 디렉터리
        verbose: True면 과제 목록을 콘솔에 출력

    Returns:
        TaskPlan: 분석 목표, 데이터 출처, 과제 목록이 담긴 객체
    """
    print("\n" + "=" * 60)
    print("[Step 2] 과제 정의")
    print("=" * 60)

    charts_dir = str(Path(output_dir) / "charts")

    prompt = PROMPTS["plan"].format(
        data_path=data_path,
        schema_result=schema_result,
        user_request=user_request,
        charts_dir=charts_dir,
        output_dir=output_dir,
    )

    # PydanticAI가 LLM 응답 → TaskPlan 객체로 자동 변환
    plan = await run_with_retry(
        plan_agent, prompt, step_name="Step 2",
        model_settings=STEP_SETTINGS["step_2"],
    )

    # 결과 저장
    temp_dir = Path(output_dir) / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    with open(temp_dir / "step2_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"\n분석 목표: {plan.goal}")
        print(f"데이터 출처: {plan.data_source}")
        print(f"과제 수: {len(plan.tasks)}개")
        for i, task in enumerate(plan.tasks, 1):
            print(f"   {i}. {task.title} [{task.output_type}]")

    print("\n[Step 2] 완료")
    return plan


# =============================================================================
# Step 3: 코드 생성
# =============================================================================
async def step3_generate_code(
    plan: TaskPlan,
    schema_result: str,
    output_dir: str,
    parallel: bool = False,
    verbose: bool = True,
) -> list[GeneratedCode]:
    """각 과제에 대해 실행 가능한 Python 분석 코드를 생성합니다.

    LLM이 과제별로 pandas/matplotlib 등을 활용한 코드를 작성하고,
    output_dir/code/ 에 .py 파일로 저장합니다.

    Args:
        plan: Step 2에서 생성된 과제 계획
        schema_result: 스키마 분석 결과 (JSON 문자열, 코드 생성 시 참조)
        output_dir: 코드 파일을 저장할 상위 디렉터리
        parallel: True면 모든 과제를 동시에 생성 (API rate limit 주의)
        verbose: True면 진행 상황을 콘솔에 출력

    Returns:
        list[GeneratedCode]: 과제별 생성된 코드 객체 리스트
    """
    print("\n" + "=" * 60)
    print(f"[Step 3] 코드 생성 ({'병렬' if parallel else '순차'} 모드)")
    print("=" * 60)

    code_dir = Path(output_dir) / "code"
    charts_dir = Path(output_dir) / "charts"
    code_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    async def generate_single(i: int, task) -> GeneratedCode:
        """단일 과제의 코드를 생성합니다."""
        if verbose:
            print(f"\n--- 과제 {i}/{len(plan.tasks)}: {task.title} ---")

        chart_info = task.chart_filename or "없음"

        prompt = PROMPTS["generate"].format(
            schema_result=schema_result,
            task_number=i,
            task_title=task.title,
            task_question=task.question,
            task_data_files=task.data_files,
            task_method=task.method,
            task_output_type=task.output_type,
            task_chart_filename=chart_info,
            charts_dir=charts_dir,
        )

        code = await run_with_retry(
            codegen_agent, prompt, step_name=f"Step 3-{i}",
            model_settings=STEP_SETTINGS["step_3"],
        )

        # Literal 타입이므로 "chart", "table" 등 문자열이 그대로 사용됨
        filename = f"task_{i}_{task.output_type}.py"
        filepath = code_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code.code)

        if verbose:
            print(f"   저장: {filepath}")

        return code

    if parallel:
        # 세마포어로 동시 API 호출 수를 제한하여 rate limit 방지
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def _limited_generate(i, task):
            async with sem:
                return await generate_single(i, task)

        generated_codes = list(
            await asyncio.gather(
                *[_limited_generate(i, task) for i, task in enumerate(plan.tasks, 1)],
                return_exceptions=True,
            )
        )
    else:
        generated_codes = []
        for i, task in enumerate(plan.tasks, 1):
            code = await generate_single(i, task)
            generated_codes.append(code)
            if i < len(plan.tasks):
                await asyncio.sleep(TASK_DELAY)

    # 결과 저장
    temp_dir = Path(output_dir) / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    with open(temp_dir / "step3_codes.json", "w", encoding="utf-8") as f:
        json.dump(
            [c.model_dump() for c in generated_codes], f, ensure_ascii=False, indent=2
        )

    print("\n[Step 3] 완료")
    return generated_codes


# =============================================================================
# Step 4: 코드 실행
# =============================================================================
async def step4_execute_code(
    plan: TaskPlan,
    generated_codes: list[GeneratedCode],
    schema_result: str,
    output_dir: str,
    parallel: bool = False,
    verbose: bool = True,
) -> list[str]:
    """MCP를 통해 생성된 Python 코드를 실행하고 결과를 수집합니다.

    Agent가 코드를 사전 검토(경로, 컬럼명, import 확인)한 뒤 실행하며,
    오류 발생 시 원인을 분석하고 코드를 수정하여 재실행합니다.

    Args:
        plan: 과제 계획 (과제 메타정보 참조용)
        generated_codes: Step 3에서 생성된 코드 객체 리스트
        schema_result: 스키마 분석 결과 (Agent가 코드 검토 시 참조)
        output_dir: 실행 결과를 저장할 상위 디렉터리
        parallel: True면 모든 과제를 동시에 실행
        verbose: True면 진행 상황을 콘솔에 출력

    Returns:
        list[str]: 과제별 실행 결과 텍스트 (성공 시 stdout, 실패 시 에러 메시지)
    """
    print("\n" + "=" * 60)
    print(f"[Step 4] 코드 실행 ({'병렬' if parallel else '순차'} 모드)")
    print("=" * 60)

    code_dir = Path(output_dir) / "code"
    charts_dir = Path(output_dir) / "charts"

    async def execute_single(i: int, task, code) -> str:
        """단일 과제의 코드를 실행합니다 (재시도 포함)."""
        if verbose:
            print(f"\n--- 과제 {i}/{len(plan.tasks)}: {task.title} ---")

        filename = f"task_{i}_{task.output_type}.py"
        filepath = code_dir / filename
        chart_path = charts_dir / task.chart_filename if task.chart_filename else None

        prompt = PROMPTS["execute"].format(
            schema_result=schema_result,
            code_filepath=str(filepath),
            task_info=f"{task.title} - {task.question}",
            output_type=task.output_type,
            chart_save_path=str(chart_path) if chart_path else "해당 없음",
            chart_filename=task.chart_filename or "해당 없음",
        )

        try:
            output_text = await run_with_retry(
                execute_agent, prompt, step_name=f"Step 4-{i}",
                model_settings=STEP_SETTINGS["step_4"],
            )
            if output_text.strip():
                if verbose:
                    print(f"   실행 완료")
                return output_text
            raise ValueError("빈 응답")
        except Exception as e:
            return f"실행 실패: {e}"

    if parallel:
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def _limited_execute(i, task, code):
            async with sem:
                return await execute_single(i, task, code)

        tasks_data = list(
            zip(range(1, len(plan.tasks) + 1), plan.tasks, generated_codes)
        )
        execution_results = list(
            await asyncio.gather(
                *[_limited_execute(i, task, code) for i, task, code in tasks_data],
                return_exceptions=True,
            )
        )
        # 예외가 반환된 경우 문자열로 변환
        execution_results = [
            f"실행 실패: {r}" if isinstance(r, Exception) else r
            for r in execution_results
        ]
    else:
        execution_results = []
        for i, (task, code) in enumerate(zip(plan.tasks, generated_codes), 1):
            result = await execute_single(i, task, code)
            execution_results.append(result)
            if i < len(plan.tasks):
                await asyncio.sleep(TASK_DELAY)

    # 결과 저장
    temp_dir = Path(output_dir) / "_temp"
    separator = "\n" + "=" * 60 + "\n"
    all_results = ""
    for i, result in enumerate(execution_results, 1):
        all_results += f"{separator}[결과 {i}]{separator}{result}\n"

    with open(temp_dir / "step4_results.txt", "w", encoding="utf-8") as f:
        f.write(all_results)

    print("\n[Step 4] 완료")
    return execution_results


# =============================================================================
# Step 5: 보고서 생성
# =============================================================================
async def step5_generate_report(
    plan: TaskPlan,
    execution_results: list[str],
    output_dir: str,
    verbose: bool = True,
) -> Report:
    """모든 과제의 실행 결과를 종합하여 구조화된 보고서를 생성합니다.

    Executive Summary, 핵심 발견사항, 과제별 인사이트, 종합 결론, 제언을 포함하는
    Report 객체를 생성하고, JSON과 마크다운 두 가지 형식으로 저장합니다.

    Args:
        plan: 과제 계획 (보고서에 목표/출처/과제 정보 포함)
        execution_results: Step 4에서 수집된 과제별 실행 결과 텍스트
        output_dir: 보고서 파일을 저장할 디렉터리
        verbose: True면 진행 상황을 콘솔에 출력

    Returns:
        Report: 제목, 요약, 발견사항, 결론 등이 담긴 구조화된 보고서 객체
    """
    print("\n" + "=" * 60)
    print("[Step 5] 보고서 생성")
    print("=" * 60)

    charts_dir = Path(output_dir) / "charts"

    # 과제별 상세 정보 구성 + 차트 이미지 수집
    task_details = ""
    chart_images = []  # BinaryContent 리스트

    for i, (task, result) in enumerate(zip(plan.tasks, execution_results), 1):
        task_details += f"""
## 과제 {i}: {task.title}
- 질문: {task.question}
- 방법: {task.method}
- 출력 유형: {task.output_type}
- 차트 파일: {task.chart_filename or '없음'}

### 실행 결과:
{result}
"""
        # 차트 이미지가 있으면 BinaryContent로 로드
        if task.chart_filename:
            chart_path = charts_dir / task.chart_filename
            if chart_path.exists():
                with open(chart_path, "rb") as f:
                    image_bytes = f.read()
                ext = chart_path.suffix.lower()
                media_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")
                chart_images.append(BinaryContent(data=image_bytes, media_type=media_type))
                if verbose:
                    print(f"   차트 이미지 포함: {task.chart_filename}")

    prompt = PROMPTS["report"].format(
        plan_goal=plan.goal,
        data_source=plan.data_source,
        task_details=task_details,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    # 차트 이미지가 있으면 멀티모달로 전달 [이미지, ..., 텍스트]
    # LLM이 차트를 직접 보고 chart_description을 작성합니다.
    if chart_images:
        prompt += (
            f"\n\n차트 이미지 {len(chart_images)}개가 함께 제공됩니다. "
            "각 차트를 직접 보고 chart_description에 핵심 패턴을 반영하세요."
        )
        user_prompt = chart_images + [prompt]
    else:
        user_prompt = prompt

    report = await run_with_retry(
        report_agent, user_prompt, step_name="Step 5",
        model_settings=STEP_SETTINGS["step_5"],
    )

    # 결과 저장 (JSON)
    temp_dir = Path(output_dir) / "_temp"
    with open(temp_dir / "step5_report.json", "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    # 마크다운 보고서 저장
    save_markdown_report(report, plan, output_dir)

    print("\n[Step 5] 완료")
    return report


# =============================================================================
# 보고서 저장 (마크다운)
# =============================================================================
def save_markdown_report(report: Report, plan: TaskPlan, output_dir: str):
    """Report 객체를 마크다운(.md) 형식의 보고서 파일로 변환하여 저장합니다.

    차트 이미지 링크, 테이블, 인사이트 등을 포함한 사람이 읽을 수 있는
    분석 보고서를 output_dir/analysis_report.md에 저장합니다.

    Args:
        report: Step 5에서 생성된 구조화된 보고서 객체
        plan: 과제 계획 (보고서 헤더에 목표/출처 정보 포함)
        output_dir: 마크다운 파일을 저장할 디렉터리
    """

    md = f"""# {report.title}

> 생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 분석 목표
{plan.goal}

## 데이터 출처
{plan.data_source}

---

## 경영진 요약
{report.executive_summary}

## 주요 발견사항
"""
    for finding in report.key_findings:
        md += f"- {finding}\n"

    if report.key_metrics:
        md += "\n## 핵심 지표\n\n"
        md += "| 지표명 | 값 | 변화 |\n"
        md += "|--------|-----|------|\n"
        for metric in report.key_metrics:
            change = metric.change if metric.change else "-"
            md += f"| {metric.name} | {metric.value} | {change} |\n"

    md += "\n---\n\n## 과제별 분석 결과\n"

    for i, (task, task_result) in enumerate(
        zip(plan.tasks, report.task_results), 1
    ):
        md += f"\n### 과제 {i}: {task.title}\n\n"
        md += f"**질문:** {task.question}\n\n"

        if task_result.chart_filename:
            md += f"![{task.title}](./charts/{task_result.chart_filename})\n\n"
            if task_result.chart_description:
                md += f"*{task_result.chart_description}*\n\n"

        if task_result.table_data:
            md += f"{task_result.table_data}\n\n"

        if task_result.insight:
            md += f"**인사이트:** {task_result.insight}\n"

    # 종합 결론
    md += f"\n---\n\n## 종합 결론\n{report.conclusion}\n"

    # 제언
    md += "\n## 제언\n"
    for i, rec in enumerate(report.recommendations, 1):
        md += f"{i}. {rec}\n"

    if report.appendix:
        md += f"\n---\n\n## 참고사항\n{report.appendix}\n"

    report_path = Path(output_dir) / "analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"보고서 저장: {report_path}")


# =============================================================================
# 파이프라인 실행 (메인 함수)
# =============================================================================
async def run_pipeline(
    data_path: str,
    user_request: str,
    output_dir: str = str(Path(__file__).parent / "outputs"),
    parallel: bool = PARALLEL,
    verbose: bool = VERBOSE,
) -> Report:
    """
    전체 분석 파이프라인을 실행합니다.

    [흐름]
      Step 1 (스키마 분석)
        → Step 2 (과제 정의)
          → Step 3 (코드 생성)
            → Step 4 (코드 실행)
              → Step 5 (보고서 생성)

    Args:
        data_path: 분석할 데이터 파일/폴더 경로
        user_request: 사용자의 분석 요청 (자연어)
        output_dir: 결과 저장 디렉터리
        parallel: True면 과제별 병렬 처리 (rate limit 주의)
        verbose: True면 실행 과정을 상세히 출력

    Returns:
        Report 객체 (구조화된 최종 보고서)
    """
    # 실행별 고유 폴더 생성 (타임스탬프 기반)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = str(Path(output_dir) / run_id)

    print("[시작] PydanticAI 분석 파이프라인")
    print(f"   모델: {MODEL_ID}")
    print(f"   데이터: {data_path}")
    print(f"   요청: {user_request}")
    print(f"   출력: {run_dir}")
    print(f"   모드: {'병렬' if parallel else '순차'}")

    # 출력 디렉터리 생성
    for sub in ["", "_temp", "code", "charts"]:
        (Path(run_dir) / sub).mkdir(parents=True, exist_ok=True)

    # Step 1: 스키마 분석 (MCP 도구 + 구조화된 출력을 하나의 Agent가 처리)
    schema_obj = await step1_analyze_schema(
        data_path, user_request, run_dir, verbose
    )
    schema_for_steps = json.dumps(
        schema_obj.model_dump(), ensure_ascii=False, indent=2
    )
    await asyncio.sleep(STEP_DELAY)

    # Step 2: 과제 정의
    plan = await step2_define_tasks(
        schema_for_steps, user_request, data_path, run_dir, verbose
    )
    await asyncio.sleep(STEP_DELAY)

    # Step 3: 코드 생성
    generated_codes = await step3_generate_code(
        plan, schema_for_steps, run_dir, parallel, verbose
    )
    await asyncio.sleep(STEP_DELAY)

    # Step 4: 코드 실행
    execution_results = await step4_execute_code(
        plan, generated_codes, schema_for_steps, run_dir, parallel, verbose
    )
    await asyncio.sleep(STEP_DELAY)

    # Step 5: 보고서 생성
    report = await step5_generate_report(plan, execution_results, run_dir, verbose)

    print("\n" + "=" * 60)
    print("[완료] 파이프라인 종료")
    print("=" * 60)
    print(f"보고서: {run_dir}/analysis_report.md")
    print(f"코드: {run_dir}/code/")
    print(f"차트: {run_dir}/charts/")

    return report


# =============================================================================
# 메인 실행
# =============================================================================
async def main():
    # 프로젝트 폴더 기준 절대 경로
    DATA_DIR = str(Path(__file__).parent / "data")

    # 예시 1: 관광 데이터 분석 (CSV)
    report = await run_pipeline(
        data_path=f"{DATA_DIR}/tourism_data",
        user_request="한국 관광인 주요 분석",
    )

    # 예시 2: H&M 매출 분석 (CSV)
    # report = await run_pipeline(
    #     data_path=f"{DATA_DIR}/h&m dataset",
    #     user_request="채널/상품군/고객 속성별 매출 특징을 분석해 주세요.",
    # )

    # 예시 3: Chinook 음악 DB 분석 (SQLite)
    # report = await run_pipeline(
    #     data_path=f"{DATA_DIR}/chinook.db",
    #     user_request="장르별/국가별 매출 분석과 고객 구매 패턴을 분석해 주세요.",
    # )

if __name__ == "__main__":
    asyncio.run(main())
