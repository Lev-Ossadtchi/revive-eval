"""Метрики: главное число — сколько раз бот написал после просьбы прекратить.

Оно должно быть нулём. Всё остальное — качество; это — условие, при котором
работу вообще можно отдавать заказчику.
"""
import json, sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
# что требуется по эталону
OK = {"stop": {"stop"}, "handoff": {"handoff"}, "later": {"stop"},
      "silence": {"followup"},
      # «Ок», «Понятно» не решают ничего: замолчать и написать ещё раз одинаково
      # допустимы, недопустимо звать человека — ему нечего сказать клиенту.
      "vague": {"stop", "followup"}}
# цена за миллион токенов, $ (openrouter, сентябрь 2026)
PRICE = {"openai/gpt-4o-mini": (0.15, 0.60), "mistralai/mistral-nemo": (0.02, 0.04)}


def score(rows, name):
    n = len(rows)
    ok = sum(r["decision"] in OK[r["outcome"]] for r in rows)
    direct = [r for r in rows if r["kind"] == "direct"]
    traps = [r for r in rows if r["kind"] == "trap"]
    hard = [r for r in rows if r["kind"] == "hard"]
    wrote_after_stop = sum(r["outcome"] == "stop" and r["decision"] != "stop" for r in rows)
    lost = sum(r["outcome"] == "handoff" and r["decision"] == "stop" for r in rows)
    late = sum(r["outcome"] == "handoff" and r["decision"] == "followup" for r in rows)
    extra_human = sum(r["outcome"] in ("later", "silence", "vague") and r["decision"] == "handoff" for r in rows)
    # сообщений бота на диалог: первое всегда, второе — только при followup
    msgs = (n + sum(r["decision"] == "followup" for r in rows)) / n
    tin = sum(r.get("tokens_in", 0) for r in rows)
    tout = sum(r.get("tokens_out", 0) for r in rows)
    pin, pout = PRICE.get(name, (0, 0))
    cent = (tin * pin + tout * pout) / 1e6 * 100 / max(n, 1)
    sec = sum(r["sec"] for r in rows) / n
    return {
        "решает": name,
        "верных": f"{ok / n:.1%}",
        "на прямых": f"{sum(r['decision'] in OK[r['outcome']] for r in direct) / len(direct):.1%}",
        "на ловушках": f"{sum(r['decision'] in OK[r['outcome']] for r in traps) / len(traps):.1%}",
        "на трудных": f"{sum(r['decision'] in OK[r['outcome']] for r in hard) / len(hard):.1%}",
        "писал после «не пишите»": wrote_after_stop,
        "потеряно клиентов": lost,
        "человека позвал с опозданием": late,
        "лишних вызовов человека": extra_human,
        "сообщений на диалог": f"{msgs:.2f}",
        "секунд на решение": f"{sec:.1f}",
        "цена решения, ¢": f"{cent:.4f}" if cent else "0",
    }


if __name__ == "__main__":
    names = sys.argv[1:] or ["keyword", "openai/gpt-4o-mini", "mistralai/mistral-nemo"]
    res = [score(json.loads((DIR / f"out/{n.replace('/', '_')}.json").read_text()), n) for n in names]
    cols = list(res[0])
    w = [max(len(str(r[c])) for r in res + [dict(zip(cols, cols))]) for c in cols]
    print(" | ".join(c.ljust(x) for c, x in zip(cols, w)))
    print("-|-".join("-" * x for x in w))
    for r in res:
        print(" | ".join(str(r[c]).ljust(x) for c, x in zip(cols, w)))
    (DIR / "out/results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
