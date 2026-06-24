import os
import fastf1
import pandas as pd
import numpy as np
import traceback
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine

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

# 2. FastF1 캐시 설정
f1_cache_dir = 'f1_cache'
if not os.path.exists(f1_cache_dir):
    os.makedirs(f1_cache_dir)

fastf1.Cache.enable_cache(f1_cache_dir)

# 3. 데이터 추출 파이프라인
drivers = ['VER', 'HAM', 'LEC', 'NOR', 'ALO', 'PER', 'SAI', 'RUS', 'GAS', 'OCO', 'PIA', 'STR', 'ALB', 'HUL', 'LAW']
TOTAL_ROUNDS = 24



print("🛰️ [실무 레벨] 서킷 좌표 및 공식 Turn 매핑 파이프라인 기동...")

for round_num in range(1, TOTAL_ROUNDS + 1):
    try:
        session = fastf1.get_session(2025, round_num, 'Q')
        session.load(telemetry=True, laps=True)
        circuit_name = session.event['EventName']
        
        try:
            circuit_info = session.get_circuit_info()
            corners = circuit_info.corners
        except Exception:
            print(f"⚠️ Round {round_num} 서킷 맵 데이터 공간 정보 없음. 패스합니다.")
            continue
            
        print(f"\n🗺️ [Round {round_num}] {circuit_name} - 공간 좌표 연산 시작...")
        spatial_features = []
        
        for driver in drivers:
            try:
                # 해당 드라이버의 가장 빠른 랩 추출
                fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                if pd.isna(fastest_lap['LapTime']):
                    continue # 기록이 없는 경우 패스
                    
                tel = fastest_lap.get_telemetry() 
                
                # 가속도 및 Jerk 계산
                tel['Time_Sec'] = tel['Time'].dt.total_seconds()
                tel['Velocity_MS'] = tel['Speed'] / 3.6
                tel['Accel'] = tel['Velocity_MS'].diff() / tel['Time_Sec'].diff()
                tel['Jerk'] = tel['Accel'].diff() / tel['Time_Sec'].diff()
                tel = tel.dropna().replace([np.inf, -np.inf], 0)
                
                for _, corner in corners.iterrows():
                    turn_num = corner['Number']
                    c_x, c_y = corner['X'], corner['Y']
                    
                    # [수정 1] FastF1 좌표계 단위에 맞춘 코너 반경 설정 (약 250m)
                    distance_from_apex = np.sqrt((tel['X'] - c_x)**2 + (tel['Y'] - c_y)**2)
                    corner_telemetry = tel[distance_from_apex < 2500].copy().reset_index(drop=True)
                    
                    if len(corner_telemetry) > 10:
                        # 1. 코너 내 에이펙스(최저 속도) 지점 인덱스 찾기
                        apex_idx = corner_telemetry['Speed'].idxmin()
                        
                        # 2. 코너 진입 ~ 에이펙스 구간 슬라이싱
                        entry_to_apex = corner_telemetry.loc[:apex_idx]
                        
                        trail_braking_style = 0 
                        
                        # 브레이크가 0보다 큰(밟힌) 데이터만 추출
                        braking_points = entry_to_apex[entry_to_apex['Brake'] > 0]
                        total_brake_ticks = len(braking_points)
                        
                        # [수정 2] 의미 있는 헤비 브레이킹 구간(최소 15틱 이상 제동)인지 확인
                        if total_brake_ticks > 15:
                            # 제동 시작 인덱스
                            brake_start_idx = braking_points.index[0]
                            
                            # 제동 전체 구간 (시작점 ~ 에이펙스)
                            braking_phase_length = apex_idx - brake_start_idx
                            
                            # [핵심] 스티어링 턴인이 시작되는 시점을 제동 구간의 60% 지점으로 추정
                            turn_in_idx = brake_start_idx + int(braking_phase_length * 0.6)
                            
                            # 트레일 브레이킹(조향+제동) 구간 추출 (턴인 시점 ~ 에이펙스)
                            trail_phase = corner_telemetry.loc[turn_in_idx:apex_idx]
                            trail_brake_ticks = (trail_phase['Brake'] > 0).sum()
                            
                            # 에이펙스 근접 구간에서 브레이크를 유지한 비율 계산
                            ratio = trail_brake_ticks / len(trail_phase) if len(trail_phase) > 0 else 0
                            
                            # 후반부 구간의 30% 이상 브레이크를 유지했다면 트레일 브레이킹으로 간주
                            if ratio > 0.3:
                                trail_braking_style = 1

                        apex_speed = corner_telemetry.loc[apex_idx, 'Speed']
                        max_jerk = corner_telemetry['Jerk'].abs().max()
                        avg_throttle = corner_telemetry['Throttle'].mean()

                        spatial_features.append({
                            'season': 2025,
                            'round': round_num,
                            'circuit': circuit_name,
                            'driver': driver,
                            'turn_number': int(turn_num),
                            'apex_speed': float(apex_speed),
                            'braking_jerk': float(max_jerk),
                            'avg_throttle': float(avg_throttle),
                            'trail_braking_style': trail_braking_style
                        })
            except Exception as e:
                # 개별 드라이버 처리 중 오류가 나도 파이프라인이 멈추지 않도록 처리
                continue
       
        if spatial_features:
            df_round = pd.DataFrame(spatial_features)
            # engine 객체를 통해 바로 DB에 적재 (if_exists='append'로 변경하여 누적 추천)
            df_round.to_sql(name='driver_style_2025', con=engine, if_exists='append', index=False)
            print(f"✅ Round {round_num} 데이터 요약본 {len(df_round)}행 MySQL 창고 적재 완료.")
            
    except Exception as e:
        print(f"❌ Round {round_num} 처리 중 오류 발생: {e}")
        traceback.print_exc()
        continue

print("\n🎉 [1단계 완료] 2025 시즌 전체 드라이빙 스타일 데이터베이스 구축을 성공적으로 마쳤습니다!")