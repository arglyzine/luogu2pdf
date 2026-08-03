"""共享格式化工具：两个后端共用的日期/时限/内存/文件名等格式化。"""

import re


def fmt_date(date_str):
    """'2026-08-03' -> '2026 年 8 月 3 日'；解析失败原样返回。"""
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(date_str))
    if m:
        return f"{m.group(1)} 年 {int(m.group(2))} 月 {int(m.group(3))} 日"
    return str(date_str)


def fmt_time_range(raw):
    """'9:00-13:00' -> '09:00 $\\sim$ 13:00'（补零 + 数学波浪号，两侧间距对称）。"""
    s = str(raw).strip().replace("~", "-").replace("～", "-")
    parts = re.split(r"\s*-\s*", s)
    if len(parts) == 2:
        def f(t):
            m = re.match(r"(\d{1,2}):(\d{2})", t.strip())
            return f"{int(m.group(1)):02d}:{m.group(2)}" if m else t.strip()
        return f"{f(parts[0])} $\\sim$ {f(parts[1])}"
    return s


def fmt_time_limit(raw):
    """'500ms' -> '0.5 秒'；'1.00s' -> '1.0 秒'；'1.00s ~ 1.20s' -> '1.0 秒 ～ 1.2 秒'。"""
    s = raw.strip().lower()
    def one(x):
        m = re.match(r"([\d.]+)\s*ms$", x)
        if m:
            return f"{float(m.group(1)) / 1000:.1f} 秒"
        m = re.match(r"([\d.]+)\s*s$", x)
        if m:
            return f"{float(m.group(1)):.1f} 秒"
        return x
    if "~" in s or "～" in s:
        a, b = re.split(r"\s*[~～]\s*", s)
        return f"{one(a)} ～ {one(b)}"
    return one(s)


def fmt_memory(raw):
    """'16.00MB' -> '16 MiB'；'512.00MB' -> '512 MiB'；'1GB' -> '1024 MiB'。"""
    s = raw.strip().upper()
    m = re.match(r"([\d.]+)\s*(KB|MB|GB)$", s)
    if m:
        v, u = float(m.group(1)), m.group(2)
        v = v * 1024 if u == "GB" else v / 1024 if u == "KB" else v
        return f"{v:g} MiB"
    return s


def safe_filename(name, fallback="题目"):
    """生成文件系统安全的名字。"""
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "-", name).strip("-")
    return cleaned or fallback


def dashfix(s):
    """日期数字之间的连字符改点号（YYYY.MM.DD 格式）。"""
    return re.sub(r"(?<=\d)-(?=\d)", ".", s)
