from app.core.config import Settings


def test_settings_defaults_are_safe_for_local_dev() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "local"
    assert settings.api_v1_prefix == "/api/v1"
    # Never a real production host/credential by default.
    assert "localhost" in settings.database_url


def test_settings_are_overridable_via_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
