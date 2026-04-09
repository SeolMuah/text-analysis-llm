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

# 데이터 로드
file_paths = [
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\미국_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\일본_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\중국_202001_202301.csv'
]

df_list = [pd.read_csv(f) for f in file_paths]
df = pd.concat(df_list, ignore_index=True)

# 날짜 형식 변환
df['날짜'] = pd.to_datetime(df['날짜'], format='%Y%m')

# 시각화
plt.figure(figsize=(12, 6))
for country in df['국가명'].unique():
    subset = df[df['국가명'] == country]
    plt.plot(subset['날짜'], subset['관광객수'], label=country)

plt.title('국가별 월별 관광객 수 추이')
plt.xlabel('날짜')
plt.ylabel('관광객수')
plt.legend()
plt.grid(True)

# 차트 저장
CHART_SAVE_PATH = r"C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\outputs\20260409_181242\charts/country_comparison.png"
plt.savefig(CHART_SAVE_PATH, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

# 통계 분석 및 출력
stats = df.groupby('국가명')['관광객수'].agg(['mean', 'max', 'min'])
print("국가별 관광객 통계 (평균, 최대, 최소):")
print(stats)
