# 🏎️ F1 Telemetry Insights: 4D Driver Driving Style Clustering Engine

> **FastF1 원시 시계열 텔레메트리 데이터를 정제하여 드라이버별 주행 DNA(제동 거칠기, 트레일 브레이킹 궤적, 탈출 과감도)를 정량화하고 머신러닝(K-Means) 기반으로 성향을 자동 분류하는 데이터 파이프라인 프로젝트입니다.**

---

## 📌 Project Overview
본 프로젝트는 중계화면이나 단순 랩타임 뒤에 숨겨진 F1 드라이버들의 고유한 주행 스타일을 차량 운동학(Vehicle Dynamics) 관점에서 분석합니다. FastF1 API를 통해 수집한 고밀도 센서 틱 데이터를 엔지니어링하여 전처리하고, MySQL 데이터베이스에 적재한 뒤, 4차원 물리 피처 공간에서 머신러닝 클러스터링을 수행합니다.

### 🛠 Tech Stacks
* **Language:** Python 3.x
* **Data Library:** FastF1, Pandas, NumPy, Scikit-learn
* **Database:** MySQL (PyMySQL)
* **Visualization:** Matplotlib, Seaborn

---

## 🚀 Key Data Pipeline Architecture

### 1. Spatial Telemetry Filtering & Ingestion
* 각 서킷의 코너별 에이펙스(Apex) 좌표를 기준으로 **반경 150m 이내의 고밀도 공간 데이터**만 정밀 컷오프하여 시계열 데이터프레임을 생성합니다.
* 중복 및 데이터 누락 방지를 위해 인프라 수준에서 `if_exists='replace'` 세탁 후 `append` 모드로 전환하는 이중 적재 세팅을 구현했습니다.

### 2. Physical Feature Engineering & Core Algorithm
드라이버의 성향을 정의하기 위해 원시 센서 채널을 조합하여 4가지 핵심 인디케이터를 추출했습니다.

* **Apex Speed (km/h):** 코너 중심부에서의 최저 페이스 기록
* **Braking Jerk (G/s):** 진입 초기 브레이크 페달 가압 변화율의 최댓값을 통한 제동 거칠기 측정
* **Avg Throttle (%):** 에이펙스 통과 후 가속 페달 개입도를 통한 탈출 과감성 산출
* **Trail Braking Style (0 or 1):** 본 프로젝트의 핵심 알고리즘입니다.

#### 💡 트레일 브레이킹 판별 알고리즘 디버깅 서사
대중에게 공개되지 않는 조향각 센서(`SteeringWhlAngle`)의 부재와 초기 틱 데이터 포화(Data Saturation)로 인해 모든 드라이버가 0% 또는 100%로 쏠리는 버그를 직면했습니다. 이를 해결하기 위해 **"코너 진입부터 에이펙스까지의 통일된 제동 구간 윈도우"**를 정의하고, **"후반 50% 감압 페이즈에서의 제동 유지 비율이 40%를 넘는가"**에 대한 통계적 컷오프(Cut-off) 및 최소 제동 틱수 필터(>15 틱)를 구축하여 물리적 변별력을 확보하는 데 성공했습니다.

---

## 📊 Analytics & Machine Learning Results

4차원 공간(`Apex Speed`, `Braking Jerk`, `Avg Throttle`, `Trail Braking Ratio`) 상에서 **StandardScaler 정규화**를 거친 뒤, **K-Means 클러스터링(K=3)**을 수행한 최종 결과입니다.

### 1. 드라이버별 주행 성향 클러스터 맵
![Driving Style Scatter Plot](./clustering_result.png) 
*※ 본인의 저장소에 올린 산점도 이미지 경로로 수정하세요.*

* **Cluster 0 (Red) - High-Speed Apex Attacker:** 직선에서 제동을 빠르게 끝내고 에이펙스 속도를 극대화하며, 탈출 시 가속 페달을 과감하게 전개하는 스타일 (예: VER, NOR, LEC)
* **Cluster 1 (Blue) - Trail-Braking Master:** 코너 깊숙한 곳까지 브레이크 유압을 정밀하게 제어하며 전륜 접지력을 극대화하는 클래식 스타일 (예: HAM, SAI)
* **Cluster 2 (Green) - Balanced Geometric Operator:** 강력한 초기 제동 거칠기(Braking Jerk)를 활용해 하중을 던진 후, 정석적인 레이싱 라인을 그리는 베테랑 스타일 (예: ALO, HUL)

### 2. 4D Cluster Profile 레이더 차트
![4D Radar Chart](./final_lador_result.png)
*※ 본인의 저장소에 올린 레이더 차트 이미지 경로로 수정하세요.*

MinMaxScaler의 특이치 왜곡으로 인해 실선으로 찌그러지던 방사형 차트를 모델 계산 스케일과 정렬된 **상대적 표준화 비율 변환 로직**으로 리팩토링하여, 차량 역학적 트레이드오프(종방향 제동력 vs 횡방향 조향력) 관계를 시각적으로 완벽하게 증명해 냈습니다.

---

## 📂 Project Structure
```text
├── spatial_pipeline.py     # MySQL 데이터 수집 및 전처리 마스터 파이프라인
├── test_logic.py           # 단일 코너 물리 알고리즘 검증용 샌드박스 스크립트
├── driver_clustering.py    # SK-learn 기반 K-Means 모델링 및 4D 시각화 코드
├── f1_cache/               # FastF1 데이터 로컬 캐시 디렉토리
└── README.md               # 프로젝트 리포트
