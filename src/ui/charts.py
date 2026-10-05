"""Matplotlib charts embedded in Tk, styled to match the original Chart.js charts."""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("TkAgg")
from matplotlib import font_manager                                    # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg        # noqa: E402
from matplotlib.figure import Figure                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch                          # noqa: E402
from matplotlib.ticker import MaxNLocator                              # noqa: E402

from .theme import scale_of                                            # noqa: E402

_FONT = "Inter" if any(f.name == "Inter" for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
PT = 0.72      # CSS px -> matplotlib points at the 100-dpi baseline (figure dpi is 100 x display scale)


def _spline(points, tension=0.35):
    """Chart.js 'splineCurve' control points for every vertex."""
    out = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        px, py = points[max(i - 1, 0)]
        nx, ny = points[min(i + 1, n - 1)]
        d01, d12 = math.hypot(x - px, y - py), math.hypot(nx - x, ny - y)
        tot = d01 + d12
        s01, s12 = (d01 / tot, d12 / tot) if tot else (0, 0)
        fa, fb = tension * s01, tension * s12
        out.append(((x - fa * (nx - px), y - fa * (ny - py)), (x + fb * (nx - px), y + fb * (ny - py))))
    return out


class ChartWidget:
    """kind: 'bar' (rounded top corners) or 'line' (smooth, filled, round points)."""

    def __init__(self, master, kind: str, labels: list[str], values: list[float], color: str, height: int = 240):
        self.kind, self.labels, self.values, self.color = kind, labels, [float(v) for v in values], color
        self.S = scale_of(master)
        self.fig = Figure(figsize=(5.0, height / 100), dpi=100 * self.S, facecolor="white")
        self.ax = self.fig.add_axes([0.1, 0.2, 0.85, 0.7])
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.widget = self.canvas.get_tk_widget()
        self.widget.configure(height=int(height * self.S), bg="white", highlightthickness=0, bd=0)
        self.canvas.mpl_connect("resize_event", lambda e: self.render())
        self.render()

    # ------------------------------------------------------------------
    def render(self):
        S, ax, n = self.S, self.ax, len(self.labels)
        W, H = self.fig.bbox.width, self.fig.bbox.height
        if W < 50 or H < 50 or n == 0:
            return
        ax.clear()
        vmax = max(self.values) if self.values else 0
        ticks = MaxNLocator(nbins=6, steps=[1, 2, 2.5, 5, 10]).tick_values(0, vmax if vmax > 0 else 1)
        ymax = float(ticks[-1])
        ticks = [t for t in ticks if t >= 0]

        # --- layout in real pixels (mirrors Chart.js auto padding) -------------------
        left = (len(f"{int(ymax)}") * 6.6 + 16) * S
        right = 12 * S
        top = 10 * S
        slot = (W - left - right) / n
        longest = max(len(s) for s in self.labels) * 5.9 * S
        rotate = longest > slot - 6 * S
        bottom = (longest * math.sin(math.radians(25)) + 22 * S) if rotate else 28 * S
        if rotate:   # the first rotated label hangs to the left of its tick: make room for it
            left = max(left, longest * math.cos(math.radians(25)) - slot / 2 + 20 * S)
            slot = (W - left - right) / n
        bottom = min(bottom, H * 0.45)
        axw, axh = W - left - right, H - top - bottom
        ax.set_position([left / W, bottom / H, axw / W, axh / H])

        # --- axes styling ---------------------------------------------------------------
        ax.set_facecolor("white")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#e5e7eb")
            ax.spines[side].set_linewidth(1 * PT)
        ax.set_ylim(0, ymax)
        ax.set_yticks(ticks)
        ax.yaxis.grid(True, color="#f1f5f9", linewidth=1 * PT)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0, labelsize=11 * PT, labelcolor="#64748b", pad=6 * PT)
        ax.tick_params(axis="x", length=0, labelsize=10 * PT, labelcolor="#64748b", pad=6 * PT)
        for lbl in ax.get_yticklabels():
            lbl.set_fontfamily(_FONT)

        if self.kind == "bar":
            self._bars(ax, n, ymax, axw, axh, S)
        else:
            self._line(ax, n, ymax, axw, axh, S)

        ax.set_xticks(range(n))
        ax.set_xticklabels(self.labels, rotation=25 if rotate else 0, ha="right" if rotate else "center",
                           rotation_mode="anchor", fontfamily=_FONT)
        self.canvas.draw_idle()

    def _bars(self, ax, n, ymax, axw, axh, S):
        ax.set_xlim(-0.5, n - 0.5)
        dpx, dpy = n / axw, ymax / axh                  # data units per pixel
        r = 6 * S * dpx
        aspect = dpy / dpx
        bw = 0.72
        pad = 14 * S * dpy                               # extends below 0 so the bottom corners are clipped away
        for i, v in enumerate(self.values):
            if v <= 0:
                continue
            ax.add_patch(FancyBboxPatch((i - bw / 2, -pad), bw, v + pad, boxstyle=f"round,pad=0,rounding_size={r}",
                                        mutation_aspect=aspect, facecolor=self.color, edgecolor="none", linewidth=0))

    def _line(self, ax, n, ymax, axw, axh, S):
        ax.set_xlim(-0.12, max(n - 1, 1) + 0.12)
        span = max(n - 1, 1)
        pts = [(axw * i / span, v / ymax * axh) for i, v in enumerate(self.values)]
        curve = [pts[0]]
        if n > 1:
            cps = _spline(pts)
            for i in range(n - 1):
                p0, p3 = pts[i], pts[i + 1]
                c1, c2 = cps[i][1], cps[i + 1][0]
                c1 = (min(max(c1[0], 0), axw), min(max(c1[1], 0), axh))
                c2 = (min(max(c2[0], 0), axw), min(max(c2[1], 0), axh))
                for k in range(1, 25):
                    t = k / 24
                    u = 1 - t
                    curve.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0],
                                  u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1]))
        xs = [x / axw * span for x, _ in curve]
        ys = [y / axh * ymax for _, y in curve]
        ax.fill_between(xs, 0, ys, color=self.color, alpha=0.10, linewidth=0)
        ax.plot(xs, ys, color=self.color, linewidth=2.5 * PT, solid_capstyle="round")
        ax.plot(list(range(n)), self.values, "o", markersize=8 * PT, markerfacecolor=self.color,
                markeredgecolor=self.color, clip_on=False)
