(() => {
  /* ---------- Theme ---------- */
  const root = document.documentElement;
  const themeBtn = document.getElementById('theme');
  const syncTheme = () => {
    const dark = root.dataset.theme === 'black';
    themeBtn.setAttribute('aria-pressed', String(dark));
    themeBtn.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
  };
  themeBtn.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'black' ? 'limestone' : 'black';
    try { localStorage.setItem('prg-theme', root.dataset.theme); } catch {}
    syncTheme();
  });
  syncTheme();

  /* ---------- Liquid Glass refraction ----------
     Chromium can run an SVG filter on the backdrop. Each glass shape gets a displacement map that
     bends what is behind it near its rounded edge, like the rim of a lens. Other browsers keep the blur. */
  const brands = navigator.userAgentData ? navigator.userAgentData.brands : [];
  const canRefract = brands.some(b => /Chromium/.test(b.brand)) && !matchMedia('(prefers-reduced-transparency: reduce)').matches;
  const filterHost = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  filterHost.setAttribute('aria-hidden', 'true');
  filterHost.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
  document.body.appendChild(filterHost);
  const filters = new Map();

  function displacementMap(w, h, r, bevel) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d');
    const img = g.createImageData(w, h);
    const hw = w / 2, hh = h / 2;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const px = x + .5 - hw, py = y + .5 - hh;
      const qx = Math.abs(px) - (hw - r), qy = Math.abs(py) - (hh - r);
      const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
      const depth = Math.max(0, -outside);
      let nx = 0, ny = 0;
      if (qx > 0 && qy > 0) { const l = Math.hypot(qx, qy) || 1; nx = qx / l; ny = qy / l; }
      else if (qx > qy) nx = 1; else ny = 1;
      nx *= Math.sign(px) || 1; ny *= Math.sign(py) || 1;
      const f = depth < bevel ? (1 - depth / bevel) ** 2 : 0;
      const i = (y * w + x) * 4;
      img.data[i] = 128 - 127 * nx * f;
      img.data[i + 1] = 128 - 127 * ny * f;
      img.data[i + 2] = 128;
      img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    return c.toDataURL();
  }

  function refract(node, w, h) {
    if (!canRefract) return;
    w = Math.round(w ?? node.offsetWidth); h = Math.round(h ?? node.offsetHeight);
    if (!w || !h) return;
    const r = Math.min(parseFloat(getComputedStyle(node).borderTopLeftRadius) || 0, w / 2, h / 2);
    const strength = Number(node.dataset.refract || 1);
    const key = `${w}x${h}x${Math.round(r)}x${strength}`;
    let id = filters.get(key);
    if (!id) {
      id = `lg${filters.size}`;
      const bevel = Math.max(8, Math.min(r * .9, 30));
      const scale = strength >= 1 ? 48 : 30;
      const f = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
      f.id = id;
      for (const [k, v] of Object.entries({ x: 0, y: 0, width: w, height: h, filterUnits: 'userSpaceOnUse', 'color-interpolation-filters': 'sRGB' })) f.setAttribute(k, v);
      f.innerHTML = `<feImage href="${displacementMap(w, h, r, bevel)}" x="0" y="0" width="${w}" height="${h}" preserveAspectRatio="none" result="map"/>` +
        `<feDisplacementMap in="SourceGraphic" in2="map" scale="${scale}" xChannelSelector="R" yChannelSelector="G"/>`;
      filterHost.appendChild(f);
      filters.set(key, id);
    }
    const blur = node.dataset.blur ?? (strength >= 1 ? 1.5 : 1);
    const value = `url(#${id}) blur(${blur}px) saturate(175%)`;
    node.style.backdropFilter = value;
    node.style.webkitBackdropFilter = value;
  }
  const refractAll = () => document.querySelectorAll('[data-refract]').forEach(n => refract(n));
  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(refractAll, 150); });

  const start = () => refractAll();
  document.fonts && document.fonts.ready ? document.fonts.ready.then(start) : start();
})();
