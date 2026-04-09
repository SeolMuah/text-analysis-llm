# =============================================================================
# models.py - 파이프라인 스키마 정의 (PydanticAI용)
# =============================================================================
# PydanticAI의 output_type으로 사용되는 Pydantic 스키마입니다.
# Enum 대신 Literal을 사용하여 PydanticAI 호환성을 높였습니다.
#
# 사용 단계:
#   - Step 1: SchemaAnalysisResult (스키마 분석 결과)
#   - Step 2: TaskPlan (분석 과제 계획)
#   - Step 3: GeneratedCode (생성된 Python 코드)
#   - Step 5: Report (최종 보고서)
# =============================================================================

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# =============================================================================
# 공통 타입
# =============================================================================

OutputType = Literal["chart", "table", "metric", "text"]
DataQuality = Literal["good", "fair", "poor"]


# =============================================================================
# Step 1: 스키마 분석 결과
# =============================================================================

class ColumnInfo(BaseModel):
    """개별 컬럼 정보"""
    name: str = Field(description="컬럼명 (원본 그대로)", min_length=1, max_length=200)
    dtype: str = Field(description="데이터타입 (int64, float64, object, datetime64 등)", min_length=1, max_length=50)
    null_count: int = Field(description="결측치/NULL 개수", ge=0)
    unique_count: int = Field(description="고유값 개수", ge=0)
    is_categorical: bool = Field(description="범주형 여부 (unique <= 20이면 True)")
    categorical_values: Optional[List[str]] = Field(
        default=None,
        description="범주형인 경우 고유값 목록 (최대 20개)",
    )
    sample_values: List[str] = Field(
        default_factory=list,
        description="샘플값 (최대 5개)",
        max_length=5,
    )


class DataSourceSchema(BaseModel):
    """개별 파일/테이블 스키마"""
    source_name: str = Field(description="파일명 또는 테이블명", min_length=1, max_length=200)
    source_path: str = Field(description="전체 경로", min_length=1)
    source_type: str = Field(description="소스 유형 (csv, xlsx, json, parquet, sqlite 등)", min_length=1, max_length=20)
    row_count: int = Field(description="행 수", ge=0)
    column_count: int = Field(description="컬럼 수", ge=1)
    columns: List[ColumnInfo] = Field(description="모든 컬럼 정보", min_length=1)
    categorical_columns: List[str] = Field(default_factory=list, description="범주형 컬럼명 목록")
    numeric_columns: List[str] = Field(default_factory=list, description="수치형 컬럼명 목록")
    datetime_columns: List[str] = Field(default_factory=list, description="날짜/시간 컬럼명 목록")


class DataRelation(BaseModel):
    """파일/테이블 간 관계"""
    source1: str = Field(description="첫 번째 소스명", min_length=1)
    source2: str = Field(description="두 번째 소스명", min_length=1)
    join_keys: List[str] = Field(description="조인 가능한 공통 컬럼명", min_length=1)
    relation_type: str = Field(description="관계 유형 (1:1, 1:N, N:M, unknown)", min_length=1, max_length=10)


class SchemaAnalysisResult(BaseModel):
    """1단계 스키마 분석 전체 결과"""
    user_request: str = Field(description="사용자 분석 요청", min_length=1)
    data_path: str = Field(description="분석한 데이터 경로", min_length=1)
    source_count: int = Field(description="발견된 데이터 소스 개수", ge=1)
    sources: List[DataSourceSchema] = Field(description="각 데이터 소스별 스키마", min_length=1)
    relations: Optional[List[DataRelation]] = Field(
        default=None,
        description="데이터 소스 간 관계 (여러 소스인 경우)",
    )
    overall_quality: DataQuality = Field(description="전반적 데이터 품질")
    quality_issues: Optional[List[str]] = Field(
        default=None, description="품질 이슈"
    )


# =============================================================================
# Step 2: 분석 과제 정의 (TaskPlan)
# =============================================================================

class Task(BaseModel):
    """개별 분석 과제"""
    number: int = Field(description="과제 번호 (1, 2, 3, ...)", ge=1)
    title: str = Field(description="과제 제목", min_length=2, max_length=100)
    question: str = Field(description="답하고자 하는 구체적 질문", min_length=5, max_length=500)
    data_files: List[str] = Field(description="사용할 데이터 파일 경로 목록", min_length=1)
    method: str = Field(description="분석 방법 설명", min_length=5, max_length=500)
    output_type: OutputType = Field(description="출력 형태: chart, table, metric, text")
    chart_filename: Optional[str] = Field(
        default=None,
        description="차트 파일명 (output_type이 chart인 경우만, 예: monthly_sales.png)",
        max_length=100,
    )


class TaskPlan(BaseModel):
    """분석 계획 (Step 2 출력)"""
    goal: str = Field(description="분석 목표 (1-2문장)", min_length=10, max_length=500)
    data_source: str = Field(description="데이터 출처 설명", min_length=5, max_length=500)
    tasks: List[Task] = Field(
        description="분석 과제 목록 (3-5개)", min_length=1, max_length=10
    )


# =============================================================================
# Step 3: 코드 생성 (GeneratedCode)
# =============================================================================

class GeneratedCode(BaseModel):
    """생성된 Python 코드 (Step 3 출력)"""
    task_number: int = Field(description="과제 번호", ge=1)
    task_title: str = Field(description="과제 제목", min_length=2, max_length=100)
    code: str = Field(description="실행 가능한 Python 코드 전체", min_length=10)
    description: str = Field(description="코드 설명 (1-2문장)", min_length=5, max_length=300)
    chart_filename: Optional[str] = Field(
        default=None, description="생성될 차트 파일명", max_length=100
    )


# =============================================================================
# Step 5: 보고서 생성 (Report)
# =============================================================================

class KeyMetric(BaseModel):
    """핵심 지표"""
    name: str = Field(description="지표명", min_length=1, max_length=100)
    value: str = Field(description="지표값 (단위 포함)", min_length=1, max_length=100)
    change: Optional[str] = Field(
        default=None, description="변화율 (있는 경우만)", max_length=50
    )


class TaskResult(BaseModel):
    """과제별 분석 결과"""
    task_number: int = Field(description="과제 번호", ge=1)
    task_title: str = Field(description="과제 제목", min_length=2, max_length=100)
    chart_filename: Optional[str] = Field(
        default=None, description="차트 파일명", max_length=100
    )
    chart_description: Optional[str] = Field(
        default=None,
        description="차트 핵심 패턴 (1-2문장)",
        max_length=500,
    )
    table_data: Optional[str] = Field(
        default=None,
        description="마크다운 표 형식 데이터",
        max_length=5000,
    )
    insight: str = Field(
        description="핵심 인사이트 (1-2문장)",
        min_length=10, max_length=500,
    )


class Report(BaseModel):
    """최종 분석 보고서 (Step 5 출력)"""
    title: str = Field(
        description="보고서 제목",
        min_length=5, max_length=100,
    )
    executive_summary: str = Field(
        description="경영진 요약 (배경 + 핵심 결론 + 시사점, 3-5문장)",
        min_length=20, max_length=2000,
    )
    key_findings: List[str] = Field(
        description="핵심 발견사항 (수치 포함, 3-5개)",
        min_length=2, max_length=7,
    )
    key_metrics: Optional[List[KeyMetric]] = Field(
        default=None, description="핵심 지표"
    )
    task_results: List[TaskResult] = Field(
        description="과제별 분석 결과", min_length=1
    )
    conclusion: str = Field(
        description="종합 결론 (전체 분석을 관통하는 핵심 메시지, 2-3문장)",
        min_length=10, max_length=1000,
    )
    recommendations: List[str] = Field(
        description="제언 (데이터 근거 기반 구체적 액션 아이템, 2-4개)",
        min_length=2, max_length=5,
    )
    appendix: Optional[str] = Field(
        default=None, description="참고사항 (분석 한계, 향후 제안 등)", max_length=3000
    )
