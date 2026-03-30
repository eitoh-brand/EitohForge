from pathlib import Path

from eitohforge_cli.template_parts.crud_templates import build_crud_context, render_crud_project_templates


def test_crud_templates_match_golden_snapshots() -> None:
    context = build_crud_context("orders")
    rendered = render_crud_project_templates(context)
    golden_dir = Path(__file__).resolve().parents[1] / "golden" / "crud" / "orders"

    assert golden_dir.exists()
    for relative_path, content in rendered.items():
        golden_file = golden_dir / f"{relative_path.replace('/', '__')}.golden"
        assert golden_file.exists(), f"Missing golden file: {golden_file}"
        assert content == golden_file.read_text(encoding="utf-8")

