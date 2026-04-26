from __future__ import annotations

import logging
from unittest.mock import patch, MagicMock

import pytest

from config.settings import reset_settings
from src.main import _configure_logging, _build_pipeline
from src.pipeline.pipeline import VideoPipeline


class TestConfigureLogging:
    def setup_method(self) -> None:
        reset_settings()

    def teardown_method(self) -> None:
        reset_settings()

    def test_configure_logging_uses_settings_level(self) -> None:
        with patch("src.main.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.log_level = "DEBUG"
            mock_gs.return_value = mock_settings

            _configure_logging()

        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_logging_invalid_level_defaults_to_info(self) -> None:
        with patch("src.main.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.log_level = "NONEXISTENT"
            mock_gs.return_value = mock_settings

            _configure_logging()

        root = logging.getLogger()
        assert root.level == logging.INFO


class TestBuildPipeline:
    def setup_method(self) -> None:
        reset_settings()

    def teardown_method(self) -> None:
        reset_settings()

    def test_build_pipeline_returns_pipeline(self) -> None:
        with patch("src.main.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.openai_api_key = "fake-key"
            mock_settings.openai_base_url = "https://fake.api/v1"
            mock_settings.openai_model = "gpt-test"
            mock_settings.tts_voice = "alloy"
            mock_settings.output_dir = "/tmp/output"
            mock_gs.return_value = mock_settings

            pipeline = _build_pipeline()

        assert isinstance(pipeline, VideoPipeline)
