import fastf1
import pandas as pd
import numpy as np

# 1. 캐시 설정 및 고속 로딩
fastf1.Cache.enable_cache('f1_cache')

print("🏎️ [Test] 2025시즌 원시 데이터 로딩 중...")
session = fastf1.get_session(2025, 1, 'Q') 
session.load(telemetry=True, laps=True)
circuit_info = session.get_circuit_info()

# 타겟 설정: 베르스타펜(VER)의 가장 빠른 랩, Turn 1
DRIVER = 'VER'
TURN_NUM = 1 

lap = session.laps.pick_driver(DRIVER).pick_fastest()
tel = lap.get_telemetry()

# [공간 처리] 해당 코너 번호 매핑 및 반경 150m 데이터 슬라이싱
corners_df = circuit_info.corners
turn_data = corners_df[corners_df['Number'].astype(str) == str(TURN_NUM)]

if turn_data.empty:
    turn_data = corners_df.iloc[0]

c_x, c_y = turn_data['X'].values[0], turn_data['Y'].values[0]
distance_from_apex = np.sqrt((tel['X'] - c_x)**2 + (tel['Y'] - c_y)**2)

# 코너 구간 잘라내기 후 인덱스를 깨끗하게 리셋 (KeyError 완전 차단)
corner_telemetry = tel[distance_from_apex < 150000].copy().reset_index(drop=True)

print(f"\n🎯 [Test] {DRIVER}의 Turn {TURN_NUM} ({len(corner_telemetry)}개 틱) 순수 물리 데이터 연산 시작")

# =============================================================================
# 2. [실무 정석] 스티어링 센서 우회형 트레일 브레이킹 연산 메커니즘
# =============================================================================
if len(corner_telemetry) > 5:
    # 5개 포인트 이동평균으로 센서 노이즈 스무딩 처리
    win_size = min(5, len(corner_telemetry))
    corner_telemetry['Brake_Smooth'] = corner_telemetry['Brake'].rolling(window=win_size, center=True).mean().fillna(corner_telemetry['Brake'])
    
    # 💥 핵심: 코너 구간 내에서 '속도가 줄어드는 진짜 감속 페이즈'를 찾습니다.
    corner_telemetry['Speed_Diff'] = corner_telemetry['Speed'].diff()
    cond_deceleration = corner_telemetry['Speed_Diff'] < 0
    
    # 이 감속이 일어나는 순간들 중에 '브레이크 스위치가 On(True)' 상태였던 행들을 추적합니다.
    decel_phase = corner_telemetry[cond_deceleration]
    
    total_brake_points = (decel_phase['Brake'] == True).sum()
    
    # ------------------ [수정] 분모/분자 구간 통일 디버깅 ------------------

    # [기준 구간 통일] 코너 시작점부터 에이펙스(최저속도점)까지만 정밀 타겟팅합니다.
    apex_idx = corner_telemetry['Speed'].idxmin()
    entry_to_apex = corner_telemetry.loc[:apex_idx]

    # 분모: 에이펙스에 도달하기 전까지 '브레이크를 밟았던 총 틱 수'
    total_brake_points = (entry_to_apex['Brake'] == True).sum()

    # 분자: 에이펙스 직전 마무리에 해당하는 후반부 윈도우 (예: 후반 50% 구간)에서 '브레이크를 유지한 틱 수'
    # 핸들을 완전히 꺾고 들어가는 에이펙스 직전 후반부 틱만 쏙 뽑아냅니다.
    half_way = len(entry_to_apex) // 2
    trail_points = (entry_to_apex.iloc[half_way:]['Brake'] == True).sum()

    # 비율 계산
    ratio = (trail_points / total_brake_points) if total_brake_points > 0 else 0
    final_result = 1 if ratio > 0.4 else 0 # 구간을 좁혔으니 컷오프를 40% 정도로 조정하면 변별력이 좋아집니다.

# --------------------------------=====================================

    # -------------------------------------------------------------------------
    # 3. 콘솔 출력 리포트 (눈으로 직접 결과 확인)
    # -------------------------------------------------------------------------
    print("\n==================================================")
    print(f"🏁 [독립 테스트 리포트] {DRIVER} - Turn {TURN_NUM}")
    print(f" - 코너 진입 총 제동 센서 틱(Tick): {total_brake_points}개")
    print(f" - 에이펙스 직전 제동 유지 틱:     {trail_points}개")
    print(f" - 트레일 브레이킹 유효 비율:       {ratio * 100:.2f}%")
    print(f" - 최종 0 / 1 스타일 판정 결과:    {'✅ 1 (트레일 적극 활용형)' if final_result == 1 else '❌ 0 (직선 위주 제동형)'}")
    print("==================================================\n")
else:
    print("데이터 포인트가 부족하여 연산할 수 없습니다.")