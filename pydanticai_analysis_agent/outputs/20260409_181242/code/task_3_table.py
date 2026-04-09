import pandas as pd

# 데이터 파일 경로
file_paths = [
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\미국_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\일본_202001_202301.csv',
    r'C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data\중국_202001_202301.csv'
]

# 데이터 로드 및 병합
dfs = [pd.read_csv(f) for f in file_paths]
df = pd.concat(dfs)

# 날짜 형식 변환 (int64 -> datetime)
df['날짜'] = pd.to_datetime(df['날짜'], format='%Y%m')

# 국가별로 정렬
df = df.sort_values(['국가명', '날짜'])

# 전월 대비 변화율 계산
df['변화율'] = df.groupby('국가명')['관광객수'].pct_change() * 100

# 결과 분석
results = []
for country in df['국가명'].unique():
    country_data = df[df['국가명'] == country].dropna()
    avg_change = country_data['변화율'].mean()
    max_change_row = country_data.loc[country_data['변화율'].idxmax()]
    
    results.append({
        '국가명': country,
        '평균 변화율(%)': round(avg_change, 2),
        '최대 변화율(%)': round(max_change_row['변화율'], 2),
        '최대 변화율 시점': max_change_row['날짜'].strftime('%Y-%m')
    })

# 결과 출력
result_df = pd.DataFrame(results)
print("국가별 관광객 변화율 분석 결과:")
print(result_df.to_string(index=False))
