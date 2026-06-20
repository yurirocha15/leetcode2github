from leet2git import version


def test_version_info_includes_runtime_details():
    info = version.version_info()

    assert "leet2git version:" in info
    assert "python version:" in info
    assert "platform:" in info


def test_find_version_line_uses_ast_assignment():
    content = 'OTHER = "__version__ = not this"\n__version__ = "1.2.3"\n'

    assert version._find_version_line(content) == 2


def test_update_version_string_accepts_v_prefix(tmp_path, monkeypatch):
    version_file = tmp_path / "version.py"
    version_file.write_text('__version__ = "0.1.0"\n', encoding="UTF8")
    monkeypatch.setattr(version, "__file__", str(version_file))

    version.update_version_string("v1.2.3")

    assert version_file.read_text(encoding="UTF8") == '__version__ = "1.2.3"\n'


def test_update_version_string_rejects_invalid_version(tmp_path, monkeypatch, capsys):
    version_file = tmp_path / "version.py"
    version_file.write_text('__version__ = "0.1.0"\n', encoding="UTF8")
    monkeypatch.setattr(version, "__file__", str(version_file))

    version.update_version_string("1.2")

    assert version_file.read_text(encoding="UTF8") == '__version__ = "0.1.0"\n'
    assert "Version 1.2 is not valid" in capsys.readouterr().out


def test_update_version_string_reports_missing_assignment(tmp_path, monkeypatch, capsys):
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "0.1.0"\n', encoding="UTF8")
    monkeypatch.setattr(version, "__file__", str(version_file))

    version.update_version_string("1.2.3")

    assert version_file.read_text(encoding="UTF8") == 'VERSION = "0.1.0"\n'
    assert "Could not find __version__" in capsys.readouterr().out
