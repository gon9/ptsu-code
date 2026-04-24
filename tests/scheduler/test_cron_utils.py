"""cron_utils モジュールのテスト。"""

from datetime import UTC, datetime

from ptsu_code.scheduler.cron_utils import (
    compute_jitter_seconds,
    cron_to_human,
    next_fire_time,
    utc_iso_from_datetime,
    validate_cron,
)


class TestValidateCron:
    """validate_cron のテスト。"""

    def test_valid_standard_expressions(self) -> None:
        """標準的なcron式が有効と判定される。"""
        assert validate_cron("0 9 * * 1-5")
        assert validate_cron("*/5 * * * *")
        assert validate_cron("0 0 * * *")
        assert validate_cron("30 14 * * *")

    def test_invalid_expressions(self) -> None:
        """無効なcron式が無効と判定される。"""
        assert not validate_cron("")
        assert not validate_cron("   ")
        assert not validate_cron("invalid")
        assert not validate_cron("60 * * * *")  # 分は0-59
        assert not validate_cron("* * *")  # フィールド不足

    def test_non_string_input(self) -> None:
        """文字列以外はFalseを返す。"""
        assert not validate_cron(None)  # type: ignore[arg-type]
        assert not validate_cron(123)  # type: ignore[arg-type]


class TestNextFireTime:
    """next_fire_time のテスト。"""

    def test_every_5_minutes(self) -> None:
        """5分毎のcron式から次回時刻が取れる。"""
        base = datetime(2026, 4, 24, 10, 0, 0)
        result = next_fire_time("*/5 * * * *", base=base)
        assert result == datetime(2026, 4, 24, 10, 5, 0)

    def test_daily_9am(self) -> None:
        """毎日9時のcron式から次回時刻が取れる。"""
        base = datetime(2026, 4, 24, 10, 0, 0)
        result = next_fire_time("0 9 * * *", base=base)
        assert result == datetime(2026, 4, 25, 9, 0, 0)

    def test_invalid_expression_returns_none(self) -> None:
        """無効な式はNoneを返す。"""
        assert next_fire_time("invalid") is None
        assert next_fire_time("") is None

    def test_jitter_adds_seconds(self) -> None:
        """ジッター指定で秒数が加算される。"""
        base = datetime(2026, 4, 24, 10, 0, 0)
        result = next_fire_time("*/5 * * * *", base=base, jitter_seconds=30)
        assert result == datetime(2026, 4, 24, 10, 5, 30)


class TestComputeJitterSeconds:
    """compute_jitter_seconds のテスト。"""

    def test_no_jitter_for_non_round_minutes(self) -> None:
        """:00 / :30 以外はジッターなし。"""
        assert compute_jitter_seconds("7 * * * *") == 0
        assert compute_jitter_seconds("*/5 * * * *") == 0

    def test_jitter_for_round_minutes(self) -> None:
        """:00 ではジッターが加算される。"""
        result = compute_jitter_seconds("0 9 * * *", max_jitter_seconds=90)
        assert 0 <= result <= 90

    def test_deterministic_jitter(self) -> None:
        """同じ式からは同じジッターが生成される(決定的)。"""
        a = compute_jitter_seconds("0 9 * * *")
        b = compute_jitter_seconds("0 9 * * *")
        assert a == b

    def test_invalid_cron_returns_zero(self) -> None:
        """無効な式はジッター0。"""
        assert compute_jitter_seconds("invalid") == 0


class TestCronToHuman:
    """cron_to_human のテスト。"""

    def test_weekday_9am(self) -> None:
        """平日9時の式が人間可読になる。"""
        result = cron_to_human("0 9 * * 1-5")
        assert "09:00" in result
        assert "weekday" in result.lower()

    def test_every_5_minutes(self) -> None:
        """5分毎の式が人間可読になる。"""
        result = cron_to_human("*/5 * * * *")
        assert "5 minutes" in result

    def test_invalid_returns_original(self) -> None:
        """無効な式は元の文字列を返す。"""
        assert cron_to_human("invalid") == "invalid"


class TestUtcIsoFromDatetime:
    """utc_iso_from_datetime のテスト。"""

    def test_naive_datetime_treated_as_utc(self) -> None:
        """tz-naive な datetime は UTC と見なされる。"""
        dt = datetime(2026, 4, 24, 10, 0, 0)
        result = utc_iso_from_datetime(dt)
        assert result.startswith("2026-04-24T10:00:00")
        assert "+00:00" in result or result.endswith("+00:00")

    def test_aware_datetime_converted_to_utc(self) -> None:
        """tz-aware な datetime はUTCに変換される。"""
        dt = datetime(2026, 4, 24, 10, 0, 0, tzinfo=UTC)
        result = utc_iso_from_datetime(dt)
        assert "2026-04-24T10:00:00" in result
