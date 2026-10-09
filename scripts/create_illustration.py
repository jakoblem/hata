"""Create a tiny, self-contained decorative SVG for the static website."""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'site' / 'assets' / 'analysis.svg'

def curve(fn, x0, x1, y0, amplitude, steps=280):
    coords = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 - amplitude * fn(t)
        coords.append(f'{"M" if i == 0 else "L"}{x:.2f},{y:.2f}')
    return ' '.join(coords)

w, h = 575, 535
s = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
<title id="t">A mathematical signal represented by harmonic components</title>
<desc id="d">An abstract wave at the top and several simpler component waves below, a decorative illustration of harmonic analysis.</desc>
<defs>
<linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#1a3347"/><stop offset="1" stop-color="#112536"/></linearGradient>
<linearGradient id="trace" x1="0" x2="1" y1="0" y2="0"><stop stop-color="#d7e8db"/><stop offset=".58" stop-color="#faefdb"/><stop offset="1" stop-color="#d0a49a"/></linearGradient>
<linearGradient id="fade" x1="0" x2="1"><stop stop-color="#aac8c1" stop-opacity=".30"/><stop offset="1" stop-color="#aac8c1" stop-opacity=".06"/></linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="10" fill="url(#bg)"/>
<circle cx="565" cy="11" r="190" fill="#517b83" opacity=".065"/>
<path d="M34 92H541" stroke="#536877" stroke-opacity=".5"/>
<rect x="34" y="27" width="9" height="9" rx="2" fill="#ddaa9d"/><rect x="49" y="27" width="9" height="9" rx="2" fill="#829fad"/><rect x="64" y="27" width="9" height="9" rx="2" fill="#456b78"/>
<text x="92" y="35" fill="#c2d2d7" font-family="Arial,Helvetica,sans-serif" font-size="12" letter-spacing="1.7">SIGNAL / REPRESENTATION</text>
<text x="539" y="35" fill="#c2d2d7" text-anchor="end" font-family="Arial,Helvetica,sans-serif" font-size="12">01</text>
<text x="38" y="124" fill="#b3c4cb" font-family="Arial,Helvetica,sans-serif" font-size="11" letter-spacing="1.6">ORIGINAL SIGNAL</text>
<text x="537" y="124" text-anchor="end" fill="#e2b4a7" font-family="Georgia,serif" font-size="17" font-style="italic">f(t)</text>''']
# waveform graph area
for y in [162, 198, 234, 270]:
    s.append(f'<path d="M38 {y}H537" stroke="#6c8290" stroke-opacity=".23" stroke-width="1"/>')
for x in range(39, 540, 42):
    s.append(f'<path d="M{x} 146V285" stroke="#6c8290" stroke-opacity=".19" stroke-width="1"/>')
fun = lambda t: .47*math.sin(2*math.pi*3.4*t + .65) + .25*math.sin(2*math.pi*7.8*t - .5) + .12*math.sin(2*math.pi*15*t + .3)
s.append(f'<path d="{curve(fun, 39, 536, 216, 68)}" stroke="url(#trace)" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
s.append('<circle cx="430" cy="178" r="4" fill="#e5b4a6"/><circle cx="430" cy="178" r="10" fill="none" stroke="#e5b4a6" opacity=".36"/>')
s.append('<path d="M38 305H537" stroke="#536877" stroke-opacity=".65"/>')
s.append('<text x="38" y="332" fill="#b3c4cb" font-family="Arial,Helvetica,sans-serif" font-size="11" letter-spacing="1.6">HARMONIC COMPONENTS</text>')
# component mini-panels
for idx, (x0, lab, freq, phase, color) in enumerate([(39,'φ₁',2.5,0.9,'#c7e0da'),(214,'φ₂',5.2,-.5,'#e4d7c8'),(389,'φ₃',8.1,1.0,'#dbaea2')]):
    s.append(f'<rect x="{x0}" y="350" width="149" height="111" rx="5" fill="#284052" opacity=".84"/>')
    s.append(f'<text x="{x0+14}" y="373" fill="{color}" font-size="15" font-family="Georgia,serif" font-style="italic">{lab}</text>')
    s.append(f'<path d="M{x0+13} 421H{x0+136}" stroke="#849aa5" stroke-opacity=".3"/>')
    s.append(f'<path d="{curve(lambda t: math.sin(2*math.pi*freq*t+phase),x0+13,x0+136,420,20,170)}" stroke="{color}" stroke-width="1.8" fill="none" opacity=".96"/>')
s.append('<path d="M38 482H537" stroke="#536877" stroke-opacity=".5"/>')
s.append('<text x="38" y="507" fill="#809baa" font-family="Arial,Helvetica,sans-serif" font-size="10" letter-spacing="1.4">STRUCTURE  ·  REDUNDANCY  ·  STABILITY</text>')
s.append('<text x="537" y="507" text-anchor="end" fill="#e2b4a7" font-family="Georgia,serif" font-size="17" font-style="italic">f = Σ cₖ φₖ</text>')
s.append('</svg>')
OUT.write_text('\n'.join(s), encoding='utf8')
print(OUT)
