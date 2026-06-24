import os
from pathlib import Path
from dotenv import load_dotenv

# 1. 파일 위치 확인
current_dir = Path(__file__).resolve().parent
env_path = current_dir / '.env'

print(f"👀 내 컴퓨터가 찾아가는 .env 파일 주소: {env_path}")
print(f"❓ 해당 위치에 파일이 실제로 존재하나요?: {env_path.exists()}")

# 2. 강제로 로드 시도
file_loaded = load_dotenv(dotenv_path=env_path)
print(f"📖 파이썬이 .env 파일을 성공적으로 읽었나요?: {file_loaded}")

# 3. 가려진 값 확인 (보안을 위해 첫 두 글자만 출력)
user_val = os.getenv("DB_USER")
pw_val = os.getenv("DB_PASSWORD")

def mask_val(val):
    if val is None: return "❌ 값 없음 (None)"
    return f"⭕ 연결 성공! ({val[:2]}***)"

print(f"👤 DB_USER 변수 상태: {mask_val(user_val)}")
print(f"🔑 DB_PASSWORD 변수 상태: {mask_val(pw_val)}")