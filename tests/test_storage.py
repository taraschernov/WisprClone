"""
tests/test_storage.py
CP-3.1: save→get roundtrip returns same value
CP-3.2: config.json after save contains no strings matching API key pattern
CP-3.3: delete→get returns None (empty string)
"""
import pytest
import json
import re
import tempfile
import os
from hypothesis import given, settings
from hypothesis import strategies as st

from storage.keyring_manager import KeyringManager
from storage.config_manager import ConfigManager


# ─── CP-3.1: save→get roundtrip ───────────────────────────────────────────────

class TestCP31_KeyringRoundtrip:
    """CP-3.1: After save_key(service, key), get_key(service) returns the same value."""

    def setup_method(self):
        self.km = KeyringManager()
        self._test_keys = []

    def teardown_method(self):
        for key in self._test_keys:
            self.km.delete(key)

    def test_save_get_roundtrip(self):
        key_name = "test_key_roundtrip"
        value = "gsk_test123456789abcdef"
        self._test_keys.append(key_name)
        self.km.save(key_name, value)
        retrieved = self.km.get(key_name)
        assert retrieved == value

    def test_get_nonexistent_returns_empty(self):
        """Getting a key that was never saved returns empty string."""
        result = self.km.get("nonexistent_key_xyz")
        assert result == ""

    @given(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=50)
    def test_property_roundtrip_preserves_value(self, value):
        """Property: any string saved to keyring can be retrieved unchanged."""
        import uuid
        # Use unique key per invocation to avoid state pollution between hypothesis examples
        key_name = f"test_prop_{uuid.uuid4().hex[:8]}"
        self._test_keys.append(key_name)
        self.km.save(key_name, value)
        retrieved = self.km.get(key_name)
        assert retrieved == value


# ─── CP-3.2: config.json contains no API key patterns ─────────────────────────

class TestCP32_NoSecretsInConfig:
    """CP-3.2: config.json after save must not contain strings matching API key pattern."""

    API_KEY_PATTERN = re.compile(r'\b[A-Za-z0-9_\-]{20,}\b')

    def test_config_json_has_no_long_alphanumeric_strings(self):
        """After saving config, the JSON file must not contain API-key-like strings."""
        # Create a temp ConfigManager with a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["APPDATA"] = tmpdir
            cm = ConfigManager()
            cm.set("hotkey", "ctrl+alt+space")
            cm.set("dictation_language", "English")
            cm.save_settings()

            with open(cm.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for long alphanumeric strings (potential keys)
            matches = self.API_KEY_PATTERN.findall(content)
            # Filter out known safe values (e.g. "ctrl+alt+space" is short, "English" is short)
            suspicious = [m for m in matches if len(m) >= 20]
            assert len(suspicious) == 0, f"Found potential API keys in config.json: {suspicious}"

    def test_secret_keys_rejected_by_set(self):
        """Attempting to set a secret key via config_manager.set() is silently refused."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["APPDATA"] = tmpdir
            cm = ConfigManager()
            cm.set("api_key", "gsk_fakekeyfakekeyfakekey")
            cm.save_settings()

            with open(cm.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "api_key" not in data


# ─── CP-3.3: delete→get returns empty ─────────────────────────────────────────

class TestCP33_DeleteKey:
    """CP-3.3: After delete_key(service), get_key(service) returns empty string."""

    def setup_method(self):
        self.km = KeyringManager()

    def test_delete_then_get_returns_empty(self):
        key_name = "test_delete_key"
        self.km.save(key_name, "some_value")
        self.km.delete(key_name)
        result = self.km.get(key_name)
        assert result == ""

    def test_delete_nonexistent_does_not_crash(self):
        """Deleting a key that doesn't exist must not raise an exception."""
        self.km.delete("nonexistent_key_to_delete")  # should not crash

