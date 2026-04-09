import pandas as pd

# 데이터 로드
transactions = pd.read_csv('./data/h&m dataset/transactions_hm.csv')
customers = pd.read_csv('./data/h&m dataset/customer_hm.csv')

# 데이터 조인
df = pd.merge(transactions, customers, on='customer_id', how='inner')

# 연령대 그룹화 (10세 단위)
df['age_group'] = (df['age'] // 10) * 10
df['age_group'] = df['age_group'].astype(str) + '대'

# 매출 합계 및 평균 구매 금액 계산
grouped = df.groupby(['age_group', 'club_member_status'])['price'].agg(['sum', 'mean']).reset_index()
grouped.columns = ['연령대', '멤버십 상태', '매출 합계', '평균 구매 금액']

# 전체 평균 매출 계산
total_avg_sales = grouped['매출 합계'].mean()

# 전체 평균 대비 매출 변화율 계산
grouped['전체 평균 대비 매출 변화율(%)'] = ((grouped['매출 합계'] - total_avg_sales) / total_avg_sales) * 100

# 결과 출력
print("--- 고객 속성(연령대, 멤버십)별 매출 특징 분석 ---")
print(grouped.to_string(index=False))

# 주요 특징 요약 출력
print("\n--- 주요 분석 결과 ---")
max_sales_group = grouped.loc[grouped['매출 합계'].idxmax()]
print(f"가장 높은 매출을 기록한 그룹: {max_sales_group['연령대']} / {max_sales_group['멤버십 상태']} "
      f"(매출 합계: {max_sales_group['매출 합계']:.2f})")

min_sales_group = grouped.loc[grouped['매출 합계'].idxmin()]
print(f"가장 낮은 매출을 기록한 그룹: {min_sales_group['연령대']} / {min_sales_group['멤버십 상태']} "
      f"(매출 합계: {min_sales_group['매출 합계']:.2f})")
