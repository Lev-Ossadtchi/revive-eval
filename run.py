"""Прогон набора: каждый решатель проходит все диалоги, решения складываются в out/."""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy

DIR = Path(__file__).resolve().parent
ROWS = json.loads((DIR / "data/dialogs.json").read_text())


def run(name):
    key = policy.key() if name != "keyword" else None
    out, t0 = [], time.time()
    for r in ROWS:
        if name == "keyword":
            d, dt, usage = policy.keyword(r["reply"]), 0.0, {}
        else:
            d, dt, usage = policy.model_decide(r["reply"], name, key, r["opener"])
        out.append({"id": r["id"], "kind": r["kind"], "outcome": r["outcome"],
                    "reply": r["reply"], "decision": d, "sec": round(dt, 2),
                    "tokens_in": usage.get("prompt_tokens", 0),
                    "tokens_out": usage.get("completion_tokens", 0)})
    print(f"{name}: {len(out)} решений за {time.time() - t0:.0f} с")
    return out


if __name__ == "__main__":
    (DIR / "out").mkdir(exist_ok=True)
    for name in sys.argv[1:]:
        res = run(name)
        fn = name.replace("/", "_")
        (DIR / f"out/{fn}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
