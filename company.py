from __future__ import annotations

import re


def canonical_company(raw_name: object) -> str:
    """Group clear airline name variants without inferring corporate ownership."""
    name = re.sub(r"\s+", "", str(raw_name))
    if not name or name.lower() in {"nan", "none", "<na>"}:
        return "未识别单位"

    if name.startswith(("东航", "中国东方航空", "东方航空")):
        return "东航"
    if name == "上航" or name.startswith("上海航空"):
        return "上海航空"
    if name == "厦航" or name.startswith("厦门航空"):
        return "厦门航空"
    if name == "山航" or name.startswith("山东航空"):
        return "山东航空"
    if name == "福航" or name.startswith("福州航空"):
        return "福州航空"
    if name.startswith(("上海吉祥航空", "吉祥航空")):
        return "吉祥航空"
    if name.startswith(("浙江长龙航空", "长龙航空")):
        return "长龙航空"
    if name.startswith(("杭州圆通货运航空", "圆通航空")):
        return "圆通航空"
    if name.startswith("青岛航空"):
        return "青岛航空"

    for suffix in ("股份有限公司", "有限责任公司", "有限公司"):
        if name.endswith(suffix) and "航空" in name:
            return name[: -len(suffix)]
    return name
