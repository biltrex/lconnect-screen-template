"""Freeze a JS-built mockup into static HTML (the DOM after its scripts ran, scripts removed).

  python -I snapshot_dom.py <design.html> <out.html> [--query "layer=full&demo=0"]

Claude Design mockups often build their widgets in JavaScript from a manifest. Converting one is
much easier from its rendered DOM: every widget is then a real element you can tag with data-lc.
Inline styles, embedded fonts and CSS are kept; <script> tags are dropped.
"""
import argparse, os, re, subprocess, tempfile, shutil, sys

ap = argparse.ArgumentParser()
ap.add_argument('design'); ap.add_argument('out')
ap.add_argument('--query', default='', help='URL query to load the page with, e.g. "demo=0" to stop demo animation')
a = ap.parse_args()
browser = next((p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'] if os.path.exists(p)), None)
if not browser: sys.exit('Chrome or Edge is required')
url = 'file:///' + os.path.abspath(a.design).replace('\\', '/') + (('?' + a.query) if a.query else '')
prof = tempfile.mkdtemp(prefix='lc-snap-')
try:
    dom = subprocess.run([browser, '--headless=new', '--disable-gpu', '--window-size=1920,480',
                          '--virtual-time-budget=3000', f'--user-data-dir={prof}', '--dump-dom', url],
                         capture_output=True, timeout=180).stdout.decode('utf-8', 'replace')
finally:
    shutil.rmtree(prof, ignore_errors=True)
dom = re.sub(r'<script\b[^>]*>.*?</script>', '', dom, flags=re.S | re.I)
open(a.out, 'w', encoding='utf-8').write(dom if dom.lstrip().lower().startswith('<!doctype') else '<!DOCTYPE html>\n' + dom)
print('wrote', a.out, f'({len(dom) // 1024} KB). Body classes from URL modes are kept; check the layout matches.')
