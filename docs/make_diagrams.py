#!/usr/bin/env python3
"""Draws the README diagrams as SVG, in a light and a dark variant (docs/img/<name>-light.svg / -dark.svg).
Run: python3 docs/make_diagrams.py  — standard library only."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent / 'img'
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif"

THEMES = {
    'light': dict(bg='none', card='#ffffff', stroke='#e4e4ee', text='#18181b', sub='#6b6b7b', line='#b9b9cc',
                  shadow='#1e1b4b', shadow_op='0.10', soft='#f4f3ff', lane='#f7f7fb'),
    'dark': dict(bg='none', card='#161b22', stroke='#2d333b', text='#e6edf3', sub='#8b949e', line='#4b5563',
                 shadow='#000000', shadow_op='0.45', soft='#1c1a33', lane='#11161d'),
}
ACCENT_A, ACCENT_B = '#6366f1', '#a855f7'
GREEN, AMBER, RED = '#10b981', '#f59e0b', '#ef4444'


class Svg:
    def __init__(self, w, h, t):
        self.w, self.h, self.t, self.parts = w, h, t, []

    def add(self, s):
        self.parts.append(s)

    def render(self):
        t = self.t
        defs = f'''<defs>
  <linearGradient id="acc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ACCENT_A}"/><stop offset="1" stop-color="{ACCENT_B}"/></linearGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="{t['shadow']}" flood-opacity="{t['shadow_op']}"/></filter>
  <marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{t['line']}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker>
  <marker id="ara" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="{ACCENT_A}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker>
</defs>'''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="{FONT}">\n{defs}\n' + '\n'.join(self.parts) + '\n</svg>\n')

    # ---- pieces
    def text(self, x, y, s, size=14, weight=500, color=None, anchor='middle', op=1):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or self.t["text"]}" '
                 f'text-anchor="{anchor}" opacity="{op}">{escape(s)}</text>')

    def card(self, x, y, w, h, title, sub=None, accent=None, r=14, fill=None):
        t = self.t
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or t["card"]}" stroke="{t["stroke"]}" filter="url(#sh)"/>')
        if accent:
            self.add(f'<rect x="{x}" y="{y + 14}" width="4" height="{h - 28}" rx="2" fill="{accent}"/>')
        cy = y + h / 2 + (0 if sub else 5)
        self.text(x + w / 2, cy - (4 if sub else 0), title, 15, 600)
        if sub:
            self.text(x + w / 2, cy + 16, sub, 12, 400, t['sub'])

    def pill(self, x, y, s, color, w=None, filled=False):
        w = w or (len(s) * 7 + 22)
        if filled:
            self.add(f'<rect x="{x - w / 2}" y="{y - 12}" width="{w}" height="24" rx="12" fill="{color}"/>')
            self.text(x, y + 4.5, s, 12, 600, '#ffffff')
        else:
            self.add(f'<rect x="{x - w / 2}" y="{y - 12}" width="{w}" height="24" rx="12" fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-opacity="0.35"/>')
            self.text(x, y + 4.5, s, 12, 600, color)

    def arrow(self, d, accent=False, dash=False):
        c = ACCENT_A if accent else self.t['line']
        self.add(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" '
                 f'{"stroke-dasharray=\"5 6\"" if dash else ""} marker-end="url(#{"ara" if accent else "ar"})"/>')

    def badge(self, x, y, n):
        self.add(f'<circle cx="{x}" cy="{y}" r="14" fill="url(#acc)"/>')
        self.text(x, y + 5, str(n), 13, 700, '#ffffff')


# ------------------------------------------------------------------ 1. how it works (five steps)
def flow(t):
    s = Svg(1000, 300, t)
    steps = [('You', 'say what to do'), ('Your agent', 'brief · size · urgency'), ('Queue', 'waits for the right moment'),
             ('One agent runs it', 'Claude · Codex · Gemini'), ('You get the result', 'checked, errors first')]
    w, h, gap, y = 168, 92, 40, 70
    x0 = (1000 - (5 * w + 4 * gap)) / 2
    for i, (title, sub) in enumerate(steps):
        x = x0 + i * (w + gap)
        s.card(x, y, w, h, title, sub)
        s.badge(x + 18, y, i + 1)
        if i < 4:
            s.arrow(f'M{x + w + 6} {y + h / 2} L{x + w + gap - 6} {y + h / 2}', accent=True)
    # the queue's little stack
    qx = x0 + 2 * (w + gap) + w / 2
    for k in range(3):
        s.add(f'<rect x="{qx - 30 + k * 4}" y="{y + h + 22 + k * 9}" width="{60 - k * 8}" height="6" rx="3" fill="url(#acc)" opacity="{0.9 - k * 0.25}"/>')
    s.text(500, 250, 'tick runs every few minutes · a task starts only when it fits · one task per agent at a time', 13, 400, t['sub'])
    return s


# ------------------------------------------------------------------ 2. where does a task go
def placement(t):
    s = Svg(1000, 420, t)
    cw, ch = 170, 64
    def node(x, y, title, sub=None, accent=None):
        s.card(x, y, cw, ch, title, sub, accent)
        return (x, y)
    def diamond(cx, cy, label):
        r = 46
        s.add(f'<path d="M{cx} {cy - r} L{cx + r * 1.35} {cy} L{cx} {cy + r} L{cx - r * 1.35} {cy} Z" fill="{t["soft"]}" stroke="{ACCENT_A}" stroke-opacity="0.45" filter="url(#sh)"/>')
        s.text(cx, cy + 5, label, 14, 600)
    node(20, 178, 'New task', 'brief · size')
    diamond(290, 210, 'Related?')
    s.arrow('M196 210 L222 210')
    # related -> same session
    s.arrow('M290 162 L290 92')
    s.pill(320, 128, 'yes', GREEN)
    node(205, 26, 'Same session', 'after current task', GREEN)
    # not related -> urgent?
    diamond(520, 210, 'Urgent?')
    s.arrow('M358 210 L452 210')
    s.pill(405, 196, 'no', s.t['sub'])
    s.arrow('M520 162 L520 92')
    s.pill(548, 128, 'yes', RED)
    node(435, 26, 'Run now', 'where it fits', RED)
    s.arrow('M520 258 L520 330')
    s.pill(560, 294, 'not sure', AMBER)
    node(435, 332, 'Ask you', 'never guessed', AMBER)
    # normal -> most weekly headroom -> fits?
    s.arrow('M588 210 L626 210')
    s.pill(607, 196, 'no', s.t['sub'], w=30)
    node(628, 178, 'Most weekly', 'headroom wins', ACCENT_A)
    diamond(890, 210, 'Fits?')
    s.arrow('M800 210 L828 210')
    s.arrow('M890 162 L890 92')
    s.pill(918, 128, 'yes', GREEN)
    node(805, 26, 'Run now', None, GREEN)
    s.arrow('M890 258 L890 330')
    s.pill(918, 294, 'no', AMBER)
    node(805, 332, 'Wait for reset', 'then run', AMBER)
    return s


# ------------------------------------------------------------------ 3. one task at a time
def timeline(t):
    s = Svg(1000, 330, t)
    left, right, top = 150, 970, 40
    W = right - left
    def X(minutes):            # 0..240 minutes across the width
        return left + W * minutes / 240
    # windows
    s.add(f'<rect x="{X(0)}" y="{top}" width="{X(120) - X(0)}" height="250" rx="12" fill="{t["lane"]}"/>')
    s.add(f'<rect x="{X(120) + 6}" y="{top}" width="{X(240) - X(120) - 6}" height="250" rx="12" fill="{t["lane"]}"/>')
    s.text(X(60), top + 22, 'usage window 1', 12, 600, t['sub'])
    s.text(X(180), top + 22, 'usage window 2', 12, 600, t['sub'])
    s.add(f'<line x1="{X(120) + 3}" y1="{top + 6}" x2="{X(120) + 3}" y2="{top + 244}" stroke="{ACCENT_A}" stroke-width="2" stroke-dasharray="4 5"/>')
    s.pill(X(120) + 3, top + 258, 'reset', ACCENT_A, filled=True)
    # lane labels
    s.text(20, 112, 'Stacked', 15, 700, anchor='start')
    s.text(20, 130, 'three at once', 12, 400, t['sub'], anchor='start')
    s.text(20, 222, 'Dispatcher', 15, 700, anchor='start')
    s.text(20, 240, 'one at a time', 12, 400, t['sub'], anchor='start')
    # stacked: three bars cut at minute 80
    for i, name in enumerate('ABC'):
        y = 82 + i * 22
        s.add(f'<rect x="{X(4)}" y="{y}" width="{X(80) - X(4)}" height="16" rx="8" fill="{RED}" fill-opacity="{0.85 - i * 0.15}"/>')
        s.add(f'<rect x="{X(80)}" y="{y}" width="{X(116) - X(80)}" height="16" rx="8" fill="none" stroke="{RED}" stroke-opacity="0.45" stroke-dasharray="4 4"/>')
        s.text(X(4) + 14, y + 12.5, f'Task {name}', 11, 600, '#ffffff', anchor='start')
    s.add(f'<line x1="{X(80)}" y1="74" x2="{X(80)}" y2="152" stroke="{RED}" stroke-width="2"/>')
    s.text(X(80) - 8, 166, 'limit hit — all three cut off, cache lost', 12, 600, RED, anchor='end')
    # dispatcher: A, B in window 1; C after the reset
    bars = [('Task A', 4, 58), ('Task B', 62, 112), ('Task C', 126, 186)]
    for name, a, b in bars:
        s.add(f'<rect x="{X(a)}" y="200" width="{X(b) - X(a)}" height="26" rx="13" fill="url(#acc)"/>')
        s.text(X(a) + 14, 217.5, name, 12, 600, '#ffffff', anchor='start')
        s.add(f'<circle cx="{X(b) - 13}" cy="213" r="8" fill="#ffffff" fill-opacity="0.9"/>')
        s.add(f'<path d="M{X(b) - 17} 213 l3 3 l6 -6" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    s.text(X(190) + 6, 246, 'all three finish', 12, 600, GREEN, anchor='start')
    return s


# ------------------------------------------------------------------ 4. related work stays in one session
def session(t):
    s = Svg(1000, 290, t)
    s.text(40, 40, 'With the dispatcher', 15, 700, anchor='start')
    s.add(f'<rect x="40" y="58" width="920" height="70" rx="16" fill="{t["soft"]}" stroke="{ACCENT_A}" stroke-opacity="0.35"/>')
    s.text(60, 84, 'session #1', 12, 600, ACCENT_A, anchor='start')
    s.add(f'<rect x="60" y="94" width="400" height="24" rx="12" fill="url(#acc)"/>')
    s.text(76, 110.5, 'weekly report', 12, 600, '#ffffff', anchor='start')
    s.add(f'<rect x="468" y="94" width="300" height="24" rx="12" fill="url(#acc)" opacity="0.8"/>')
    s.text(484, 110.5, '+ add a chart (queued --with)', 12, 600, '#ffffff', anchor='start')
    s.pill(865, 106, 'context kept · cache warm', GREEN, w=180)
    s.text(40, 176, 'Without', 15, 700, t['sub'], anchor='start')
    s.add(f'<rect x="40" y="194" width="920" height="70" rx="16" fill="none" stroke="{t["stroke"]}"/>')
    s.add(f'<rect x="60" y="230" width="400" height="24" rx="12" fill="{t["line"]}" opacity="0.6"/>')
    s.text(76, 246.5, 'weekly report', 12, 600, '#ffffff', anchor='start')
    s.text(60, 220, 'session #1', 12, 600, t['sub'], anchor='start')
    s.add(f'<rect x="468" y="230" width="140" height="24" rx="12" fill="{AMBER}" fill-opacity="0.75"/>')
    s.text(482, 246.5, 're-reading…', 12, 600, '#ffffff', anchor='start')
    s.add(f'<rect x="612" y="230" width="156" height="24" rx="12" fill="{t["line"]}" opacity="0.6"/>')
    s.text(626, 246.5, 'add a chart', 12, 600, '#ffffff', anchor='start')
    s.text(468, 220, 'session #2 (starts from zero)', 12, 600, t['sub'], anchor='start')
    s.pill(865, 242, 'slower · costs more', AMBER, w=150)
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (('how-it-works', flow), ('placement', placement), ('one-at-a-time', timeline), ('same-session', session)):
        for theme, t in THEMES.items():
            (OUT / f'{name}-{theme}.svg').write_text(fn(t).render(), encoding='utf-8')
    print('written:', ', '.join(sorted(p.name for p in OUT.glob('*.svg'))))


if __name__ == '__main__':
    main()
