import json
import pytest
from unittest.mock import patch

from pdfcrawler import SettingsManager


@pytest.fixture
def settings_file(tmp_path):
    """Create a temporary settings file path."""
    settings_dir = tmp_path / ".pdfcrawler"
    settings_dir.mkdir()
    sf = settings_dir / "settings.json"
    with patch("pdfcrawler.SETTINGS_DIR", settings_dir), \
         patch("pdfcrawler.SETTINGS_FILE", sf):
        yield sf, settings_dir


class TestSettingsManager:
    """Tests for SettingsManager class."""

    def test_init_creates_dir(self, settings_file):
        """Test that SettingsManager creates the settings directory."""
        sf, settings_dir = settings_file
        SettingsManager()
        assert settings_dir.exists()

    def test_init_loads_empty(self, settings_file):
        """Test that SettingsManager handles missing settings file."""
        sf, _ = settings_file
        sm = SettingsManager()
        assert sm.get_recent_folders() == []
        assert sm.get_frequent_destinations() == []
        assert sm.get_theme() == "darkly"

    def test_save_recent_folders(self, settings_file):
        """Test saving recent search folders."""
        sf, _ = settings_file
        sm = SettingsManager()
        sm.add_recent_folder("/path/to/folder1")
        sm.add_recent_folder("/path/to/folder2")
        sm.add_recent_folder("/path/to/folder3")

        folders = sm.get_recent_folders()
        assert len(folders) == 3
        assert folders[0] == "/path/to/folder3"
        assert folders[1] == "/path/to/folder2"
        assert folders[2] == "/path/to/folder1"

    def test_recent_folders_max_limit(self, settings_file):
        """Test that recent folders are limited to MAX_RECENT."""
        sf, _ = settings_file
        sm = SettingsManager()
        for i in range(20):
            sm.add_recent_folder(f"/path/folder{i}")
        folders = sm.get_recent_folders()
        assert len(folders) == 8  # MAX_RECENT

    def test_recent_folders_dedup(self, settings_file):
        """Test that adding an existing folder moves it to front."""
        sf, _ = settings_file
        sm = SettingsManager()
        sm.add_recent_folder("/path/a")
        sm.add_recent_folder("/path/b")
        sm.add_recent_folder("/path/c")
        sm.add_recent_folder("/path/a")  # Re-add existing

        folders = sm.get_recent_folders()
        assert folders[0] == "/path/a"
        assert len(folders) == 3

    def test_frequent_destinations(self, settings_file):
        """Test saving frequent destination folders."""
        sf, _ = settings_file
        sm = SettingsManager()
        sm.add_frequent_destination("/dest/1")
        sm.add_frequent_destination("/dest/2")

        dests = sm.get_frequent_destinations()
        assert len(dests) == 2
        assert dests[0] == "/dest/2"

    def test_frequent_destinations_max_limit(self, settings_file):
        """Test that frequent destinations are limited to MAX_FREQUENT."""
        sf, _ = settings_file
        sm = SettingsManager()
        for i in range(20):
            sm.add_frequent_destination(f"/dest/{i}")
        dests = sm.get_frequent_destinations()
        assert len(dests) == 5  # MAX_FREQUENT

    def test_theme_persistence(self, settings_file):
        """Test theme saving and loading."""
        sf, _ = settings_file
        sm = SettingsManager()
        sm.set_theme("cosmo")
        assert sm.get_theme() == "cosmo"

        # Reload
        sm2 = SettingsManager()
        assert sm2.get_theme() == "cosmo"

    def test_settings_file_persistence(self, settings_file):
        """Test that settings are persisted to disk."""
        sf, _ = settings_file
        sm = SettingsManager()
        sm.add_recent_folder("/test/path")
        sm.set_theme("flatly")

        assert sf.exists()
        data = json.loads(sf.read_text())
        assert "/test/path" in data["recent_search_folders"]
        assert data["theme"] == "flatly"

    def test_load_corrupted_file(self, settings_file):
        """Test that corrupted settings file is handled gracefully."""
        sf, _ = settings_file
        sf.write_text("not valid json {{{")
        sm = SettingsManager()
        assert sm.get_recent_folders() == []
        assert sm.get_theme() == "darkly"

    def test_load_partial_data(self, settings_file):
        """Test loading settings with missing keys."""
        sf, _ = settings_file
        sf.write_text(json.dumps({"theme": "darkly"}))
        sm = SettingsManager()
        assert sm.get_recent_folders() == []
        assert sm.get_frequent_destinations() == []
        assert sm.get_theme() == "darkly"
