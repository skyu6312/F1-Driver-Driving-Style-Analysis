import pymysql
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os
from dotenv import load_dotenv
import urllib.parse
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler


load_dotenv()

# MySQL 연결 정보 환경 변수 가져오기
db_user = os.getenv("DB_USER")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")


# 1. 꺼내서 불순물 제거 (공백 및 따옴표 제거)
raw_pw = os.getenv('DB_PASSWORD', '')
clean_pw = raw_pw.strip().replace("'", "").replace('"', '')

# 2. 안전하게 포장 (특수문자를 URL용으로 변환)
# (주의: 비밀번호에 띄어쓰기가 있다면 quote_plus 대신 quote를 쓰는 것이 안전합니다)
encoded_pw = urllib.parse.quote(clean_pw)

# 3. 조립
DB_URL = f"mysql+pymysql://{db_user}:{encoded_pw}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DB_URL)

# 💡 [수정 포인트] 본격적인 파이프라인 가동 전, DB 연결을 먼저 테스트합니다.
try:
    with engine.connect() as conn:
        print("✅ MySQL DB 연결 사전 테스트 성공!")
except Exception as e:
    print(f"❌ DB 연결 실패! MySQL 서버가 켜져 있는지, 환경 변수가 맞는지 확인하세요.")
    print(f"상세 에러: {e}")
    exit() # DB 연결이 안 되면 여기서 스크립트를 즉시 중단합니다.


query = """
    SELECT driver, turn_number, apex_speed, braking_jerk, avg_throttle, trail_braking_style 
    FROM driver_style_2025
    WHERE season = 2025;
"""
df = pd.read_sql(query, engine)
# conn.close()  # engine을 사용할 경우 연결을 수동으로 닫을 필요가 없습니다.

print(f"📊 수집된 총 데이터 행 수: {len(df)}개")

# 2. 드라이버별 평균 주행 피처 집계 (드라이버 레벨로 압축)
# 코너별로 흩어진 데이터를 드라이버 한 명의 '평균 주행 성향'으로 묶어줍니다.
driver_profiles = df.groupby('driver').agg({
    'apex_speed': 'mean',
    'braking_jerk': 'mean',
    'avg_throttle': 'mean',
    'trail_braking_style': 'mean' # 0과 1 사이의 '트레일 브레이킹 구사 빈도(비율)'가 됩니다.
}).reset_index()

# 머신러닝 학습에 사용할 핵심 피처 선택
features = ['apex_speed', 'braking_jerk', 'avg_throttle', 'trail_braking_style']
X = driver_profiles[features]

# 3. [중요] 피처 스케일링 (표준화)
# 단위 차이로 인해 특정 피처가 모델을 왜곡하는 것을 방지합니다.
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. K-Means 클러스터링 수행 (그룹 수는 가장 전형적인 3개 그룹으로 설정)
# 성향을 더 찢어보고 싶다면 n_clusters를 4나 5로 바꾸셔도 됩니다.
K = 3
kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
driver_profiles['cluster'] = kmeans.fit_predict(X_scaled)

# 5. 분석 결과 리포트 출력
print("\n🏁 [드라이버별 군집 매핑 결과]")
print(driver_profiles[['driver', 'cluster']].sort_values(by='cluster').to_string(index=False))

# 각 군집(그룹)의 피처별 평균값을 봅니다. 이 숫자가 그룹의 '성향'을 정의합니다.
cluster_summary = driver_profiles.groupby('cluster')[features].mean()
print("\n📊 [군집별 주행 스타일 프로필 분석]")
print(cluster_summary)

# 6. 결과 시각화 (산점도 그래프)
# 가장 변별력이 큰 '코너 에이펙스 속도'와 '트레일 브레이킹 구사 빈도'를 축으로 그립니다.
plt.figure(figsize=(10, 7))
sns.scatterplot(
    x='apex_speed', 
    y='trail_braking_style', 
    hue='cluster', 
    data=driver_profiles, 
    palette='Set1', 
    s=200, 
    edgecolor='black'
)

# 그래프에 드라이버 이름 표기
for i in range(len(driver_profiles)):
    plt.text(
        driver_profiles['apex_speed'].iloc[i] + 0.2, 
        driver_profiles['trail_braking_style'].iloc[i], 
        driver_profiles['driver'].iloc[i], 
        fontsize=11, 
        weight='bold'
    )

plt.title('F1 Driver Driving Style Clustering (2025)', fontsize=16, weight='bold')
plt.xlabel('Average Apex Speed (km/h)', fontsize=12)
plt.ylabel('Trail Braking Ratio (0 ~ 1)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.show()



# 1. 시각화를 위해 군집별 평균 데이터 추출 (0~1로 스케일 통일)
# 레이더 차트는 각 축의 단위가 같아야 하므로, 군집별 평균치를 MinMaxScaler로 0~1 사이로 변환합니다.
cluster_features = driver_profiles.groupby('cluster')[features].mean()

scaler = StandardScaler()
scaled_array = scaler.fit_transform(cluster_features)

min_val = scaled_array.min()
max_val = scaled_array.max()
scaled_data = (scaled_array - min_val) / (max_val - min_val) + 0.1

cluster_scaled = pd.DataFrame(
    scaled_data, 
    columns=['Apex Speed', 'Braking Jerk', 'Avg Throttle', 'Trail Braking Ratio'],
    index=cluster_features.index
)

# 2. 레이더 차트 (Radar Chart) 그리기 세팅
labels = cluster_scaled.columns.tolist()
num_vars = len(labels)

# 방사형 그래프는 처음과 끝이 연결되어야 하므로 원을 닫아줍니다.
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

# 군집별 색상 및 이름 매핑
colors = {0: 'red', 1: 'blue', 2: 'green'}
cluster_names = {
    0: "Cluster 0: High-Speed Apex Attacker",
    1: "Cluster 1: Trail-Braking Master",
    2: "Cluster 2: Balanced Geometric Operator"
}

# 3. 각 군집의 주행 DNA 선 그리기
for cluster_id in cluster_scaled.index:
    values = cluster_scaled.loc[cluster_id].tolist()
    values += values[:1] # 원 닫기
    
    # 선 그리기
    ax.plot(angles, values, color=colors[cluster_id], linewidth=2, label=cluster_names[cluster_id])
    # 영역 채우기
    ax.fill(angles, values, color=colors[cluster_id], alpha=0.15)

# 4. 그래프 디테일 세팅
ax.set_theta_offset(np.pi / 2) # 시작점을 12시 방향으로
ax.set_theta_direction(-1)     # 시계 방향으로 회전

# 축 레이블 배치
plt.xticks(angles[:-1], labels, fontsize=12, weight='bold')
ax.set_rscale('linear')
plt.ylim(0, 1.1)

plt.title('F1 Driving Style DNA - 4D Cluster Profile', fontsize=16, weight='bold', pad=30)
plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
plt.tight_layout()
plt.show()