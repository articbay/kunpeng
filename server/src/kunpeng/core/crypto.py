"""
敏感字段加解密工具

统一使用对称加密 (Fernet / AES-128-CBC + HMAC) 对 API 密钥等敏感信息加密存储，
密钥由应用配置 ``settings.secret_key`` 派生，避免再引入额外的密钥管理成本。

设计要点：
1. 密钥派生：对 ``secret_key`` 取 SHA-256 后做 urlsafe base64，得到 Fernet 需要的 32 字节 key，
   保证任意长度的 ``secret_key`` 都能生成合法密钥。
2. 平滑迁移：``decrypt`` 对无密文前缀的历史明文原样返回，方便在不停机的情况下逐步加密存量数据；
   但对带 ``enc::v1::`` 前缀却解密失败的数据（多因 ``secret_key`` 不一致），直接抛出
   :class:`DecryptError`，避免把密文当明文继续下发（例如被当作 API-Key 请求外部接口）。
3. 幂等加密：``encrypt`` 对已经是本套算法密文的输入不会二次加密，避免重复调用导致嵌套加密。
"""
import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# 自定义密文前缀，用于快速判断字符串是否为本套算法生成的密文，避免误解密/二次加密
_CIPHER_PREFIX = "enc::v1::"


class DecryptError(Exception):
    """密文解密失败异常

    当输入带有 ``enc::v1::`` 前缀（确定是本套算法密文），但使用当前 ``secret_key``
    无法解密时抛出。常见原因是运行进程加载的 ``secret_key`` 与加密时不一致
    （例如从不同目录启动读了不同的 ``.env``，或回落到默认占位值）。
    """


@lru_cache()
def _get_fernet() -> Fernet:
    """根据应用密钥派生 Fernet 实例（缓存，避免重复计算）"""
    from kunpeng.config import settings

    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def is_encrypted(value: str) -> bool:
    """判断字符串是否为本套算法生成的密文"""
    return isinstance(value, str) and value.startswith(_CIPHER_PREFIX)


def encrypt(plaintext: Optional[str]) -> Optional[str]:
    """加密明文；空值原样返回，已加密内容不再二次加密"""
    if plaintext is None or plaintext == "":
        return plaintext
    if is_encrypted(plaintext):
        return plaintext
    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_CIPHER_PREFIX}{token}"


def decrypt(ciphertext: Optional[str]) -> Optional[str]:
    """解密密文；空值或历史明文原样返回（平滑迁移）"""
    if ciphertext is None or ciphertext == "":
        return ciphertext
    if not is_encrypted(ciphertext):
        # 历史明文数据，尚未加密，原样返回
        return ciphertext
    token = ciphertext[len(_CIPHER_PREFIX):]
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        # 带密文前缀却解密失败，几乎都是 secret_key 不一致导致。
        # 绝不能返回原始密文——否则密文会被当明文继续使用（如作为 API-Key 下发），
        # 引发难以定位的下游报错（例如 Ozon 返回 400 Invalid Api-Key）。
        logger.error(
            "敏感字段解密失败：密文带 %s 前缀但无法解密，"
            "通常是 secret_key 与加密时不一致（检查运行目录/.env 加载）。",
            _CIPHER_PREFIX,
        )
        raise DecryptError(
            "无法解密密文，secret_key 可能与加密时不一致"
        ) from exc


def mask_secret(value: Optional[str], visible: int = 4) -> Optional[str]:
    """对敏感信息做脱敏展示：仅保留末尾若干位，其余用 * 代替

    - None / 空字符串：原样返回
    - 长度不足以脱敏：整体用固定长度掩码
    """
    if value is None or value == "":
        return value
    if len(value) <= visible:
        return "*" * 8
    return "*" * 8 + value[-visible:]


from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class EncryptedText(TypeDecorator):
    """透明加解密的 SQLAlchemy 字段类型

    - 写入数据库前自动加密（``process_bind_param``）
    - 从数据库读取后自动解密（``process_result_value``）

    对上层 Service / CRUD 完全透明：读到的始终是明文，落库的始终是密文，
    历史明文数据在解密时原样返回，实现平滑迁移。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
