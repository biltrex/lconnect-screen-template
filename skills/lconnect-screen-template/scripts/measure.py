"""Measure where text and elements sit in a design page (after fonts load and scripts run).

  python -I measure.py <design.html> [--selector "CSS selector"] [--query "demo=0"] [--all-text]

Prints one line per element: box (left, top, width, height), the text's own ink-ish box (a DOM Range),
font size/weight and the text. Use it when adapting a mockup that glues units to numbers: measure the
original value and unit spans, then place the live value slot and a static unit element at those spots.
Default selector: every element that directly contains text.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, html

ap = argparse.ArgumentParser()
ap.add_argument('design')
ap.add_argument('--selector', default=None, help='CSS selector (default: every element with its own text)')
ap.add_argument('--query', default='', help='URL query, e.g. "demo=0" to stop demo animation')
a = ap.parse_args()

js = r"""
<script>
addEventListener('load', () => { for (let i = 1; i < 10000; i++) { clearInterval(i); clearTimeout(i); }
  document.fonts.ready.then(() => {
    const sel = %SEL%;
    const els = sel ? [...document.querySelectorAll(sel)]
      : [...document.querySelectorAll('body *')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
    const out = els.map(e => { const r = e.getBoundingClientRect(), g = document.createRange(); g.selectNodeContents(e);
      const t = g.getBoundingClientRect(), cs = getComputedStyle(e);
      return { tag: e.tagName.toLowerCase(), id: e.id || e.dataset.widget || e.dataset.lc || '', text: e.textContent.trim().slice(0, 40),
               box: [r.left, r.top, r.width, r.height].map(Math.round), text_box: [t.left, t.top, t.width, t.height].map(v => Math.round(v * 10) / 10),
               font: cs.fontSize + ' ' + cs.fontWeight + ' ' + cs.fontFamily.split(',')[0], transform: cs.textTransform }; });
    const pre = document.createElement('pre'); pre.id = 'lc-measure'; pre.style.display = 'none';
    pre.textContent = JSON.stringify(out); document.body.appendChild(pre); }); });
</script>
""".replace('%SEL%', json.dumps(a.selector))

src = open(a.design, encoding='utf-8').read()
src = src.replace('</body>', js + '</body>', 1) if '</body>' in src else src + js
tmp = os.path.join(os.path.dirname(os.path.abspath(a.design)), '.' + os.path.basename(a.design) + '.measure.html')
open(tmp, 'w', encoding='utf-8').write(src)
browser = next((p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'] if os.path.exists(p)), None)
if not browser: sys.exit('Chrome or Edge is required')
prof = tempfile.mkdtemp(prefix='lc-measure-')
try:
    url = 'file:///' + os.path.abspath(tmp).replace('\\', '/') + (('?' + a.query) if a.query else '')
    dom = subprocess.run([browser, '--headless=new', '--disable-gpu', '--window-size=1920,480', '--virtual-time-budget=3000',
                          f'--user-data-dir={prof}', '--dump-dom', url], capture_output=True, timeout=180).stdout.decode('utf-8', 'replace')
finally:
    shutil.rmtree(prof, ignore_errors=True); os.remove(tmp)
m = re.search(r'<pre id="lc-measure" style=[^>]*>(.*?)</pre>', dom, re.S)
if not m: sys.exit('nothing measured (page scripts may have thrown)')
sys.stdout.reconfigure(encoding='utf-8')
for e in json.loads(html.unescape(m.group(1))):
    print(f"{e['tag']:5s} {e['id'][:14]:14s} box={e['box']} text_box={e['text_box']} {e['font']} {e['transform'] if e['transform'] != 'none' else ''} | {e['text']}")
