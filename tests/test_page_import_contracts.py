"""Catch broken cross-module imports in Streamlit multipage scripts."""
import ast
import importlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCAL_MODULES = {
    "guma_brand", "guma_earth_data", "agrovision_http", "agrovision_modis",
    "agrovision_validation", "agrovision_agronomy", "agrovision_rotation",
    "agrovision_zarc", "agrovision_climate", "agrovision_quality",
    "agrovision_commons", "agrovision_fieldlab", "agrovision_atlas",
    "agrovision_systems",
}


class PageImportContractTests(unittest.TestCase):
    def test_all_local_from_imports_in_pages_resolve(self):
        failures = []
        for path in sorted((ROOT / "pages").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level or node.module not in LOCAL_MODULES:
                    continue
                module = importlib.import_module(node.module)
                for alias in node.names:
                    if alias.name != "*" and not hasattr(module, alias.name):
                        failures.append(f"{path.name}: {node.module}.{alias.name}")
        self.assertEqual(failures, [], "Broken page imports: " + ", ".join(failures))


if __name__ == "__main__":
    unittest.main()
