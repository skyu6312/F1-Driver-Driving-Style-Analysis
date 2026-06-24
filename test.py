import os
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
current_dir = Path(__file__).resolve().parent
load_dotenv(dotenv_path=current_dir / '.env')

# 변수들 일단 날것 그대로 가져오기
u = os.getenv("DB_USER")
p = os.getenv("DB_PASSWORD")
h = os.getenv("DB_HOST")
pt = os.getenv("DB_PORT")
n = os.getenv("DB_NAME")

print("\n==== 🔎 [긴급 디버깅] 내 컴퓨터가 조립한 재료들의 실제 상태 ====")
print(f"1. u  (유저)  : {repr(u)}")
print(f"2. p  (비번)  : {repr(p[:2] + '***' if p else p)}") # 앞글자만 살짝 확인
print(f"3. h  (호스트): {repr(h)}")
print(f"4. pt (포트)  : {repr(pt)}")
print(f"5. n  (DB명)  : {repr(n)}")

# 가공 처리 과정 재현
u_s = str(u).strip().replace(" ", "")
p_s = str(p).strip().replace(" ", "") if p else ""
h_s = str(h).strip().replace(" ", "")
pt_s = str(pt).strip().replace(" ", "")
n_s = str(n).strip().replace(" ", "")

# 문제의 주소 조립 (비밀번호를 감춘 채로 구조만 출력)
masked_url = f"mysql+pymysql://{u_s}:***@{h_s}:{pt_s}/{n_s}"
print(f"\n6. 🧩 최종 조립된 주소의 뼈대 형태:\n   -> {masked_url}")
print("========================================================\n")

# 여기서 강제로 프로그램을 멈춰서 터미널 창의 로그를 확인하게 만듭니다.
import sys
sys.exit("🚨 주소 검증을 위해 임시로 정지했습니다. 위 로그를 확인해 주세요!")