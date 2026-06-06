"""认证工具：bcrypt 密码哈希 + JWT 签发/校验。"""
import os
import time
import bcrypt
import jwt

# JWT 密钥：生产环境务必通过环境变量 SCANNORARE_JWT_SECRET 注入足够长的随机值。
JWT_SECRET = os.environ.get(
    "SCANNORARE_JWT_SECRET",
    "scannorare-dev-secret-change-me-in-production-0123456789",
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = int(os.environ.get("SCANNORARE_JWT_EXPIRE", str(7 * 24 * 3600)))  # 默认 7 天


def hash_password(plain: str) -> str:
    """bcrypt 哈希（密码超过 72 字节按 bcrypt 规范截断）。"""
    pw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        # 兼容旧的明文密码（V1.0 占位实现）：哈希不是 bcrypt 格式时按明文比对，便于平滑迁移。
        if not hashed.startswith("$2"):
            return plain == hashed
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """校验并解码 JWT；无效或过期返回 None。"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
