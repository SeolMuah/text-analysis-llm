import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import platform

# 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 파일 경로
file_paths = [
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\미국_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\일본_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\중국_202001_202301.csv'
]

# 1. 데이터 로드 및 병합
dfs = [pd.read_csv(f) for f in file_paths]
df = pd.concat(dfs)

# '날짜' 컬럼을 datetime 형식으로 변환
df['날짜'] = pd.to_datetime(df['날짜'], format='%Y%m')

# 2. 월별 전체 관광객 합계 계산
monthly_total = df.groupby('날짜')['관광객수'].sum().reset_index()

# 3. 추세 시각화
plt.figure(figsize=(12, 6))
plt.plot(monthly_total['날짜'], monthly_total['관광객수'], marker='o', linestyle='-', color='b')
plt.title('2020-2023년 미국, 일본, 중국 관광객 월별 추세')
plt.xlabel('날짜')
plt.ylabel('전체 관광객 수')
plt.grid(True)

# 차트 저장
CHART_SAVE_PATH = r"C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\outputs\20260409_181242\charts/total_tourism_trend.png"
plt.savefig(CHART_SAVE_PATH, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

# 4. 결과 출력
total_visitors = monthly_total['관광객수'].sum()
mean_visitors = monthly_total['관광객수'].mean()

print(f"기간 내 총 관광객 수: {total_visitors}")
print(f"월평균 관광객 수: {mean_visitors:.2f}")
