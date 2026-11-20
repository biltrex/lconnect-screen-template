"""Screenshot a 1920x480 design page and measure its native slots.

  python -I export_design.py <design.html> <build_dir>

Writes into build_dir:
  design-export.html  the design with lc-export.js injected (for debugging)
  ref.png             everything, including sample values (calibration reference)
  background.png      static layer only: all [data-lc] slots hidden (becomes template layer 1)
  manifest.json       every slot's sensor binding + measured box/font/colour
"""
import sys, os, subprocess, json, re, html, shutil, tempfile

here = os.path.dirname(os.path.abspath(__file__))
design, build = sys.argv[1], sys.argv[2]
W, H = 1920, 480
os.makedirs(build, exist_ok=True)

src = open(design, encoding='utf-8').read()
if '</body>' not in src:
    src += '</body>'
inj = ''.join('<script>\n' + open(os.path.join(here, f), encoding='utf-8').read() + '\n</script>\n'
              for f in ('lc-preview.js', 'lc-export.js'))   # preview only fills empty slots, so a design may include it too
src = src.replace('</body>', inj + '</body>', 1)
# Written next to the design (then removed) so relative images/fonts still resolve.
out_html = os.path.join(os.path.dirname(os.path.abspath(design)),
                        '.' + os.path.splitext(os.path.basename(design))[0] + '.lc-export.html')
open(out_html, 'w', encoding='utf-8').write(src)

browser = next((p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'] if os.path.exists(p)), None)
if not browser:
    sys.exit('Chrome or Edge is required for the export step')
url = 'file:///' + os.path.abspath(out_html).replace('\\', '/')
prof = tempfile.mkdtemp(prefix='lc-chrome-')
base = [browser, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
        f'--window-size={W},{H}', '--virtual-time-budget=4000', '--default-background-color=000000ff',
        '--allow-file-access-from-files', f'--user-data-dir={prof}']

def shot(mode, name):
    p = os.path.abspath(os.path.join(build, name))
    subprocess.run(base + [f'--screenshot={p}', f'{url}?lc={mode}'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    print('wrote', p)

try:
    shot('ref', 'ref.png')
    shot('bg', 'background.png')
    shot('text', 'ref-text.png')
    dom = subprocess.run(base + ['--dump-dom', f'{url}?lc=ref'], capture_output=True, timeout=180).stdout.decode('utf-8', 'replace')
finally:
    shutil.rmtree(prof, ignore_errors=True)
    shutil.copy(out_html, os.path.join(build, 'design-export.html'))
    os.remove(out_html)
m = re.search(r'<pre id="lc-manifest" style=[^>]*>(.*?)</pre>', dom, re.S)
if not m:
    sys.exit('No manifest produced: the page has no [data-lc] slots, or its scripts threw before load.')
man = json.loads(html.unescape(m.group(1)))
json.dump(man, open(os.path.join(build, 'manifest.json'), 'w'), indent=1)
from collections import Counter
print(f"manifest: {len(man['texts'])} text slots; " + ', '.join(f'{v} {k}' for k, v in Counter(x['kind'] for x in man['slots']).items()))
for e in man['errors']:
    print('  ERROR', e)
if man['page']['w'] != W or man['page']['h'] != H:
    print(f"  WARNING viewport measured {man['page']}, expected {W}x{H}")
