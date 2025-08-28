import importlib
import os


def test_chat_label_prefix(monkeypatch):
    # Ensure dummy token/chat so the notifier is enabled
    os.environ["TG_BOT_TOKEN"] = "dummy-token"
    os.environ["TG_CHAT_ID"] = "123456"
    os.environ["TELEGRAM__LABEL"] = "DEV"

    import src.infra.notify_telegram as nt

    importlib.reload(nt)  # pick up env

    sent = []

    class FakeSender:
        def __init__(self, token: str, chat_id: str) -> None:
            assert token and chat_id

        def send(self, text: str) -> bool:
            sent.append(text)
            return True

    monkeypatch.setattr(nt, "TelegramSender", FakeSender)
    ok = nt.send_telegram("Hello world", enabled=True)
    assert ok is True
    assert sent and sent[0].startswith("DEV | ")
