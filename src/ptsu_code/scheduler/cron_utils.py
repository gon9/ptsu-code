"""cron式のパースと次回発火時刻計算。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from croniter import CroniterBadCronError, croniter


def validate_cron(expression: str) -> bool:
    """cron式が有効かを検証する。

    Args:
        expression: 5-field cron式 (例: "0 9 * * 1-5")

    Returns:
        有効ならTrue
    """
    if not isinstance(expression, str) or not expression.strip():
        return False
    try:
        croniter(expression)
    except (CroniterBadCronError, ValueError, KeyError):
        return False
    return True


def next_fire_time(
    expression: str,
    base: datetime | None = None,
    jitter_seconds: int = 0,
) -> datetime | None:
    """次回発火時刻を計算する。

    Args:
        expression: 5-field cron式
        base: 基準時刻(ローカルtz推奨)、省略時はnow
        jitter_seconds: 発火時刻に加算するジッター秒数 (0以上)

    Returns:
        次回発火時刻、cron式が無効ならNone
    """
    if not validate_cron(expression):
        return None
    base = base or datetime.now()
    try:
        iterator = croniter(expression, base)
        next_dt: datetime = iterator.get_next(datetime)
    except (CroniterBadCronError, ValueError):
        return None
    if jitter_seconds > 0:
        next_dt = next_dt + timedelta(seconds=jitter_seconds)
    return next_dt


def compute_jitter_seconds(
    expression: str,
    max_jitter_seconds: int = 90,
) -> int:
    """発火時刻のジッター秒数を計算する。

    cron式が ":00" または ":30" の正時に一致する場合のみジッターを加え、
    サーバー負荷の集中を避ける (Claude Code KAIROS 準拠)。

    Args:
        expression: 5-field cron式
        max_jitter_seconds: 最大ジッター秒数 (デフォ90秒)

    Returns:
        ジッター秒数 (0 <= jitter <= max_jitter_seconds)
    """
    if not validate_cron(expression):
        return 0
    # 分フィールドが 0 or 30 の固定値なら、式の決定性からハッシュで
    # 擬似乱数を生成する
    fields = expression.split()
    if len(fields) < 1:
        return 0
    minute_field = fields[0]
    if minute_field not in ("0", "30"):
        return 0
    # 式からハッシュ値を生成 (決定的なジッター)
    seed = abs(hash(expression)) % (max_jitter_seconds + 1)
    return seed


def cron_to_human(expression: str) -> str:
    """cron式を人間可読な説明に変換する(簡易版)。

    Args:
        expression: 5-field cron式

    Returns:
        人間可読な説明 (例: "at 9:00 on weekdays")、無効なら元の式
    """
    if not validate_cron(expression):
        return expression
    fields = expression.split()
    if len(fields) != 5:
        return expression
    minute, hour, dom, month, dow = fields
    parts = []
    if minute.startswith("*/"):
        parts.append(f"every {minute[2:]} minutes")
    elif hour == "*" and minute != "*":
        parts.append(f"every hour at minute {minute}")
    else:
        time_str = _format_time(hour, minute)
        if time_str:
            parts.append(f"at {time_str}")
    if dow != "*":
        parts.append(_format_dow(dow))
    if dom != "*":
        parts.append(f"on day {dom} of the month")
    if month != "*":
        parts.append(f"in month {month}")
    return " ".join(parts) if parts else expression


def _format_time(hour: str, minute: str) -> str:
    """時刻フィールドを HH:MM 形式にフォーマットする。"""
    try:
        h = int(hour)
        m = int(minute)
        return f"{h:02d}:{m:02d}"
    except (ValueError, TypeError):
        return ""


def _format_dow(dow: str) -> str:
    """曜日フィールドを人間可読な形式に変換する。"""
    mapping = {
        "0": "Sunday",
        "1": "Monday",
        "2": "Tuesday",
        "3": "Wednesday",
        "4": "Thursday",
        "5": "Friday",
        "6": "Saturday",
        "1-5": "on weekdays",
        "0,6": "on weekends",
        "6,0": "on weekends",
    }
    if dow in mapping:
        value = mapping[dow]
        return value if value.startswith("on") else f"on {value}"
    return f"on dow={dow}"


def utc_iso_from_datetime(dt: datetime) -> str:
    """datetimeをUTC ISO 8601文字列に変換する。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.isoformat()
