# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.rag import api_key_loader


class RagApiKeyLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_project_root = api_key_loader.PROJECT_ROOT
        self.previous_openai_api_key = os.environ.get("OPENAI_API_KEY")
        os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self) -> None:
        api_key_loader.PROJECT_ROOT = self.previous_project_root
        if self.previous_openai_api_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.previous_openai_api_key

    def test_secrets_toml_has_priority_over_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".streamlit").mkdir()
            (project_root / "data").mkdir()
            (project_root / ".streamlit" / "secrets.toml").write_text(
                'OPENAI_API_KEY = "secret-key"\n', encoding="utf-8"
            )
            (project_root / "data" / ".env").write_text(
                "OPENAI_API_KEY=env-key\n", encoding="utf-8"
            )
            api_key_loader.PROJECT_ROOT = project_root

            self.assertEqual(api_key_loader.load_api_key(), "secret-key")

    def test_placeholder_secret_falls_back_to_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".streamlit").mkdir()
            (project_root / "data").mkdir()
            (project_root / ".streamlit" / "secrets.toml").write_text(
                'OPENAI_API_KEY = "<your_api_key>"\n', encoding="utf-8"
            )
            (project_root / "data" / ".env").write_text(
                "OPENAI_API_KEY=env-key\n", encoding="utf-8"
            )
            api_key_loader.PROJECT_ROOT = project_root

            self.assertEqual(api_key_loader.load_api_key(), "env-key")


if __name__ == "__main__":
    unittest.main()
