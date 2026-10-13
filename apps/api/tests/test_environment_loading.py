import fluxmed


def test_load_environment_with_shallow_docker_path(monkeypatch) -> None:
    # A container can place the package at /app/src/fluxmed; the loader must not
    # assume the monorepo's five nested parent directories exist.
    monkeypatch.setattr(fluxmed, "__file__", "/app/src/fluxmed/__init__.py")
    fluxmed._load_project_environment()


def test_load_environment_keeps_explicit_variables(monkeypatch, tmp_path) -> None:
    project = tmp_path / "fluxmed-project"
    package = project / "apps" / "api" / "src" / "fluxmed"
    package.mkdir(parents=True)
    (project / ".env").write_text("FLUXMED_CONFIG_TEST=from-file\n", encoding="utf-8")
    monkeypatch.setattr(fluxmed, "__file__", str(package / "__init__.py"))
    monkeypatch.setenv("FLUXMED_CONFIG_TEST", "explicit")
    fluxmed._load_project_environment()
    assert __import__("os").environ["FLUXMED_CONFIG_TEST"] == "explicit"
