"""Три решения бота-реаниматора после ответа клиента: замолчать, позвать человека, написать ещё раз.

Два решателя: словарь стоп-слов (то, что обычно и стоит в таких ботах) и
дешёвая модель. Сравниваются на одном наборе.
"""
import json, os, re, time, urllib.request
from pathlib import Path

KEY_FILE = Path.home() / ".config/claudefl/openrouter.key"
DECISIONS = ("stop", "handoff", "followup")

STOP_WORDS = re.compile(r"не пиш|не писать|отпиш|удалит\w* (меня|мой|из)|чёрн\w* список|черн\w* список|"
                        r"прекрат|хватит|отстан|спам|не беспоко|пожалуюсь|не давал соглас", re.I)
INTEREST = re.compile(r"актуал|сколько|цена|стоит|смет|срок|замер|посчита|готовы продолж|обсуд", re.I)


def keyword(reply: str | None) -> str:
    """Словарь: стоп-слово важнее интереса — так его обычно и пишут."""
    if reply is None:
        return "followup"
    if STOP_WORDS.search(reply):
        return "stop"
    if INTEREST.search(reply):
        return "handoff"
    return "followup"


SYSTEM = """Ты решаешь, что делать боту после ответа клиента на сообщение из старой базы.

Ответь одним словом:
stop — клиент просит не писать, злится или его ответ означает конец разговора;
handoff — клиент отвечает по делу: спрашивает цену, сроки, замер, просит посчитать;
followup — клиент молчит или ответ ничего не решает; уместно одно короткое сообщение.

Разбирай смысл, а не отдельные слова. «Не звоните, пишите сюда, сколько стоит» —
это handoff: клиент меняет канал и спрашивает по делу. «Да, интересно, но я просил
не писать» — это stop: согласие относится к прошлой просьбе прекратить.
Если клиент отложил вопрос на потом и ничего не спрашивает — stop: человека звать не за чем."""


def _post(model, messages, key, timeout=60):
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", body,
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def model_decide(reply: str | None, model: str, key: str, opener: str = "") -> tuple[str, float, dict]:
    if reply is None:
        return "followup", 0.0, {}      # молчание решает не модель, а правило
    t0 = time.time()
    for attempt in range(3):
        try:
            data = _post(model, [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": f"Бот написал: «{opener}»\nОтвет клиента: «{reply}»"}], key)
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    out = data["choices"][0]["message"]["content"].strip().lower()
    usage = data.get("usage", {})
    for d in DECISIONS:
        if d in out:
            return d, time.time() - t0, usage
    return "followup", time.time() - t0, usage


def key():
    return os.environ.get("OPENROUTER_KEY") or KEY_FILE.read_text().strip()
