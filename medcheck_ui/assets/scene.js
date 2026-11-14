// MedCheck 3D stage: a pharmaceutical blister strip. Decorative only.
// Input: { phase: 'idle' | 'scanning' | 'result', status: 'alert' | 'unable' | 'no_alert' | 'error' | null }.
// It never receives a photo, text, batch number or record. Three.js is loaded from the local static folder only.
// Scanning is shown ONLY while the real OCR call runs (the phase is set by the Python script around pipeline.check()).
const VERSION = 5;
const ENGINE_URL = new URL('app/static/vendor/three/three.module.min.js', document.baseURI).href;
const TINT = { alert: [1.0, 0.62, 0.20], unable: [0.95, 0.76, 0.30], no_alert: [0.21, 0.82, 0.90], error: [0.55, 0.60, 0.67] };
const RIM = [0.13, 0.83, 0.93];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smooth = (u) => u * u * (3 - 2 * u);

// Camera/strip poses along the scroll story. x,y are fractions of the half-width/half-height, share = strip width / screen width.
const POSE = {
  hero: { x: 0.52, y: 0.02, share: 0.56, yaw: 0.52, pitch: 0.16, roll: -0.05, cam: 11.0, op: 1.0, glow: 0.75 },
  s1:   { x: 0.60, y: -0.02, share: 0.60, yaw: 0.92, pitch: 0.36, roll: 0.04, cam: 9.2, op: 1.0, glow: 0.9 },   // macro: blisters
  s2:   { x: 0.64, y: 0.20, share: 0.66, yaw: -0.30, pitch: -0.10, roll: 0.0, cam: 8.8, op: 1.0, glow: 1.0 },  // the batch band
  s3:   { x: 0.60, y: 0.02, share: 0.54, yaw: 0.14, pitch: 0.10, roll: 0.02, cam: 10.4, op: 1.0, glow: 1.0 }, // pull back
  tool: { x: 0.60, y: 0.36, share: 0.30, yaw: 0.50, pitch: 0.20, roll: -0.05, cam: 12.5, op: 0.30, glow: 0.35 },
  scan: { x: 0.0, y: 0.04, share: 0.76, yaw: 0.14, pitch: 0.08, roll: 0.0, cam: 10.0, op: 1.0, glow: 1.0 },
};
const FIELDS = ['x', 'y', 'share', 'yaw', 'pitch', 'roll', 'cam', 'op', 'glow'];
const mix = (a, b, u) => { const o = {}; for (const k of FIELDS) o[k] = a[k] + (b[k] - a[k]) * u; return o; };

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch (e) { return false; }
}
function setMode(mode) { document.documentElement.setAttribute('data-mc-stage', mode); }

function create(data) {
  const st = { v: VERSION, disposed: false, timer: 0, raf: 0, undo: [], state: { phase: 'idle', status: null }, info: { frames: 0, level: 0 } };
  const on = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); st.undo.push(() => t.removeEventListener(ev, fn, o)); };
  st.calls = 0;
  st.set = (d) => {
    const prev = st.state.phase;
    st.state = { phase: (d && d.phase) || 'idle', status: (d && d.status) || null };
    document.documentElement.setAttribute('data-mc-phase', st.state.phase);
    if (prev !== 'result' && st.state.phase === 'result' && st.onResult) st.onResult();
    if (st.apply) st.apply();
  };
  st.cancelDispose = () => { clearTimeout(st.timer); st.timer = 0; };
  // Every mount of the component calls the default export; each returns its own cleanup. A cleanup disposes the scene
  // only after a grace period AND only if no newer mount happened since: an old instance being torn down after a new
  // one started must not destroy the live scene. A real unmount (no newer call) releases everything.
  st.makeCleanup = () => {
    const id = ++st.calls;
    return () => { clearTimeout(st.timer); st.timer = setTimeout(() => { if (st.calls === id) st.dispose(); }, 600); };
  };
  st.dispose = () => {
    if (st.disposed) return;
    st.disposed = true;
    cancelAnimationFrame(st.raf);
    st.undo.forEach((u) => { try { u(); } catch (e) { /* ignore */ } });
    if (st.free) { try { st.free(); } catch (e) { /* ignore */ } }
    document.documentElement.removeAttribute('data-mc-phase');
    if (window.__mcStage === st) delete window.__mcStage;
  };
  st.set(data);
  init(st, on).catch((e) => fail(st, e));
  return st;
}

function fail(st, e) {
  st.info.error = String(e && e.message || e);
  setMode('fallback');          // the CSS shows the still artwork instead
  st.dispose();
}

// ---- procedural textures (no image files) ----
function makeRand(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function foilCanvas(W, H) {
  const c = document.createElement('canvas'); c.width = 1536; c.height = 640;
  const g = c.getContext('2d'), r = makeRand(11);
  const grd = g.createLinearGradient(0, 0, c.width, c.height);
  grd.addColorStop(0, '#e4eaf1'); grd.addColorStop(0.45, '#bcc7d4'); grd.addColorStop(1, '#dbe3ec');
  g.fillStyle = grd; g.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < 1400; i++) {                                   // brushed lines
    const v = r() > 0.5 ? 255 : 70;
    g.strokeStyle = `rgba(${v},${v},${v + 10},${0.025 + r() * 0.05})`; g.lineWidth = 1;
    const y = r() * c.height; g.beginPath(); g.moveTo(0, y); g.lineTo(c.width, y + (r() - 0.5) * 8); g.stroke();
  }
  for (let i = 0; i < 90; i++) {                                     // crinkles of the foil lid
    g.strokeStyle = `rgba(255,255,255,${0.07 + r() * 0.12})`; g.lineWidth = 1 + r() * 2.4;
    let x = r() * c.width, y = r() * c.height; g.beginPath(); g.moveTo(x, y);
    for (let k = 0; k < 5; k++) { x += (r() - 0.5) * 200; y += (r() - 0.5) * 110; g.lineTo(x, y); }
    g.stroke();
    g.strokeStyle = `rgba(40,55,75,${0.05 + r() * 0.07})`; g.lineWidth = 1; g.beginPath(); g.moveTo(x, y);
    g.lineTo(x + 60 * (r() - 0.5), y + 40 * (r() - 0.5)); g.stroke();
  }
  g.fillStyle = 'rgba(40,52,66,0.55)';                               // perforation (tear) lines between pockets
  const px = (wx) => (wx / W + 0.5) * c.width, py = (wy) => (0.5 - wy / H) * c.height;
  [-1.75, 0, 1.75].forEach((wx) => { for (let y = 0; y < c.height; y += 18) { g.beginPath(); g.arc(px(wx), y + 4, 2.6, 0, 7); g.fill(); } });
  for (let x = 0; x < c.width; x += 18) { g.beginPath(); g.arc(x + 4, py(0.21), 2.6, 0, 7); g.fill(); }
  return c;
}

async function init(st, on) {
  if (!webglAvailable()) throw new Error('WebGL is not available');
  const THREE = await import(ENGINE_URL);
  if (st.disposed) return;

  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduced = mq.matches;
  on(mq, 'change', () => { reduced = mq.matches; restart(); });

  const canvas = document.createElement('canvas');
  canvas.id = 'mc-stage';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x000000, 0);
  on(canvas, 'webglcontextlost', (e) => { e.preventDefault(); fail(st, new Error('WebGL context lost')); });

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 60);
  camera.position.set(0, 0, 11);
  const disposables = [];
  const track = (o) => { disposables.push(o); return o; };
  let hud = null, brackets = null;
  st.free = () => {
    scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { if (x.map) x.map.dispose(); x.dispose(); });
    });
    disposables.forEach((d) => { try { d.dispose(); } catch (e) { /* ignore */ } });
    renderer.dispose(); renderer.forceContextLoss();
    canvas.remove(); if (hud) hud.remove(); if (brackets) brackets.remove();
    setMode('off');
  };

  // ---- image-based lighting built in code (no HDR file): navy room, long softboxes that streak across foil and glass ----
  const pm = new THREE.PMREMGenerator(renderer);
  const room = new THREE.Scene();
  room.add(new THREE.Mesh(new THREE.BoxGeometry(26, 26, 26), new THREE.MeshBasicMaterial({ color: 0x0a1f40, side: THREE.BackSide })));
  const panel = (r, g, b, w, h, x, y, z) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.lookAt(0, 0, 0); room.add(m);
  };
  panel(6, 6, 6.5, 14, 2.2, 0, 9, 3);        // overhead strip softbox
  panel(5, 5.4, 6, 12, 0.7, 0, 3.5, 9);      // thin front strip: the long highlight on the domes
  panel(0.5, 3.6, 4.8, 2.5, 9, -10, 0, 3);   // cyan side bar
  panel(2.6, 3.8, 5.2, 2.5, 7, 10, 1, 5);    // cool side bar
  panel(1.4, 2.2, 3.0, 12, 1.6, 0, -8, 4);   // low fill
  const envTarget = pm.fromScene(room, 0.03);
  track(envTarget);
  scene.environment = envTarget.texture;
  pm.dispose();
  room.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });

  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(2.5, 4.5, 6.5); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0003; key.shadow.normalBias = 0.02; key.shadow.radius = 3.5;
  Object.assign(key.shadow.camera, { left: -6, right: 6, top: 4, bottom: -4, near: 0.5, far: 24 });
  scene.add(key);
  const rim = new THREE.PointLight(new THREE.Color(...RIM), 42, 34, 1.6); rim.position.set(-5, 2, 3); scene.add(rim);
  const back = new THREE.PointLight(0x3aa8ff, 30, 30, 1.8); back.position.set(5, -1, -3); scene.add(back);

  // ---- backdrop glow and drifting light motes (depth) ----
  const glowCanvas = document.createElement('canvas'); glowCanvas.width = glowCanvas.height = 256;
  { const g = glowCanvas.getContext('2d'); const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(34,211,238,0.55)'); gr.addColorStop(0.45, 'rgba(20,110,170,0.22)'); gr.addColorStop(1, 'rgba(6,20,43,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); }
  const glowTex = track(new THREE.CanvasTexture(glowCanvas));
  const backdrop = new THREE.Mesh(new THREE.PlaneGeometry(17, 11), new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }));
  backdrop.position.z = -3.5; scene.add(backdrop);

  const dotCanvas = document.createElement('canvas'); dotCanvas.width = dotCanvas.height = 64;
  { const g = dotCanvas.getContext('2d'); const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(210,248,255,1)'); gr.addColorStop(0.35, 'rgba(120,225,245,0.5)'); gr.addColorStop(1, 'rgba(34,211,238,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64); }
  const dotTex = track(new THREE.CanvasTexture(dotCanvas));
  const NP = 150, ppos = new Float32Array(NP * 3), pspd = new Float32Array(NP), rr0 = makeRand(5);
  for (let i = 0; i < NP; i++) { ppos[i * 3] = (rr0() - 0.5) * 20; ppos[i * 3 + 1] = (rr0() - 0.5) * 11; ppos[i * 3 + 2] = -5 + rr0() * 9; pspd[i] = 0.03 + rr0() * 0.09; }
  const pgeo = new THREE.BufferGeometry(); pgeo.setAttribute('position', new THREE.BufferAttribute(ppos, 3));
  const motes = new THREE.Points(pgeo, new THREE.PointsMaterial({ map: dotTex, size: 0.11, color: 0xbdf2ff, transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
  scene.add(motes);

  // ---- the strip ----
  const strip = new THREE.Group(); strip.rotation.order = 'YXZ';
  scene.add(strip);
  const roundRect = (w, h, r) => {
    const s = new THREE.Shape(); const x = -w / 2, y = -h / 2;
    s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0);
    s.lineTo(x + w, y + h - r); s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2);
    s.lineTo(x + r, y + h); s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
    s.lineTo(x, y + r); s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5); return s;
  };
  const W = 7.4, H = 2.9;
  const fc = foilCanvas(W, H);
  const foilColor = track(new THREE.CanvasTexture(fc)); foilColor.colorSpace = THREE.SRGBColorSpace;
  const foilData = track(new THREE.CanvasTexture(fc));
  [foilColor, foilData].forEach((t) => { t.repeat.set(1 / W, 1 / H); t.offset.set(0.5, 0.5); t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy()); });
  const foil = new THREE.Mesh(
    new THREE.ExtrudeGeometry(roundRect(W, H, 0.26), { depth: 0.07, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.025, bevelSegments: 4, curveSegments: 20 }),
    new THREE.MeshStandardMaterial({ map: foilColor, bumpMap: foilData, bumpScale: 1.6, roughnessMap: foilData, color: 0xffffff, metalness: 1, roughness: 0.42, envMapIntensity: 1.9 }));
  foil.receiveShadow = true; strip.add(foil);
  const sheet = new THREE.Mesh(
    new THREE.ShapeGeometry(roundRect(W - 0.08, H - 0.08, 0.24), 20),
    new THREE.MeshPhysicalMaterial({ color: 0xd8f1ff, transparent: true, opacity: 0.07, roughness: 0.04, clearcoat: 1, depthWrite: false }));
  sheet.position.z = 0.118; strip.add(sheet);

  // blister: lathe-profiled dome with an embossed flange, true refractive glass
  const prof = [[0, 0.40], [0.10, 0.396], [0.20, 0.378], [0.29, 0.342], [0.355, 0.285], [0.395, 0.215], [0.418, 0.13], [0.43, 0.055], [0.45, 0.016], [0.48, 0.005], [0.53, 0.0]]
    .map(([r, y]) => new THREE.Vector2(r, y)).reverse();   // outer edge first: the lathe then faces outward
  const domeGeo = new THREE.LatheGeometry(prof, 64); domeGeo.scale(1.6, 1, 1); domeGeo.rotateX(Math.PI / 2);
  const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0, roughness: 0.035, transmission: 1, thickness: 0.28, ior: 1.4,
    attenuationColor: new THREE.Color(0xbdeeff), attenuationDistance: 2.5, specularIntensity: 1, clearcoat: 0.6, clearcoatRoughness: 0.02, envMapIntensity: 1.5 });
  const R = 0.17, CYL = 0.28;
  const cylGeo = new THREE.CylinderGeometry(R, R, CYL, 32, 1, true);
  const capGeo = new THREE.SphereGeometry(R, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2);
  const ringGeo = new THREE.TorusGeometry(R + 0.004, 0.011, 8, 32);
  const seamMat = new THREE.MeshStandardMaterial({ color: 0x0a5f73, roughness: 0.4, metalness: 0.2 });
  const half = (mat, dir) => {
    const g = new THREE.Group();
    const c = new THREE.Mesh(cylGeo, mat); c.rotation.z = Math.PI / 2; c.position.x = dir * CYL / 2; c.castShadow = true;
    const s = new THREE.Mesh(capGeo, mat); s.rotation.z = -dir * Math.PI / 2; s.position.x = dir * CYL; s.castShadow = true;
    g.add(c, s); return g;
  };
  const rnd = makeRand(7);
  const pockets = [];
  for (let row = 0; row < 2; row++) for (let col = 0; col < 4; col++) {
    const x = -2.625 + col * 1.75, y = 0.78 - row * 1.14;
    const mc = new THREE.MeshPhysicalMaterial({ color: 0x14bfd8, roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.05, side: THREE.DoubleSide, emissive: 0x18d0e8, emissiveIntensity: 0.1 });
    const mw = new THREE.MeshPhysicalMaterial({ color: 0xf2f8ff, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.05, side: THREE.DoubleSide, emissive: 0xbfefff, emissiveIntensity: 0 });
    const cap = new THREE.Group(); cap.add(half(mc, -1), half(mw, 1));
    const ring = new THREE.Mesh(ringGeo, seamMat); ring.rotation.y = Math.PI / 2; cap.add(ring);
    cap.position.set(x + (rnd() - 0.5) * 0.08, y + (rnd() - 0.5) * 0.05, 0.095 + R + 0.012); cap.rotation.z = (rnd() - 0.5) * 0.18; cap.rotation.y = (rnd() - 0.5) * 0.12;
    strip.add(cap);
    const dome = new THREE.Mesh(domeGeo, glass); dome.position.set(x, y, 0.095); dome.renderOrder = 2; strip.add(dome);
    pockets.push({ x, mc, mw });
  }
  const liteDome = new THREE.MeshPhysicalMaterial({ color: 0xd2f3ff, transparent: true, opacity: 0.2, roughness: 0.04, clearcoat: 1, envMapIntensity: 1.6, depthWrite: false });

  // printed batch band (decorative placeholder dots, not a real batch number)
  const tc = document.createElement('canvas'); tc.width = 1536; tc.height = 160;
  const g2 = tc.getContext('2d');
  g2.fillStyle = '#26323f'; g2.font = '600 74px "Segoe UI Variable Text","Segoe UI",sans-serif'; g2.textBaseline = 'middle';
  g2.fillText('B.No. •••••••   Exp •• / ••••', 40, 84);
  const printTex = track(new THREE.CanvasTexture(tc)); printTex.colorSpace = THREE.SRGBColorSpace;
  printTex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const bandBg = new THREE.Mesh(new THREE.PlaneGeometry(6.9, 0.56), new THREE.MeshBasicMaterial({ color: 0xc9d4e1, transparent: true, opacity: 0.9 }));
  bandBg.position.set(0, -1.12, 0.094); strip.add(bandBg);
  const band = new THREE.Mesh(new THREE.PlaneGeometry(6.8, 0.52), new THREE.MeshBasicMaterial({ map: printTex, transparent: true }));
  band.position.set(0, -1.12, 0.1); strip.add(band);
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(7.1, 0.7), new THREE.MeshBasicMaterial({ color: 0x35d0e6, transparent: true, opacity: 0, depthWrite: false }));
  glow.position.set(0, -1.12, 0.09); strip.add(glow);

  // scanning beam
  const bc = document.createElement('canvas'); bc.width = 256; bc.height = 4;
  const g3 = bc.getContext('2d'); const grad = g3.createLinearGradient(0, 0, 256, 0);
  grad.addColorStop(0, 'rgba(34,211,238,0)'); grad.addColorStop(0.5, 'rgba(180,245,255,1)'); grad.addColorStop(1, 'rgba(34,211,238,0)');
  g3.fillStyle = grad; g3.fillRect(0, 0, 256, 4);
  const beamTex = track(new THREE.CanvasTexture(bc));
  const beam = new THREE.Mesh(new THREE.PlaneGeometry(0.7, H + 0.5), new THREE.MeshBasicMaterial({ map: beamTex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
  beam.position.z = 0.6; strip.add(beam);

  // ---- DOM overlays (created here so they exist only while the 3D stage runs): brackets and the reading line ----
  brackets = document.createElement('div'); brackets.id = 'mc-brackets'; brackets.setAttribute('aria-hidden', 'true');
  brackets.innerHTML = '<i></i><i></i><i></i><i></i>'; document.body.appendChild(brackets);
  hud = document.createElement('div'); hud.id = 'mc-hud'; hud.setAttribute('role', 'status');
  hud.innerHTML = '<b>Reading the photo on this computer</b><span>Two offline text-recognition engines are working. This takes a few seconds.</span><em></em>';
  document.body.appendChild(hud);

  // ---- viewport ----
  const resize = () => {
    const w = Math.max(1, window.innerWidth), h = Math.max(1, window.innerHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    st.info.aspect = +camera.aspect.toFixed(3); st.info.canvasPx = [canvas.width, canvas.height];
    anchorsAt = 0; requestFrame();
  };
  on(window, 'resize', resize);

  // ---- scroll story: poses keyed to where each step really sits on the page ----
  const scroller = () => document.querySelector('[data-testid="stMain"]');
  let anchors = null, anchorsAt = 0;
  const getAnchors = (now) => {
    if (anchors && now - anchorsAt < 400) return anchors;
    const sc = scroller(), steps = [...document.querySelectorAll('.mc-step')], tool = document.getElementById('mc-tool');
    if (!sc || steps.length < 3 || !tool) return (anchors = null);
    const vh = window.innerHeight, base = sc.getBoundingClientRect().top, top0 = sc.scrollTop;
    const at = (el, centre) => { const r = el.getBoundingClientRect(); return r.top - base + top0 - (centre ? vh / 2 - r.height / 2 : vh * 0.3); };
    const a = [0, ...steps.slice(0, 3).map((e) => at(e, true)), at(tool, false)];
    for (let i = 1; i < a.length; i++) a[i] = Math.max(a[i], a[i - 1] + 1);
    anchorsAt = now; return (anchors = a);
  };
  const scrollPose = (now) => {
    const sc = scroller(), A = getAnchors(now);
    if (!sc || !A) return POSE.hero;
    const s = sc.scrollTop, seq = [POSE.hero, POSE.s1, POSE.s2, POSE.s3, POSE.tool];
    if (s <= A[0]) return seq[0];
    for (let i = 0; i < 4; i++) if (s <= A[i + 1]) return mix(seq[i], seq[i + 1], smooth((s - A[i]) / (A[i + 1] - A[i])));
    return seq[4];
  };
  on(window, 'scroll', (e) => {
    const t = e.target;
    if (t !== document && !(t.getAttribute && t.getAttribute('data-testid') === 'stMain')) return;
    requestFrame();
  }, { capture: true, passive: true });
  const adapt = (p, scanning) => {              // portrait screens: centred strip above the text, never behind it
    if (camera.aspect >= 1.1) return p;
    const o = { ...p };
    o.x = 0; o.share = Math.min(0.94, p.share * 1.6);
    o.y = scanning ? 0.05 : (p === POSE.tool ? 0.55 : 0.45 + (p.y || 0) * 0.3);
    o.op = scanning ? 1 : Math.min(p.op, 0.5);
    return o;
  };

  // pointer parallax (off under reduced motion)
  let pxT = 0, pyT = 0, px = 0, py = 0;
  on(window, 'pointermove', (e) => { pxT = (e.clientX / window.innerWidth - 0.5) * 2; pyT = (e.clientY / window.innerHeight - 0.5) * 2; }, { passive: true });

  st.onResult = () => {                          // the verdict is where the user should look: ease the page to it
    st.resultAt = performance.now();
    setTimeout(() => {
      if (st.disposed || st.state.phase !== 'result') return;
      const a = [...document.querySelectorAll('[data-testid="stAlert"]')].find((x) => /^(Alert found|No alert found|Unable to verify|Expired|System error)/.test(x.innerText.trim()));
      if (a) a.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
    }, 650);
  };

  // ---- state ----
  const cur = { ...POSE.hero };
  let beamX = 0, glowO = 0, canvasO = 1, ratioLevel = 0, lastRatio = 0, lite = false;
  const t0 = performance.now();
  const tint = new THREE.Color(...RIM), tmp = new THREE.Color(), corner = new THREE.Vector3();
  const ratio = () => (st.state.phase === 'scanning' ? 1 : Math.min(window.devicePixelRatio || 1, 1.5)) * (ratioLevel >= 2 ? 0.75 : ratioLevel === 1 ? 0.9 : 1);
  const goLite = () => {                          // governor step 2: cheaper glass, no shadows, no motes
    if (lite) return; lite = true;
    scene.traverse((o) => { if (o.isMesh && o.material === glass) o.material = liteDome; });
    renderer.shadowMap.enabled = false; key.castShadow = false; motes.visible = false;
    scene.traverse((o) => { if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.needsUpdate = true; }); });
  };

  const frame = (now, dt) => {
    const scanning = st.state.phase === 'scanning', res = st.state.phase === 'result';
    const tt = (now - t0) / 1000;
    const tgt = adapt(scanning ? POSE.scan : scrollPose(now), scanning);
    if (res) tgt.op = Math.max(tgt.op, 0.55);        // keep the tinted strip visible beside the verdict
    const k = reduced ? 1 : 1 - Math.exp(-Math.min(dt, 0.25) * 4.5);       // cinematic inertia
    for (const f of FIELDS) cur[f] += (tgt[f] - cur[f]) * k;
    px += (pxT - px) * 0.05; py += (pyT - py) * 0.05;
    const par = reduced ? 0 : 1;
    camera.position.set(px * 0.4 * par, -py * 0.22 * par, cur.cam); camera.lookAt(0, 0, 0);
    const halfH = cur.cam * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)), halfW = halfH * camera.aspect;
    strip.scale.setScalar(clamp((cur.share * 2 * halfW) / W, 0.2, 2.4));
    const sway = reduced ? 0 : Math.sin(tt * 0.35);
    strip.position.set(cur.x * halfW, cur.y * halfH + (reduced ? 0 : Math.sin(tt * 0.9) * 0.07), 0);
    strip.rotation.set(cur.pitch + (reduced ? 0 : Math.sin(tt * 0.5) * 0.02), cur.yaw + sway * (scanning ? 0.02 : 0.1), cur.roll);

    // beam: a real sweep while scanning; a slow, faint pass while idle in the hero
    let sweep = 0;
    if (scanning) { sweep = reduced ? 0.5 : Math.abs(((tt * 0.45) % 2) - 1); beam.material.opacity = 0.75; }
    else { const ph = (tt * 0.16) % 1; sweep = ph; beam.material.opacity = reduced || res ? 0 : (ph < 0.5 ? Math.sin(ph * 2 * Math.PI) * 0.2 : 0); }
    beamX = (sweep * 2 - 1) * (W / 2 - 0.4); beam.position.x = beamX;
    pockets.forEach((p) => {                      // blisters light up as the beam crosses them (only while scanning)
      const near = scanning ? Math.max(0, 1 - Math.abs(beamX - p.x) / 0.95) : 0;
      p.mc.emissiveIntensity += ((0.1 + near * 1.5) - p.mc.emissiveIntensity) * 0.35;
      p.mw.emissiveIntensity += ((near * 0.55) - p.mw.emissiveIntensity) * 0.35;
    });

    // result tint (a tint, never a verdict: no_alert is a calm cyan)
    const tc2 = res && TINT[st.state.status] ? TINT[st.state.status] : RIM;
    tint.setRGB(...tc2);
    const pulse = res && st.state.status === 'alert' && !reduced ? 0.5 + 0.5 * Math.sin(tt * 3.2) : 1;
    const gl = res ? (st.state.status === 'no_alert' ? 0.3 : st.state.status === 'error' ? 0.2 : 0.5 * (0.55 + 0.45 * pulse)) : scanning ? 0.25 : 0;
    glowO += (gl - glowO) * 0.1; glow.material.opacity = glowO; glow.material.color.copy(scanning ? tmp.setRGB(...RIM) : tint);
    rim.color.lerp(res ? tint : tmp.setRGB(...RIM), 0.06);
    backdrop.material.opacity = 0.18 + 0.4 * cur.glow; backdrop.position.x = cur.x * halfW * 0.7;
    backdrop.material.color.lerp(res ? tint : tmp.setRGB(1, 1, 1), 0.05);
    canvasO += (cur.op - canvasO) * 0.2; canvas.style.opacity = canvasO.toFixed(3);

    if (motes.visible && !reduced) {              // light motes drift upward; faster while scanning
      const sp = scanning ? 3.2 : 1;
      for (let i = 0; i < NP; i++) {
        ppos[i * 3 + 1] += pspd[i] * dt * sp; ppos[i * 3] += Math.sin(tt * 0.3 + i) * 0.0015;
        if (ppos[i * 3 + 1] > 5.6) ppos[i * 3 + 1] = -5.6;
      }
      pgeo.attributes.position.needsUpdate = true;
    }

    // brackets lock onto the batch band while scanning and for a moment after the result
    const showBr = scanning || (res && st.resultAt && now - st.resultAt < 2600);
    if (showBr) {
      strip.updateMatrixWorld(true);
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const [cx, cy] of [[-3.55, -0.78], [3.55, -0.78], [3.55, -1.46], [-3.55, -1.46]]) {
        corner.set(cx, cy, 0.1); strip.localToWorld(corner); corner.project(camera);
        const sx = (corner.x * 0.5 + 0.5) * window.innerWidth, sy = (-corner.y * 0.5 + 0.5) * window.innerHeight;
        x0 = Math.min(x0, sx); y0 = Math.min(y0, sy); x1 = Math.max(x1, sx); y1 = Math.max(y1, sy);
      }
      Object.assign(brackets.style, { left: x0 + 'px', top: y0 + 'px', width: (x1 - x0) + 'px', height: (y1 - y0) + 'px', opacity: '1' });
      brackets.style.setProperty('--mc-tint', `${Math.round(tint.r * 255)},${Math.round(tint.g * 255)},${Math.round(tint.b * 255)}`);
      brackets.classList.toggle('mc-lock', !scanning);
    } else brackets.style.opacity = '0';

    const pr = ratio();
    if (pr !== lastRatio) { lastRatio = pr; renderer.setPixelRatio(pr); renderer.setSize(window.innerWidth, window.innerHeight, false); }
    renderer.render(scene, camera);
    st.info.frames += 1;
  };

  // ---- loop: capped ~30 fps (20 fps while the OCR runs), paused when hidden, static when motion is reduced ----
  let last = 0, slow = 0, pending = false;
  const loop = (now) => {
    st.raf = requestAnimationFrame(loop);
    const cap = st.state.phase === 'scanning' ? 50 : 33;
    const dt = now - last; if (dt < cap - 2) return;
    // quality governor: if frames arrive far slower than the cap, lower resolution, then use cheaper glass; if still slow, give up
    if (last && dt > cap * 2.2) slow++; else slow = Math.max(0, slow - 1);
    const prev = last; last = now;
    if (slow > 40) {
      ratioLevel++; slow = 0; st.info.level = ratioLevel;
      if (ratioLevel === 1) goLite(); else if (ratioLevel > 2) { fail(st, new Error('too slow')); return; }
    }
    frame(now, prev ? (now - prev) / 1000 : 0.033);
  };
  const requestFrame = () => {
    if (!reduced || pending || st.disposed) return;
    pending = true; requestAnimationFrame((n) => { pending = false; if (!st.disposed) frame(n, 1); });
  };
  const restart = () => {
    cancelAnimationFrame(st.raf);
    if (reduced) requestFrame(); else if (!document.hidden) st.raf = requestAnimationFrame(loop);
  };
  on(document, 'visibilitychange', restart);
  st.apply = () => { if (reduced) requestFrame(); };

  resize();
  frame(performance.now(), 0.033);
  setMode('3d');
  restart();
}

export default function (component) {
  const { data } = component;
  let st = window.__mcStage;
  if (st && st.v !== VERSION) { st.dispose(); st = null; }
  if (st && !st.disposed) { st.cancelDispose(); st.set(data); return st.makeCleanup(); }
  st = create(data);
  window.__mcStage = st;
  return st.makeCleanup();
}
