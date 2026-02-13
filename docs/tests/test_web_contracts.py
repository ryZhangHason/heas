from __future__ import annotations

import unittest
from pathlib import Path


class TestWebContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.app_js = (root / "app.js").read_text(encoding="utf-8")
        cls.index_html = (root / "index.html").read_text(encoding="utf-8")

    def test_contract_versions_exist(self) -> None:
        self.assertIn("PLAYGROUND_CONFIG_VERSION", self.app_js)
        self.assertIn("PLAYGROUND_RUN_RESULT_VERSION", self.app_js)
        self.assertIn("EXPORT_BUNDLE_VERSION", self.app_js)

    def test_run_facts_and_error_panels_exist(self) -> None:
        self.assertIn('id="runFactsOutput"', self.index_html)
        self.assertIn('id="validationErrors"', self.index_html)
        self.assertIn('id="runtimeErrors"', self.index_html)

    def test_io_controls_exist(self) -> None:
        for element_id in ["exportBtn", "importInput", "shareBtn", "replayBtn", "cancelBtn"]:
            self.assertIn(f'id="{element_id}"', self.index_html)


if __name__ == "__main__":
    unittest.main()
