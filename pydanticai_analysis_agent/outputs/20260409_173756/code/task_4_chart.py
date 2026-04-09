import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import os

# 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
transactions = pd.read_csv('./data/h&m dataset/transactions_hm.csv')
articles = pd.read_csv('./data/h&m dataset/articles_hm.csv')

# 데이터 조인
df = pd.merge(transactions, articles, on='article_id', how='inner')

# 교차 집계: 채널별 상품군 매출 합계
pivot_df = df.pivot_table(
    index='sales_channel_id',
    columns='product_group_name',
    values='price',
    aggfunc='sum'
)

# 채널별 상품군 매출 비중 계산 (행 기준 정규화)
pivot_norm = pivot_df.div(pivot_df.sum(axis=1), axis=0)

# 히트맵 시각화
plt.figure(figsize=(14, 8))
sns.heatmap(pivot_norm, annot=True, fmt='.2f', cmap='YlGnBu')
plt.title('판매 채널별 상품군 매출 비중 히트맵')
plt.xlabel('상품군')
plt.ylabel('판매 채널 ID')

# 차트 저장
CHART_SAVE_PATH = "outputs/20260409_173756/charts/channel_product_heatmap.png"
os.makedirs(os.path.dirname(CHART_SAVE_PATH), exist_ok=True)
plt.savefig(CHART_SAVE_PATH, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

# 분석 결과 출력
print("--- 채널별 상품군 매출 비중 분석 결과 ---")
for channel in pivot_norm.index:
    top_products = pivot_norm.loc[channel].sort_values(ascending=False).head(3)
    print(f"\n판매 채널 {channel}의 핵심 상품군 (매출 비중 상위 3개):")
    print(top_products)
