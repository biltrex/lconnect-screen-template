/* Injected into a design page by export_design.py (after lc-preview.js). Driven by ?lc=ref | ?lc=bg.
   - Measures every native slot ([data-lc]) after fonts load and writes a JSON manifest into
     <pre id="lc-manifest">: text slots with their resolved font/colour, every other slot with its
     box and data-* attributes.
   - ?lc=bg hides every slot so the screenshot becomes the static background layer;
     ?lc=text hides only the non-text slots (text calibration reference).
   - Pauses the page's own timers so sample values stay frozen. */
(function () {
  const mode = new URLSearchParams(location.search).get('lc');
  if (mode !== 'ref' && mode !== 'bg' && mode !== 'text') return;
  const KINDS = ['text', 'bar', 'slider', 'arc', 'chart', 'needle', 'ring', 'image'];
  const NEED_SENSOR = ['text', 'bar', 'slider', 'arc', 'chart', 'needle'];

  function run() {
    for (let i = 1; i < 10000; i++) { clearInterval(i); clearTimeout(i); }
    document.fonts.ready.then(measure);
  }

  function measure() {
    const out = { page: { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight },
                  texts: [], slots: [], errors: [] };
    const slots = [...document.querySelectorAll('[data-lc]')];
    slots.forEach((el, i) => {
      const kind = el.dataset.lc;
      const r = el.getBoundingClientRect();
      const box = { x: r.left, y: r.top, w: r.width, h: r.height };
      const id = el.dataset.lcId || el.id || `${kind}-${i}`;
      if (!KINDS.includes(kind)) { out.errors.push(`${id}: unknown data-lc="${kind}" (use ${KINDS.join(', ')})`); return; }
      if (NEED_SENSOR.includes(kind) && !el.dataset.sensor) { out.errors.push(`${id}: missing data-sensor`); return; }
      if (r.width < 1 || r.height < 1) { out.errors.push(`${id}: slot has no size (give it width/height)`); return; }
      if (kind === 'text') {
        const range = document.createRange(); range.selectNodeContents(el);
        const tr = range.getBoundingClientRect();
        const cs = getComputedStyle(el);
        out.texts.push({
          id, sensor: el.dataset.sensor, sub: el.dataset.sub || null,
          align: el.dataset.align || 'right', label: el.dataset.label || id,
          text: el.textContent.trim(), box, ink: { x: tr.left, y: tr.top, w: tr.width, h: tr.height },
          size: parseFloat(cs.fontSize), weight: +cs.fontWeight || 400, italic: cs.fontStyle === 'italic',
          family: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
          font: el.dataset.font || null, color: cs.color,
          gradient: el.dataset.gradient || null, gradientDir: +(el.dataset.gradientDir || 1),
          spacing: parseFloat(cs.letterSpacing) || 0, transform: cs.textTransform
        });
      } else {
        const s = { id, kind, box, label: el.dataset.label || id, data: Object.assign({}, el.dataset) };
        if (kind === 'image') {
          const src = el.currentSrc || el.src || el.dataset.src;
          if (!src) out.errors.push(`${id}: image slot needs an <img src> (or data-src)`);
          s.src = src;
        }
        if (kind === 'ring' && !el.dataset.style) out.errors.push(`${id}: ring needs data-style (Ring1..Ring5)`);
        if ((kind === 'bar' || kind === 'slider' || kind === 'arc') && !el.dataset.on) out.errors.push(`${id}: missing data-on colour`);
        out.slots.push(s);
      }
    });
    if (mode === 'bg') slots.forEach(el => { el.style.visibility = 'hidden'; });
    // text-only reference: hide the non-text slots (their previews) so text ink can be measured alone
    if (mode === 'text') slots.forEach(el => { if (el.dataset.lc !== 'text') el.style.visibility = 'hidden'; });
    const pre = document.createElement('pre');
    pre.id = 'lc-manifest'; pre.style.display = 'none';
    pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
  }

  if (document.readyState === 'complete') run(); else addEventListener('load', run);
})();
