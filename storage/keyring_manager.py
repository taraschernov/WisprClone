import keyring
import keyring.errors

SERVICE_NAME = "YapClean"


class KeyringManager:
    def save(self, key_name: str, value: str) -> None:
        keyring.set_password(SERVICE_NAME, key_name, value)

    def get(self, key_name: str) -> str:
        try:
            return keyring.get_password(SERVICE_NAME, key_name) or ""
        except Exception:
            return ""

    def delete(self, key_name: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, key_name)
        except Exception:
            pass


keyring_manager = KeyringManager()
