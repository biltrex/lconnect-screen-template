/* lc-preview.js: draws a browser preview of every native L-Connect slot from its data-* attributes,
   so a design shows what the screen will. Inline it at the end of a design's <body> (or let
   export_design.py inject it). It only draws into slots that have no child elements, so hand-made
   preview art always wins. Text slots are left alone: they already show their sample value.
   Attribute reference: references/design-contract.md */
(function () {
  const num = (v, d) => (v === undefined || v === '' || isNaN(+v) ? d : +v);
  const yes = v => v !== undefined && v !== 'false' && v !== '0';      // <div data-round> counts as true
  // value -> fraction, using L-Connect's own scales (M_Data.MaxVals): temperatures read against 110, etc.
  const MAX = { CPUTEMP: 110, HDDTEMP: 110, CPUTEMP_F: 230, GPUTEMP_F: 230, HDDTEMP_F: 230, UPSPEED: 100, DOWNSPEED: 100 };
  const pct = el => Math.max(0, Math.min(1, num(el.dataset.sample, 50) / num(el.dataset.max, MAX[(el.dataset.sensor || '').toUpperCase()] || 100)));
  function canvas(el, padY) {
    const r = el.getBoundingClientRect(); padY = padY || 0;
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.round(r.width)); c.height = Math.max(1, Math.round(r.height + 2 * padY));
    c.style.cssText = `position:absolute;left:0;top:${-padY}px;width:100%;height:${r.height + 2 * padY}px;pointer-events:none;overflow:visible`;
    if (getComputedStyle(el).position === 'static') el.style.position = 'absolute';
    el.appendChild(c);
    const g = c.getContext('2d'); g.translate(0, padY);
    return [g, c.width, c.height - 2 * padY];
  }
  function rrect(g, x, y, w, h, r) {
    r = Math.max(0, Math.min(r, w / 2, h / 2));
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }
  const rad = deg => (deg - 90) * Math.PI / 180;      // 0 deg = 12 o'clock, clockwise

  function bar(el, slider) {
    const r0 = el.getBoundingClientRect(), kn = slider ? num(el.dataset.knob, r0.height * 2) : 0;
    const [g, w, h] = canvas(el, Math.max(0, (kn - r0.height) / 2 + 1)); const d = el.dataset, p = pct(el);
    const fill = d.fill || (h > w ? 'btt' : 'ltr'), vertical = fill === 'btt' || fill === 'ttb';
    const len = vertical ? h : w, r = num(d.radius, 0), on = d.on || '#fff', off = d.off || 'transparent';
    const track = d.track || 'solid', lw = num(d.lineWidth, 2);
    if (track === 'solid') { g.fillStyle = off; rrect(g, 0, 0, w, h, r); g.fill(); }
    if (track === 'outline') { g.strokeStyle = off; g.lineWidth = lw; rrect(g, lw / 2, lw / 2, w - lw, h - lw, r); g.stroke(); }
    const n = num(d.segments, 0), gap = num(d.gap, 0);
    const paint = (a, b) => {                      // a..b along the fill axis, in px
      let x = 0, y = 0, ww = w, hh = h;
      if (fill === 'ltr') { x = a; ww = b - a; } else if (fill === 'rtl') { x = w - b; ww = b - a; }
      else if (fill === 'ttb') { y = a; hh = b - a; } else { y = h - b; hh = b - a; }
      let st = on;
      if (d.gradient) {
        const gr = vertical ? g.createLinearGradient(0, fill === 'btt' ? h : 0, 0, fill === 'btt' ? 0 : h)
                            : g.createLinearGradient(fill === 'rtl' ? w : 0, 0, fill === 'rtl' ? 0 : w, 0);
        gr.addColorStop(0, on); gr.addColorStop(1, d.gradient); st = gr;
      }
      g.fillStyle = st; rrect(g, x, y, ww, hh, n > 1 ? 0 : r); g.fill();
    };
    if (n > 1) {
      if (track === 'solid') g.clearRect(0, 0, w, h);                 // blocks draw their own track
      const blk = (len - (n - 1) * gap) / n, lit = Math.round(p * n);
      for (let i = 0; i < n; i++) {
        const a = i * (blk + gap);
        if (i < lit) { paint(a, a + blk); continue; }
        if (track === 'none' || off === 'transparent') continue;
        g.fillStyle = off; let x = 0, y = 0, ww = w, hh = h;          // unlit block
        if (fill === 'ltr') { x = a; ww = blk; } else if (fill === 'rtl') { x = w - a - blk; ww = blk; }
        else if (fill === 'ttb') { y = a; hh = blk; } else { y = h - a - blk; hh = blk; }
        g.fillRect(x, y, ww, hh);
      }
    } else if (p > 0) paint(0, Math.max(r * 2 * (slider ? 0 : 1), p * len));
    if (slider) {
      const k = num(d.knob, h * 2), c = fill === 'rtl' ? w - p * w : p * w;
      g.fillStyle = d.knobColor || on; g.beginPath(); g.arc(Math.max(k / 2, Math.min(w - k / 2, c)), h / 2, k / 2, 0, 7); g.fill();
    }
  }

  function arc(el) {
    const [g, w] = canvas(el); const d = el.dataset, p = pct(el);
    const t = num(d.thickness, w * 0.1), R = (w - t) / 2, c = w / 2;
    const start = num(d.start, 0), sweep = num(d.sweep, 360), rev = yes(d.reverse);
    const a0 = rad(start), a1 = rad(start + (rev ? -1 : 1) * sweep * p), aEnd = rad(start + (rev ? -1 : 1) * sweep);
    g.lineWidth = t; g.lineCap = yes(d.round) ? 'round' : 'butt';
    if (d.track !== 'none' && d.off) { g.strokeStyle = d.off; g.beginPath(); g.arc(c, c, R, a0, aEnd, rev); g.stroke(); }
    if (d.border) { g.save(); g.lineWidth = num(d.border, 2); g.strokeStyle = d.off || '#888';
      for (const rr of [R - t / 2, R + t / 2]) { g.beginPath(); g.arc(c, c, Math.max(1, rr), 0, 7); g.stroke(); } g.restore(); }
    let st = d.on || '#fff';
    if (d.gradient && g.createConicGradient) { const cg = g.createConicGradient(a0, c, c); cg.addColorStop(0, d.on); cg.addColorStop(Math.min(1, sweep / 360), d.gradient); st = cg; }
    g.strokeStyle = st;
    const blk = num(d.block, 0), gap = num(d.gap, 0);
    if (blk > 0) {
      const da = (blk + gap) / R, db = blk / R, tot = Math.abs(a1 - a0);
      for (let a = 0; a < tot - 1e-6; a += da) { const s = rev ? a0 - a : a0 + a; g.beginPath(); g.arc(c, c, R, s, rev ? s - Math.min(db, tot - a) : s + Math.min(db, tot - a), rev); g.stroke(); }
    } else if (p > 0) { g.beginPath(); g.arc(c, c, R, a0, a1, rev); g.stroke(); }
  }

  function chart(el) {
    const [g, w, h] = canvas(el); const d = el.dataset;
    const max = num(d.max, 100), step = num(d.step, 8), n = Math.max(2, Math.round(w / step));
    let hist = (d.history || '').split(',').filter(s => s.trim() !== '').map(Number);
    if (!hist.length) for (let i = 0; i < n; i++) hist.push(45 + 25 * Math.sin(i / 3) + 12 * Math.sin(i * 1.7));
    hist = hist.slice(-n);
    const x0 = d.anchor === 'right' ? w - (hist.length - 1) * step : 0;
    const pts = hist.map((v, i) => [x0 + i * step, h - Math.max(0, Math.min(max, v)) / max * h]);
    if (d.fillColor) { g.fillStyle = d.fillColor; g.beginPath(); g.moveTo(pts[0][0], h); pts.forEach(q => g.lineTo(q[0], q[1])); g.lineTo(pts[pts.length - 1][0], h); g.fill(); }
    g.strokeStyle = d.color || '#fff'; g.lineWidth = num(d.lineWidth, 2); g.beginPath(); pts.forEach((q, i) => i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1])); g.stroke();
    if (num(d.frameWidth, 0) > 0) { g.strokeStyle = d.frame || d.color; g.lineWidth = num(d.frameWidth, 1); g.strokeRect(0.5, 0.5, w - 1, h - 1); }
  }

  function needle(el) {
    const [g, w, h] = canvas(el); const d = el.dataset, c = [w / 2, h / 2];
    let p = pct(el);
    if (d.sensor === 'TIME' && d.sample === undefined) { const n = new Date(); p = { h_12: (n.getHours() % 12 + n.getMinutes() / 60) / 12, h_24: n.getHours() / 24, m: n.getMinutes() / 60, s: n.getSeconds() / 60 }[d.sub] ?? 0; }
    const ang = rad(num(d.start, d.sensor === 'TIME' ? 0 : -135) + p * num(d.sweep, d.sensor === 'TIME' ? 360 : 270));
    if (d.image) { return; }   // custom needle images preview as the <img> the design puts inside, if any
    const L = num(d.length, Math.min(w, h) * 0.42), tail = num(d.tail, L * 0.18), wd = num(d.width, Math.max(2, L * 0.06));
    g.strokeStyle = d.color || '#f44'; g.lineWidth = wd; g.lineCap = 'round';
    g.beginPath(); g.moveTo(c[0] - Math.cos(ang) * tail, c[1] - Math.sin(ang) * tail); g.lineTo(c[0] + Math.cos(ang) * L, c[1] + Math.sin(ang) * L); g.stroke();
    if (d.cap !== 'none') { g.fillStyle = d.cap || '#fff'; g.beginPath(); g.arc(c[0], c[1], Math.max(3, wd), 0, 7); g.fill(); }
  }

  function ring(el) {     // approximation of Lian Li's Ring styles (exact look comes from L-Connect)
    const [g, w] = canvas(el); const d = el.dataset, p = pct(el), t = w * 0.12, R = (w - t) / 2 - 2, c = w / 2;
    g.lineWidth = t; g.strokeStyle = d.bg || '#00454D'; g.beginPath(); g.arc(c, c, R, 0, 7); g.stroke();
    const gr = g.createLinearGradient(0, w, w, 0); gr.addColorStop(0, d.color2 || '#00FFEE'); gr.addColorStop(1, d.color1 || '#2A00FF');
    g.strokeStyle = gr; g.beginPath(); g.arc(c, c, R, rad(0), rad(360 * p)); g.stroke();
    g.fillStyle = d.textColor || '#fff'; g.textAlign = 'center'; g.font = `600 ${w * 0.26}px ${d.font || 'Bahnschrift'}, sans-serif`;
    g.fillText(String(Math.round(p * 100)), c, c + w * 0.09);
  }

  function gradientText(el) {   // L-Connect gradient text: colour -> data-gradient
    const c = getComputedStyle(el).color, dir = num(el.dataset.gradientDir, 1);
    el.style.backgroundImage = `linear-gradient(${{ 1: '90deg', 2: '180deg', 3: '135deg' }[dir] || '90deg'}, ${c}, ${el.dataset.gradient})`;
    el.style.webkitBackgroundClip = 'text'; el.style.backgroundClip = 'text'; el.style.webkitTextFillColor = 'transparent';
  }

  function draw() {
    document.querySelectorAll('[data-lc="text"][data-gradient]').forEach(gradientText);
    document.querySelectorAll('[data-lc]').forEach(el => {
      if (el.children.length && el.dataset.preview !== 'auto') return;
      if (el.dataset.preview === 'auto') el.querySelectorAll('canvas').forEach(c => c.remove());
      ({ bar: e => bar(e, false), slider: e => bar(e, true), arc, chart, needle, ring })[el.dataset.lc]?.(el);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', draw); else draw();
})();
