"""Use temporary, explicitly fake credentials. No live keys or network calls."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def importer():
    path = Path(__file__).resolve().parents[1] / "scripts/import_supabase.py"
    spec = importlib.util.spec_from_file_location("import_config_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_file_supports_comments_bom_whitespace_quotes_and_precedence(importer, tmp_path):
    config = tmp_path / "admin.env"
    fake_key = "unit-test-only-not-a-live-key"
    config.write_text("\ufeff# Local test\n SUPABASE_URL = 'https://unit-test.example/' \nSUPABASE_SECRET_KEY=\"" + fake_key + "\"\n", encoding="utf-8")
    result = importer.load_admin_credentials(config, {"SUPABASE_URL": "https://stale.example", "SUPABASE_SECRET_KEY": "stale-test-value"})
    assert result == ("https://unit-test.example", fake_key)


def test_missing_file_uses_process_environment(importer, tmp_path):
    assert importer.load_admin_credentials(tmp_path / "absent.env", {"SUPABASE_URL": " https://unit-test.example/ ", "SUPABASE_SECRET_KEY": " unit-test-only "}) == ("https://unit-test.example", "unit-test-only")


def test_blank_file_key_never_falls_back_to_stale_environment(importer, tmp_path):
    config = tmp_path / "admin.env"
    config.write_text("SUPABASE_URL=https://unit-test.example\nSUPABASE_SECRET_KEY=\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing SUPABASE_SECRET_KEY"):
        importer.load_admin_credentials(config, {"SUPABASE_SECRET_KEY": "stale-test-value"})


@pytest.mark.parametrize("url", ["https://unit-test.example/rest/v1", "https://supabase.com/dashboard/project/test", "postgresql://user:password@unit-test.example/database", "http://unit-test.example", "https://unit-test.example?value=private-test-value", "https://unit-test.example/#fragment"])
def test_rejects_wrong_url_without_echoing_values(importer, tmp_path, url):
    with pytest.raises(ValueError) as error:
        importer.load_admin_credentials(tmp_path / "absent.env", {"SUPABASE_URL": url, "SUPABASE_SECRET_KEY": "private-test-value"})
    assert "plain HTTPS project origin" in str(error.value)
    assert "private-test-value" not in str(error.value)
    assert "password@" not in str(error.value)


@pytest.mark.parametrize("line", ["VITE_SUPABASE_SECRET_KEY=private-test-value", "$env:SUPABASE_URL = 'https://unit-test.example'", "SUPABASE_SECRET_KEY='private-test-value", "SUPABASE_SECRET_KEY=one\nSUPABASE_SECRET_KEY=private-test-value"])
def test_parser_errors_do_not_echo_contents(importer, tmp_path, line):
    config = tmp_path / "admin.env"
    config.write_text("SUPABASE_URL=https://unit-test.example\n" + line, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        importer.load_admin_credentials(config, {})
    assert "private-test-value" not in str(error.value)


@pytest.mark.parametrize("key", ["sb_publishable_" + "unit-test-only", "https://unit-test.example", "postgresql://unit-test.example"])
def test_rejects_public_key_or_url_in_secret_field(importer, tmp_path, key):
    with pytest.raises(ValueError, match="must be an admin/secret key"):
        importer.load_admin_credentials(tmp_path / "absent.env", {"SUPABASE_URL": "https://unit-test.example", "SUPABASE_SECRET_KEY": key})


def test_dry_run_does_not_even_read_credentials_or_connect(importer, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Dry run must not read credentials or contact Supabase")
    monkeypatch.setattr(importer, "load_admin_credentials", forbidden)
    monkeypatch.setattr(importer, "request", forbidden)
    monkeypatch.setattr(importer.sys, "argv", ["import_supabase.py"])
    importer.main()
    assert "Dry run only" in capsys.readouterr().out


def test_config_check_does_not_publish_print_key_or_read_research(importer, monkeypatch, capsys):
    fake_key = "unit-test-only-not-a-live-key"
    monkeypatch.setattr(importer, "load_admin_credentials", lambda: ("https://unit-test.example", fake_key))
    def forbidden(*args, **kwargs):
        pytest.fail("Configuration checks must not access publication data or network")
    monkeypatch.setattr(importer, "request", forbidden)
    monkeypatch.setattr(importer, "load_publication", forbidden)
    monkeypatch.setattr(importer.sys, "argv", ["import_supabase.py", "--check-config"])
    importer.main()
    output = capsys.readouterr().out
    assert "No credentials printed and no network requests made" in output
    assert fake_key not in output


def test_publish_and_check_are_mutually_exclusive(importer, monkeypatch):
    monkeypatch.setattr(importer.sys, "argv", ["import_supabase.py", "--check-config", "--publish"])
    with pytest.raises(SystemExit) as error:
        importer.main()
    assert error.value.code == 2
