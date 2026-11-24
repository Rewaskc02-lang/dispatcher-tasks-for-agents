#!/usr/bin/env python3
"""Draws the README hero illustration (docs/img/hero-light.svg, hero-dark.svg). Standard library only.
A person asks; a small dispatcher robot keeps a queue of task cards; three agent desks: one working, one waiting
for its window to reset, one resting. Run: python3 docs/make_hero.py"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent / 'img'
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif"
VIOLET, INDIGO, PINK = '#8b5cf6', '#6366f1', '#ec4899'
GREEN, AMBER, RED, SKY = '#10b981', '#f59e0b', '#ef4444', '#38bdf8'

THEMES = {
    'light': dict(bg1='#f7f5ff', bg2='#eef4ff', ink='#1f1d2e', sub='#6b6880', paper='#ffffff', line='#d9d6ea',
                  desk='#e9e6f7', deskedge='#d6d1ee', skin='#f2c6a8', hair='#3b2f4a', shirt=INDIGO, screen='#1e1b3a',
                  robot='#ffffff', robotedge='#d9d6ea', shadow='0.10', star='#c9c2f0'),
    'dark': dict(bg1='#14122a', bg2='#0d1526', ink='#ecebf7', sub='#9b98b5', paper='#1d1b33', line='#353252',
                 desk='#211f3a', deskedge='#2e2b4d', skin='#e7b48f', hair='#a78bfa', shirt=VIOLET, screen='#0b0a17',
                 robot='#262443', robotedge='#3d3a62', shadow='0.45', star='#3d3870'),
}


class Pic:
    def __init__(self, t, w=1200, h=600):
        self.t, self.w, self.h, self.p = t, w, h, []

    def add(self, s):
        self.p.append(s)

    def text(self, x, y, s, size=14, weight=600, color=None, anchor='middle', op=1):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or self.t["ink"]}" '
                 f'text-anchor="{anchor}" opacity="{op}">{escape(s)}</text>')

    def render(self):
        t = self.t
        defs = f'''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['bg1']}"/><stop offset="1" stop-color="{t['bg2']}"/></linearGradient>
  <linearGradient id="acc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
  <linearGradient id="glow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SKY}" stop-opacity="0.55"/><stop offset="1" stop-color="{SKY}" stop-opacity="0"/></linearGradient>
  <radialGradient id="halo"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.35"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <filter id="sh" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#1e1b4b" flood-opacity="{t['shadow']}"/></filter>
</defs>'''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="{FONT}">\n{defs}\n' + '\n'.join(self.p) + '\n</svg>\n')


def background(p):
    t = p.t
    p.add(f'<rect x="0" y="0" width="{p.w}" height="{p.h}" rx="28" fill="url(#bg)"/>')
    for x, y, r in ((90, 70, 3), (260, 40, 2), (520, 60, 2.5), (760, 36, 2), (1010, 72, 3), (1130, 140, 2), (640, 120, 1.8),
                    (40, 300, 2), (1160, 330, 2.5), (400, 150, 1.6)):
        p.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{t["star"]}"/>')
    # floor line
    p.add(f'<path d="M40 520 H1160" stroke="{t["line"]}" stroke-width="2" stroke-linecap="round"/>')


def person(p, x, y):
    """A person at a laptop, (x, y) = seat point."""
    t = p.t
    # chair
    p.add(f'<rect x="{x - 46}" y="{y + 20}" width="92" height="12" rx="6" fill="{t["deskedge"]}"/>')
    p.add(f'<rect x="{x - 6}" y="{y + 32}" width="12" height="70" rx="6" fill="{t["deskedge"]}"/>')
    # body
    p.add(f'<path d="M{x - 40} {y + 22} C{x - 40} {y - 50}, {x + 40} {y - 50}, {x + 40} {y + 22} Z" fill="{t["shirt"]}"/>')
    # head + hair
    p.add(f'<circle cx="{x}" cy="{y - 72}" r="30" fill="{t["skin"]}"/>')
    p.add(f'<path d="M{x - 31} {y - 74} C{x - 34} {y - 112}, {x + 30} {y - 118}, {x + 32} {y - 78} C{x + 18} {y - 92}, {x - 10} {y - 96}, {x - 31} {y - 74} Z" fill="{t["hair"]}"/>')
    p.add(f'<circle cx="{x + 12}" cy="{y - 70}" r="3" fill="{t["ink"]}"/>')
    p.add(f'<path d="M{x + 8} {y - 57} q6 4 12 0" stroke="{t["ink"]}" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
    # desk + laptop
    p.add(f'<rect x="{x + 20}" y="{y + 4}" width="150" height="14" rx="7" fill="{t["desk"]}" stroke="{t["deskedge"]}"/>')
    p.add(f'<rect x="{x + 60}" y="{y + 18}" width="10" height="84" rx="5" fill="{t["deskedge"]}"/>')
    p.add(f'<rect x="{x + 150}" y="{y + 18}" width="10" height="84" rx="5" fill="{t["deskedge"]}"/>')
    p.add(f'<path d="M{x + 70} {y + 4} L{x + 82} {y - 52} L{x + 150} {y - 52} L{x + 140} {y + 4} Z" fill="{t["screen"]}"/>')
    p.add(f'<circle cx="{x + 114}" cy="{y - 24}" r="5" fill="{VIOLET}" opacity="0.8"/>')
    # arm
    p.add(f'<path d="M{x + 22} {y - 18} Q{x + 52} {y - 8} {x + 72} {y}" stroke="{t["shirt"]}" stroke-width="16" fill="none" stroke-linecap="round"/>')


def bubble(p, x, y, lines):
    t = p.t
    w = max(len(s) for s in lines) * 8.2 + 36
    h = 26 + 22 * len(lines)
    p.add(f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{t["paper"]}"/>'
          f'<path d="M{x + 34} {y + h - 1} l-10 22 l26 -22 Z" fill="{t["paper"]}"/></g>')
    for i, s in enumerate(lines):
        p.text(x + 20, y + 32 + i * 22, s, 15, 600 if i == 0 else 500, t['ink'] if i == 0 else t['sub'], anchor='start')
    return w, h


def robot(p, x, y, s=1.0, body=None, eyes='open', glow=False):
    """A small rounded robot head+body centred at x, bottom at y."""
    t = p.t
    body = body or t['robot']
    if glow:
        p.add(f'<circle cx="{x}" cy="{y - 70 * s}" r="{90 * s}" fill="url(#halo)"/>')
    p.add(f'<g filter="url(#sh)">')
    p.add(f'<rect x="{x - 42 * s}" y="{y - 60 * s}" width="{84 * s}" height="{60 * s}" rx="{22 * s}" fill="{body}" stroke="{t["robotedge"]}"/>')
    p.add(f'<rect x="{x - 50 * s}" y="{y - 132 * s}" width="{100 * s}" height="{74 * s}" rx="{26 * s}" fill="{body}" stroke="{t["robotedge"]}"/>')
    p.add('</g>')
    p.add(f'<line x1="{x}" y1="{y - 132 * s}" x2="{x}" y2="{y - 152 * s}" stroke="{t["robotedge"]}" stroke-width="{4 * s}" stroke-linecap="round"/>')
    p.add(f'<circle cx="{x}" cy="{y - 156 * s}" r="{7 * s}" fill="{PINK if glow else t["robotedge"]}"/>')
    p.add(f'<rect x="{x - 36 * s}" y="{y - 118 * s}" width="{72 * s}" height="{40 * s}" rx="{16 * s}" fill="{t["screen"]}"/>')
    if eyes == 'open':
        for dx in (-14, 14):
            p.add(f'<circle cx="{x + dx * s}" cy="{y - 100 * s}" r="{5.5 * s}" fill="{SKY}"/>')
        p.add(f'<path d="M{x - 9 * s} {y - 89 * s} q{9 * s} {6 * s} {18 * s} 0" stroke="{SKY}" stroke-width="{2.6 * s}" fill="none" stroke-linecap="round"/>')
    elif eyes == 'sleep':
        for dx in (-14, 14):
            p.add(f'<path d="M{x + (dx - 6) * s} {y - 99 * s} q{6 * s} {5 * s} {12 * s} 0" stroke="{SKY}" stroke-width="{2.6 * s}" fill="none" stroke-linecap="round"/>')
    elif eyes == 'wait':
        for dx in (-14, 14):
            p.add(f'<rect x="{x + (dx - 6) * s}" y="{y - 102 * s}" width="{12 * s}" height="{4 * s}" rx="{2 * s}" fill="{AMBER}"/>')


def card(p, x, y, label, tag, color, w=150, rot=0):
    t = p.t
    p.add(f'<g transform="rotate({rot} {x + w / 2} {y + 22})" filter="url(#sh)">'
          f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="12" fill="{t["paper"]}" stroke="{t["line"]}"/>'
          f'<rect x="{x + 10}" y="{y + 12}" width="{w - 66}" height="7" rx="3.5" fill="{t["line"]}"/>'
          f'<rect x="{x + 10}" y="{y + 25}" width="{w - 90}" height="7" rx="3.5" fill="{t["line"]}" opacity="0.7"/>'
          f'<rect x="{x + w - 46}" y="{y + 11}" width="36" height="22" rx="11" fill="{color}"/>'
          f'<text x="{x + w - 28}" y="{y + 26.5}" font-size="12" font-weight="700" fill="#ffffff" text-anchor="middle">{escape(tag)}</text></g>')


def desk(p, x, y, name, state, week):
    """An agent workstation: desk, monitor, robot. state: working | waiting | resting."""
    t = p.t
    # desk
    p.add(f'<rect x="{x - 70}" y="{y}" width="140" height="14" rx="7" fill="{t["desk"]}" stroke="{t["deskedge"]}"/>')
    p.add(f'<rect x="{x - 58}" y="{y + 14}" width="10" height="{520 - y - 14}" rx="5" fill="{t["deskedge"]}"/>')
    p.add(f'<rect x="{x + 48}" y="{y + 14}" width="10" height="{520 - y - 14}" rx="5" fill="{t["deskedge"]}"/>')
    robot(p, x - 30, y + 2, 0.52, eyes={'working': 'open', 'waiting': 'wait', 'resting': 'sleep'}[state],
          glow=(state == 'working'))
    # monitor
    mx, my = x + 2, y - 92
    p.add(f'<rect x="{mx}" y="{my}" width="66" height="62" rx="10" fill="{t["screen"]}" stroke="{t["robotedge"]}"/>')
    p.add(f'<rect x="{mx + 27}" y="{my + 62}" width="12" height="30" fill="{t["robotedge"]}"/>')
    if state == 'working':
        p.add(f'<rect x="{mx}" y="{my}" width="66" height="62" rx="10" fill="url(#glow)"/>')
        for i, (w, c) in enumerate(((40, VIOLET), (30, SKY), (46, PINK), (24, GREEN))):
            p.add(f'<rect x="{mx + 10}" y="{my + 10 + i * 11}" width="{w}" height="6" rx="3" fill="{c}" opacity="0.9"/>')
    elif state == 'waiting':
        cx, cy = mx + 33, my + 31
        p.add(f'<circle cx="{cx}" cy="{cy}" r="19" fill="none" stroke="{AMBER}" stroke-width="3"/>')
        p.add(f'<path d="M{cx} {cy - 11} V{cy} L{cx + 8} {cy + 6}" stroke="{AMBER}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    else:
        p.text(mx + 33, my + 38, 'z z', 16, 700, t['sub'])
    # name + status
    p.text(x, y + 44, name, 15, 700)
    status = {'working': ('working on 1 task', GREEN), 'waiting': ('waits for its reset', AMBER), 'resting': ('free', SKY)}[state]
    p.text(x, y + 64, status[0], 12.5, 600, status[1])
    # weekly gauge
    gx, gy = x - 55, y + 78
    p.add(f'<rect x="{gx}" y="{gy}" width="110" height="8" rx="4" fill="{t["line"]}"/>')
    p.add(f'<rect x="{gx}" y="{gy}" width="{110 * week}" height="8" rx="4" fill="url(#acc)"/>')
    p.text(x, gy + 24, f'week used {int(week * 100)}%', 11.5, 500, t['sub'])


def hero(t):
    p = Pic(t)
    background(p)
    # 1. you
    person(p, 110, 410)
    bubble(p, 34, 150, ['“Refactor payments —', 'not urgent, size L.”'])
    p.add(f'<path d="M280 215 C330 225, 360 250, 385 300" stroke="{VIOLET}" stroke-width="2.4" fill="none" stroke-dasharray="2 9" stroke-linecap="round"/>')
    # 2. dispatcher robot with a clipboard
    robot(p, 425, 470, 1.1, glow=True)
    p.add(f'<g transform="rotate(12 478 376)"><rect x="456" y="347" width="44" height="58" rx="8" fill="{t["paper"]}" stroke="{t["line"]}"/>'
          + ''.join(f'<rect x="464" y="{358 + i * 12}" width="28" height="5" rx="2.5" fill="{t["line"]}"/>' for i in range(3)) + '</g>')
    p.text(425, 505, 'dispatcher', 16, 700)
    p.text(425, 545, 'one queue · sizes · urgency', 12.5, 500, t['sub'])
    # the queue: stacked cards
    card(p, 530, 370, 'urgent', 'now', RED, rot=-2)
    card(p, 536, 310, 'payments', 'L', VIOLET, rot=1.5)
    card(p, 528, 250, 'tests', 'M', INDIGO, rot=-1)
    card(p, 538, 190, 'docs', 'S', SKY, rot=2)
    p.text(612, 450, 'queue', 15, 700)
    p.text(612, 470, 'waits for the right moment', 12, 500, t['sub'])
    # the payments card flies to the free window
    p.add(f'<path d="M690 300 C720 160, 780 120, 812 270" stroke="{VIOLET}" stroke-width="2.4" fill="none" stroke-dasharray="2 9" stroke-linecap="round"/>')
    card(p, 712, 112, 'payments', 'L', VIOLET, w=110, rot=8)
    # 3. agent desks in a row
    desk(p, 820, 380, 'Claude Code', 'working', 0.34)
    desk(p, 970, 380, 'Codex CLI', 'waiting', 0.71)
    desk(p, 1120, 380, 'Gemini CLI', 'resting', 0.18)
    return p


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f'hero-{name}.svg').write_text(hero(t).render(), encoding='utf-8')
    print('written: hero-light.svg, hero-dark.svg')


if __name__ == '__main__':
    main()
