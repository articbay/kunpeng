"""敏感字段加解密工具单元测试"""
import pytest

from kunpeng.core import crypto
from kunpeng.core.crypto import (
    DecryptError,
    decrypt,
    encrypt,
    is_encrypted,
    mask_secret,
)
from kunpeng.schemas.shop import ShopResponse


def test_encrypt_decrypt_roundtrip():
    plaintext = "dc99ca88-db3f-466d-a17c-af646866250c"
    cipher = encrypt(plaintext)
    assert is_encrypted(cipher)
    assert cipher != plaintext
    assert decrypt(cipher) == plaintext


def test_encrypt_is_idempotent():
    """已加密内容不应被二次加密"""
    cipher = encrypt("secret")
    assert encrypt(cipher) == cipher


def test_encrypt_empty_values_passthrough():
    assert encrypt("") == ""
    assert encrypt(None) is None


def test_decrypt_legacy_plaintext_passthrough():
    """历史明文（无密文前缀）应原样返回，兼容平滑迁移"""
    assert decrypt("legacy-plain-key") == "legacy-plain-key"
    assert decrypt("") == ""
    assert decrypt(None) is None


def test_decrypt_wrong_secret_key_raises(monkeypatch):
    """密文前缀存在但 secret_key 不一致时应抛 DecryptError，绝不返回原始密文。

    历史 bug：此处静默返回密文，导致密文被当明文（如 API-Key）继续下发，
    引发 Ozon 400 Invalid Api-Key 这类难以定位的下游报错。
    """
    from kunpeng.config import settings

    original_key = settings.secret_key
    try:
        cipher = encrypt("dc99ca88-db3f-466d-a17c-af646866250c")
        assert is_encrypted(cipher)

        # 切换到不同的 secret_key（模拟测试进程 .env 未加载/回落默认值）
        crypto._get_fernet.cache_clear()
        settings.secret_key = "a-totally-different-secret-key"
        crypto._get_fernet.cache_clear()

        with pytest.raises(DecryptError):
            decrypt(cipher)
    finally:
        settings.secret_key = original_key
        crypto._get_fernet.cache_clear()


def test_mask_secret():
    assert mask_secret("dc99ca88-db3f-466d") == "********f-466d"[-12:] or mask_secret(
        "dc99ca88-db3f-466d"
    ).endswith("466d")
    assert mask_secret("ab") == "*" * 8
    assert mask_secret("") == ""
    assert mask_secret(None) is None


def test_shop_response_masks_sensitive_fields():
    """ShopResponse 序列化时应对敏感字段脱敏"""
    resp = ShopResponse(
        id=1,
        user_id=2,
        name="测试店铺",
        platform="ozon",
        platform_shop_id="123",
        api_key="dc99ca88-db3f-466d-a17c-af646866250c",
        performance_client_id="xxx@advertising.performance.ozon.ru",
        performance_client_secret="8VcFyuK-JDi6QHBc9pMR3TbxBxBC6nHOnQ",
    )
    dumped = resp.model_dump()
    assert dumped["api_key"].startswith("*")
    assert dumped["api_key"].endswith("250c")
    assert dumped["performance_client_secret"].startswith("*")
    # 非敏感字段不脱敏
    assert dumped["performance_client_id"] == "xxx@advertising.performance.ozon.ru"
