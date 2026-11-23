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
  const KINDS = ['text', 'label', 'bar', 'slider', 'arc', 'chart', 'needle', 'ring', 'image'];
  const TEXTY = ['text', 'label'];   // label = static text widget (L-Connect StaticText), not baked into the background
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
      if (kind === 'label' && el.dataset.sensor) { out.errors.push(`${id}: a label is static text; use data-lc="text" for a sensor`); return; }
      if (TEXTY.includes(kind)) {
        const lit = kind === 'label' ? el.innerText.trim() : el.textContent.trim();   // innerText applies text-transform
        if (kind === 'label' && lit.includes('\n')) { out.errors.push(`${id}: a label is one line; split it into one label per line`); return; }
        if (kind === 'label' && el.children.length) { out.errors.push(`${id}: a label holds plain text only (no child elements); split styled parts into separate labels`); return; }
        const range = document.createRange(); range.selectNodeContents(el);
        const tr = range.getBoundingClientRect();
        const cs = getComputedStyle(el);
        // the range box is the font's whole line box; narrow it to the glyphs' real vertical extent so a
        // neighbour's box (used to mask its ink out of this slot's reference) doesn't swallow this slot's ink
        let iy = tr.top, ih = tr.height;
        try {
          const cx = (measure.cv || (measure.cv = document.createElement('canvas'))).getContext('2d');
          cx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
          const m = cx.measureText(lit);
          if (m.fontBoundingBoxAscent && (m.actualBoundingBoxAscent || m.actualBoundingBoxDescent)) {
            const base = tr.top + m.fontBoundingBoxAscent;
            iy = Math.max(tr.top, base - m.actualBoundingBoxAscent - 1);
            ih = Math.min(tr.top + tr.height, base + m.actualBoundingBoxDescent + 1) - iy;
          }
        } catch (e) {}
        out.texts.push({
          id, sensor: kind === 'label' ? 'StaticText' : el.dataset.sensor, static: kind === 'label', sub: el.dataset.sub || null,
          align: el.dataset.align || (kind === 'label' ? ({ right: 'right', end: 'right', center: 'center' }[cs.textAlign] || 'left') : 'right'), label: el.dataset.label || id,
          text: lit, box, ink: { x: tr.left, y: iy, w: tr.width, h: ih },
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
    if (mode === 'text') slots.forEach(el => { if (!TEXTY.includes(el.dataset.lc)) el.style.visibility = 'hidden'; });
    const pre = document.createElement('pre');
    pre.id = 'lc-manifest'; pre.style.display = 'none';
    pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
  }

  if (document.readyState === 'complete') run(); else addEventListener('load', run);
})();
