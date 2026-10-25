"""PNG of the engine result: 90-day liquidity band (p10-p90, median) over weekly shortfall risk. Plots engine numbers only."""
import base64
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def chart_png(r: dict) -> bytes:
    f, w = r["fan"], r["weeks"]
    x = [date.fromisoformat(d) for d in f["dates"]]
    fig, (a, b) = plt.subplots(2, 1, figsize=(7, 6), constrained_layout=True)
    a.fill_between(x, [v / 1e5 for v in f["p10"]], [v / 1e5 for v in f["p90"]], alpha=0.25, label="10th-90th percentile")
    a.plot(x, [v / 1e5 for v in f["p50"]], label="median")
    a.axhline(0, color="red", lw=1)
    a.set(title="Cash available (bank + undrawn limit), ₹ lakh", ylabel="₹ L")
    a.legend(loc="best", fontsize=8)
    b.bar([date.fromisoformat(k["week_start"]) for k in w], [k["p_shortfall"] * 100 for k in w], width=5,
          color=["tab:red" if k["p_shortfall"] > r["risk_target"] else "tab:green" for k in w])
    b.axhline(r["risk_target"] * 100, color="gray", ls="--", lw=1)
    b.set(title="Chance of running short, by week (%)", ylabel="%")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()


if __name__ == "__main__":
    import json
    from pathlib import Path
    p = chart_png(json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "engine_result.json").read_text()))
    assert p[:4] == b"\x89PNG"
    print("ok")
