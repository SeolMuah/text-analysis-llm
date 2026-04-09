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
transactions = pd.read_csv('./data/h&m dataset/transactions_hm.csv')
articles = pd.read_csv('./data/h&m dataset/articles_hm.csv')

# 데이터 조인
df = pd.merge(transactions, articles, on='article_id')

# 상품군별 매출 합계 계산
product_group_sales = df.groupby('product_group_name')['price'].sum().sort_values(ascending=False)

# 전체 매출 대비 비중 계산
total_sales = product_group_sales.sum()
product_group_share = (product_group_sales / total_sales) * 100

# 상위 10개 상품군 선정
top_10_sales = product_group_sales.head(10)
top_10_share = product_group_share.head(10)

# 결과 출력
print("상품군별 매출 성과 (상위 10개):")
for group, sales in top_10_sales.items():
    print(f"- {group}: {sales:,.2f} (비중: {top_10_share[group]:.2f}%)")

# 시각화
plt.figure(figsize=(12, 6))
top_10_sales.plot(kind='bar', color='skyblue')
plt.title('상품군별 매출 상위 10개')
plt.xlabel('상품군')
plt.ylabel('매출 합계')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', linestyle='--', alpha=0.7)

# 차트 저장
CHART_SAVE_PATH = "outputs\\20260409_173756\\charts/product_group_sales.png"
plt.savefig(CHART_SAVE_PATH, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
