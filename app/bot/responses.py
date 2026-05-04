from __future__ import annotations

# 本文件用途：Bot 响应文本加载器。
# 从项目根目录的 resources/bot/<name>.txt 文件读取响应文本，支持 Docker volume 挂载覆盖。
# 文件缺失时记录 warning 并降级使用硬编码 fallback，保证服务不中断。
# 已读取的内容会缓存到模块级字典，进程生命周期内只做一次 IO。

from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

# 模块级缓存：name -> 文本内容
_cache: dict[str, str] = {}

# 各响应名称的硬编码 fallback 文本，当对应 txt 文件不存在时使用
_FALLBACK: dict[str, str] = {
    "start": "机器人已就绪，功能正在逐步接入。",
}

# 资源目录：项目根目录 / resources / bot /
# 本文件位于 app/bot/responses.py，向上三级即项目根
_RESOURCES_DIR: Path = Path(__file__).parent.parent.parent / "resources" / "bot"


def load_bot_response(name: str) -> str:
    """加载指定名称的 Bot 响应文本。

    优先从 resources/bot/<name>.txt 文件读取；文件不存在时降级到 _FALLBACK 字典，
    若 _FALLBACK 也无对应条目则返回空字符串。结果会缓存，进程内只读一次 IO。

    Args:
        name: 响应名称（不含 .txt 后缀），如 "start"。

    Returns:
        响应文本字符串；末尾换行已剥除。
    """
    if name in _cache:
        return _cache[name]

    txt_path = _RESOURCES_DIR / f"{name}.txt"
    if txt_path.exists():
        try:
            text = txt_path.read_text(encoding="utf-8").rstrip("\n")
            _cache[name] = text
            logger.debug("已从文件加载 Bot 响应: name=%s path=%s", name, txt_path)
            return text
        except OSError as exc:
            # 读取失败时仍走 fallback，但记录警告
            logger.warning("读取 Bot 响应文件失败，将使用 fallback: name=%s error=%s", name, exc)
    else:
        logger.warning(
            "Bot 响应文件不存在，将使用 fallback: name=%s expected_path=%s",
            name,
            txt_path,
        )

    fallback = _FALLBACK.get(name, "")
    _cache[name] = fallback
    return fallback


__all__ = ["load_bot_response"]
