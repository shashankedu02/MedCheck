// MedCheck 3D stage: a pharmaceutical blister strip. Decorative only.
// Input: { phase: 'idle' | 'scanning' | 'result', status: 'alert' | 'unable' | 'no_alert' | 'error' | null }.
// It never receives a photo, text, batch number or record. Three.js is loaded from the local static folder only.
const VERSION = 4;
const ENGINE_URL = new URL('app/static/vendor/three/three.module.min.js', document.baseURI).href;
const TINT = { alert: [1.0, 0.62, 0.20], unable: [0.95, 0.76, 0.30], no_alert: [0.21, 0.82, 0.90], error: [0.55, 0.60, 0.67] };
const RIM = [0.13, 0.83, 0.93];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

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
  st.set = (d) => { st.state = { phase: (d && d.phase) || 'idle', status: (d && d.status) || null }; if (st.apply) st.apply(); };
  st.calls = 0;
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
    if (window.__mcStage === st) delete window.__mcStage;
  };
  st.set(data);
  init(st, on).catch((e) => fail(st, e));
  return st;
}

function fail(st, e) {
  st.info.error = String(e && e.message || e);
  setMode('fallback');          // the CSS shows the SVG hero instead
  st.dispose();
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
  renderer.toneMappingExposure = 1.2;
  renderer.setClearColor(0x000000, 0);
  on(canvas, 'webglcontextlost', (e) => { e.preventDefault(); fail(st, new Error('WebGL context lost')); });

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 60);
  camera.position.set(0, 0, 11);

  // ---- image-based lighting built in code (no HDR file): a dark navy room with three light panels ----
  const pm = new THREE.PMREMGenerator(renderer);
  const room = new THREE.Scene();
  room.add(new THREE.Mesh(new THREE.BoxGeometry(24, 24, 24), new THREE.MeshBasicMaterial({ color: 0x0b2142, side: THREE.BackSide })));
  const panel = (r, g, b, w, h, x, y, z) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.lookAt(0, 0, 0); room.add(m);
  };
  panel(5, 5, 5.5, 10, 3, 0, 9, 3);
  panel(0.4, 3.2, 4.2, 3, 8, -9, 1, 3);
  panel(2.2, 3.4, 4.5, 3, 6, 9, 0, 5);
  const envTarget = pm.fromScene(room, 0.03);
  scene.environment = envTarget.texture;
  pm.dispose();
  room.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });

  const key = new THREE.DirectionalLight(0xffffff, 1.4); key.position.set(3, 5, 7); scene.add(key);
  const rim = new THREE.PointLight(new THREE.Color(...RIM), 38, 30, 1.6); rim.position.set(-5, 2, 3); scene.add(rim);

  // ---- the strip ----
  const strip = new THREE.Group();
  scene.add(strip);
  const roundRect = (w, h, r) => {
    const s = new THREE.Shape(); const x = -w / 2, y = -h / 2;
    s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0);
    s.lineTo(x + w, y + h - r); s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2);
    s.lineTo(x + r, y + h); s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
    s.lineTo(x, y + r); s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5); return s;
  };
  const W = 7.4, H = 2.9;
  const foil = new THREE.Mesh(
    new THREE.ExtrudeGeometry(roundRect(W, H, 0.26), { depth: 0.07, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 3, curveSegments: 18 }),
    new THREE.MeshStandardMaterial({ color: 0xd6dee9, metalness: 1, roughness: 0.24, envMapIntensity: 1.9 }));
  strip.add(foil);
  const sheet = new THREE.Mesh(
    new THREE.ShapeGeometry(roundRect(W - 0.1, H - 0.1, 0.24), 18),
    new THREE.MeshPhysicalMaterial({ color: 0xcfeeff, transparent: true, opacity: 0.1, roughness: 0.05, clearcoat: 1, depthWrite: false }));
  sheet.position.z = 0.115; strip.add(sheet);

  const domeGeo = new THREE.SphereGeometry(0.42, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2);
  domeGeo.scale(1.9, 0.75, 1); domeGeo.rotateX(Math.PI / 2);
  const domeMat = new THREE.MeshPhysicalMaterial({ color: 0xd2f3ff, transparent: true, opacity: 0.2, roughness: 0.04, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6, side: THREE.DoubleSide, depthWrite: false });
  const matCyan = new THREE.MeshPhysicalMaterial({ color: 0x14bfd8, roughness: 0.28, clearcoat: 1, side: THREE.DoubleSide });
  const matWhite = new THREE.MeshPhysicalMaterial({ color: 0xf2f8ff, roughness: 0.3, clearcoat: 1, side: THREE.DoubleSide });
  const cylGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.3, 28, 1, true);
  const capGeo = new THREE.SphereGeometry(0.2, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2);
  const half = (mat, dir) => {
    const g = new THREE.Group();
    const c = new THREE.Mesh(cylGeo, mat); c.rotation.z = Math.PI / 2; c.position.x = dir * 0.15;
    const s = new THREE.Mesh(capGeo, mat); s.rotation.z = -dir * Math.PI / 2; s.position.x = dir * 0.3;
    g.add(c, s); return g;
  };
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let row = 0; row < 2; row++) for (let col = 0; col < 4; col++) {
    const x = -2.625 + col * 1.75, y = 0.78 - row * 1.14;
    const dome = new THREE.Mesh(domeGeo, domeMat); dome.position.set(x, y, 0.08); dome.renderOrder = 2; strip.add(dome);
    const cap = new THREE.Group(); cap.add(half(matCyan, -1), half(matWhite, 1));
    cap.position.set(x, y, 0.065 + 0.2); cap.rotation.z = (rnd() - 0.5) * 0.16; strip.add(cap);
  }

  // printed batch band (decorative placeholder dots, not a real batch number)
  const tc = document.createElement('canvas'); tc.width = 1536; tc.height = 160;
  const g2 = tc.getContext('2d');
  g2.fillStyle = '#26323f'; g2.font = '600 74px "Segoe UI Variable Text","Segoe UI",sans-serif'; g2.textBaseline = 'middle';
  g2.fillText('B.No. •••••••   Exp •• / ••••', 40, 84);
  const printTex = new THREE.CanvasTexture(tc); printTex.colorSpace = THREE.SRGBColorSpace;
  printTex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const bandBg = new THREE.Mesh(new THREE.PlaneGeometry(6.9, 0.56), new THREE.MeshBasicMaterial({ color: 0xc9d4e1, transparent: true, opacity: 0.88 }));
  bandBg.position.set(0, -1.12, 0.092); strip.add(bandBg);   // a light printed label area so the batch line reads on the dark foil
  const band = new THREE.Mesh(new THREE.PlaneGeometry(6.8, 0.52), new THREE.MeshBasicMaterial({ map: printTex, transparent: true }));
  band.position.set(0, -1.12, 0.1); strip.add(band);
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(7.0, 0.66), new THREE.MeshBasicMaterial({ color: 0x35d0e6, transparent: true, opacity: 0, depthWrite: false }));
  glow.position.set(0, -1.12, 0.09); strip.add(glow);

  // scanning beam
  const bc = document.createElement('canvas'); bc.width = 256; bc.height = 4;
  const g3 = bc.getContext('2d'); const grad = g3.createLinearGradient(0, 0, 256, 0);
  grad.addColorStop(0, 'rgba(34,211,238,0)'); grad.addColorStop(0.5, 'rgba(180,245,255,1)'); grad.addColorStop(1, 'rgba(34,211,238,0)');
  g3.fillStyle = grad; g3.fillRect(0, 0, 256, 4);
  const beamTex = new THREE.CanvasTexture(bc);
  const beam = new THREE.Mesh(new THREE.PlaneGeometry(0.7, H + 0.5), new THREE.MeshBasicMaterial({ map: beamTex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
  beam.position.z = 0.5; strip.add(beam);

  // ---- layout that follows the viewport (resize + camera aspect) ----
  const target = { x: 0, y: 0, s: 1 };
  const tint = new THREE.Color(...RIM);
  const resize = () => {
    const w = Math.max(1, window.innerWidth), h = Math.max(1, window.innerHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    const halfH = camera.position.z * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)), halfW = halfH * camera.aspect;
    const wide = camera.aspect >= 1.1;
    const widthShare = wide ? 0.38 : 0.9;   // wide: the strip lives in the right part of the screen, clear of the hero text
    target.s = clamp((widthShare * 2 * halfW) / W, 0.25, 1.5);
    target.x = wide ? halfW * 0.56 : 0;
    target.y = wide ? halfH * 0.02 : halfH * 0.5;
    strip.scale.setScalar(target.s); strip.position.x = target.x; strip.position.y = target.y;
    st.info.aspect = +camera.aspect.toFixed(3); st.info.canvasPx = [canvas.width, canvas.height]; st.info.stripScale = +target.s.toFixed(3);
    requestFrame();
  };
  on(window, 'resize', resize);

  // ---- state ----
  let scrollP = 0, yaw = 0.4, bob = 0, beamPhase = 0, glowO = 0, canvasO = 1, ratioLevel = 0, lastRatio = 0, t0 = performance.now();
  const scroller = () => document.querySelector('[data-testid="stMain"]');
  on(window, 'scroll', (e) => {
    const t = e.target; const el = t === document ? document.scrollingElement : t;
    if (!el || (el.getAttribute && el.getAttribute('data-testid') !== 'stMain' && t !== document)) return;
    scrollP = clamp(el.scrollTop / Math.max(1, window.innerHeight * 0.9), 0, 1);
    requestFrame();
  }, { capture: true, passive: true });

  const ratio = () => (st.state.phase === 'scanning' ? 1 : Math.min(window.devicePixelRatio || 1, 1.5)) * (ratioLevel >= 2 ? 0.75 : ratioLevel === 1 ? 0.9 : 1);
  const frame = (now) => {
    const scanning = st.state.phase === 'scanning', res = st.state.phase === 'result';
    const tt = (now - t0) / 1000;
    const tgtYaw = scanning ? 0.12 : 0.4 + (reduced ? 0 : Math.sin(tt * 0.35) * 0.3) + scrollP * 0.55;
    yaw += (tgtYaw - yaw) * 0.08;
    bob = reduced ? 0 : Math.sin(tt * 0.9) * 0.06;
    strip.rotation.y = yaw; strip.rotation.x = 0.16 + scrollP * 0.1; strip.position.y = target.y + bob;
    if (scanning) {
      beamPhase = reduced ? 0.5 : (tt * 0.55) % 1;
      beam.material.opacity = 0.7;
    } else {
      beamPhase = ((tt * 0.16) % 1);                       // a slow, faint pass while idle (hero)
      beam.material.opacity = reduced || res ? 0 : (beamPhase < 0.5 ? Math.sin(beamPhase * 2 * Math.PI) * 0.22 : 0);
    }
    beam.position.x = (beamPhase * 2 - 1) * (W / 2 - 0.4) * (scanning || !res ? 1 : 0);
    // result tint: a steady glow behind the batch band; only alert pulses, and never when motion is reduced
    const tc2 = res && TINT[st.state.status] ? TINT[st.state.status] : RIM;
    tint.setRGB(...tc2);
    const pulse = res && st.state.status === 'alert' && !reduced ? 0.5 + 0.5 * Math.sin(tt * 3.2) : 1;
    const gl = res ? (st.state.status === 'no_alert' ? 0.25 : st.state.status === 'error' ? 0.18 : 0.45 * (0.55 + 0.45 * pulse)) : scanning ? 0.18 : 0;
    glowO += (gl - glowO) * 0.1; glow.material.opacity = glowO; glow.material.color.copy(scanning ? new THREE.Color(...RIM) : tint);
    rim.color.lerp(res ? tint : new THREE.Color(...RIM), 0.06);
    canvasO += ((1 - 0.72 * scrollP) - canvasO) * 0.12; canvas.style.opacity = canvasO.toFixed(3);
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
    // quality governor: if frames arrive far slower than the cap, lower the resolution; if still slow, give up (SVG hero)
    if (last && dt > cap * 2.2) slow++; else slow = Math.max(0, slow - 1);
    last = now;
    if (slow > 40) { ratioLevel++; slow = 0; st.info.level = ratioLevel; if (ratioLevel > 2) { fail(st, new Error('too slow')); return; } }
    frame(now);
  };
  const requestFrame = () => {
    if (!reduced || pending || st.disposed) return;
    pending = true; requestAnimationFrame((n) => { pending = false; if (!st.disposed) frame(n); });
  };
  const restart = () => {
    cancelAnimationFrame(st.raf);
    if (reduced) requestFrame(); else if (!document.hidden) st.raf = requestAnimationFrame(loop);
  };
  on(document, 'visibilitychange', restart);
  st.apply = () => { if (reduced) requestFrame(); };

  st.free = () => {
    scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { if (x.map) x.map.dispose(); x.dispose(); });
    });
    [domeGeo, cylGeo, capGeo].forEach((x) => x.dispose());
    printTex.dispose(); beamTex.dispose(); envTarget.dispose();
    renderer.dispose(); renderer.forceContextLoss();
    canvas.remove();
    setMode('off');
  };

  resize();
  frame(performance.now());
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
