"""
Unit tests — Application Configuration.

Tests that Settings loads correctly, computed fields work,
and default values are sane. No DB or Redis required.
"""

from backend.core.config import Settings, get_settings


class TestSettingsDefaults:
    """Test that Settings provides sensible defaults."""

    def test_app_name_default(self):
        s = Settings(postgres_password="x")
        assert s.app_name == "SynapseOps"

    def test_environment_default(self):
        s = Settings(postgres_password="x")
        assert s.environment == "development"

    def test_debug_default_is_false(self):
        s = Settings(postgres_password="x")
        assert s.debug is False

    def test_api_port_default(self):
        s = Settings(postgres_password="x")
        assert s.api_port == 8000

    def test_postgres_port_default(self):
        s = Settings(postgres_password="x")
        assert s.postgres_port == 5432

    def test_redis_port_default(self):
        s = Settings(postgres_password="x")
        assert s.redis_port == 6379

    def test_redis_db_default(self):
        s = Settings(postgres_password="x")
        assert s.redis_db == 0


class TestComputedFields:
    """Test that computed DSN fields are assembled correctly."""

    def test_database_url_contains_asyncpg_driver(self):
        s = Settings(
            postgres_user="user",
            postgres_password="pass",
            postgres_host="db",
            postgres_port=5432,
            postgres_db="testdb",
        )
        assert "postgresql+asyncpg" in s.database_url

    def test_database_url_sync_contains_psycopg2(self):
        s = Settings(
            postgres_user="user",
            postgres_password="pass",
            postgres_host="db",
            postgres_port=5432,
            postgres_db="testdb",
        )
        assert "postgresql+psycopg2" in s.database_url_sync

    def test_database_url_includes_host(self):
        s = Settings(
            postgres_user="u",
            postgres_password="p",
            postgres_host="myhost",
            postgres_port=5433,
            postgres_db="mydb",
        )
        assert "myhost" in s.database_url
        assert "5433" in s.database_url
        assert "mydb" in s.database_url

    def test_redis_url_no_password(self):
        s = Settings(
            postgres_password="x",
            redis_host="redishost",
            redis_port=6380,
            redis_db=2,
            redis_password=None,
        )
        assert s.redis_url == "redis://redishost:6380/2"
        # No credentials present — URL should not contain '@'
        assert "@" not in s.redis_url

    def test_redis_url_with_password(self):
        s = Settings(
            postgres_password="x",
            redis_host="redishost",
            redis_port=6379,
            redis_db=0,
            redis_password="secret",
        )
        assert ":secret@" in s.redis_url


class TestGetSettings:
    """Test the cached get_settings() factory."""

    def test_get_settings_returns_settings_instance(self):
        # Clear cache to ensure fresh load
        get_settings.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_is_cached(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
