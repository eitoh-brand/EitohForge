import importlib

import pytest

from eitohforge_sdk.infrastructure.notifications.contracts import NotificationMessage
from eitohforge_sdk.infrastructure.notifications.firebase_push import build_firebase_push_sender


def test_firebase_messaging_module_requires_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    fb_mod = importlib.import_module("eitohforge_sdk.infrastructure.notifications.firebase_push")
    real_import = importlib.import_module

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "firebase_admin.messaging":
            raise ModuleNotFoundError("firebase_admin.messaging")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(fb_mod.importlib, "import_module", fake_import)
    with pytest.raises(RuntimeError, match="firebase-admin"):
        fb_mod._messaging_module()


def test_firebase_push_sender_skips_non_push_channel() -> None:
    sender = build_firebase_push_sender()
    result = sender(NotificationMessage(channel="email", recipient="x", body="b"))
    assert result.status == "skipped"
