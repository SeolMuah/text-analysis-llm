import pandas as pd

# 데이터 로드
file_path = './data/h&m dataset/transactions_hm.csv'
df = pd.read_csv(file_path)

# 전체 매출 지표 계산
total_revenue = df['price'].sum()
avg_revenue = df['price'].mean()
max_revenue = df['price'].max()
min_revenue = df['price'].min()

# 채널별 매출 집계
channel_revenue = df.groupby('sales_channel_id')['price'].sum()
total_sum = channel_revenue.sum()
channel_share = (channel_revenue / total_sum) * 100

# 결과 출력
print("--- 전체 매출 현황 ---")
print(f"전체 매출 합계: {total_revenue:.2f}")
print(f"평균 매출: {avg_revenue:.2f}")
print(f"최대 매출: {max_revenue:.2f}")
print(f"최소 매출: {min_revenue:.2f}")
print("\n--- 판매 채널별 매출 비중 ---")
for channel_id, revenue in channel_revenue.items():
    share = channel_share[channel_id]
    print(f"채널 {channel_id}: 매출 {revenue:.2f} (비중 {share:.2f}%)")
