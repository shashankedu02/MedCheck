// MedCheck cinematic stage (core). Decorative only.
// Input: { phase: 'idle' | 'scanning' | 'result', status: 'alert' | 'unable' | 'no_alert' | 'error' | null }.
// It never receives a photo, text, batch number or record. Three.js is loaded from the local static folder only.
// Scanning is shown ONLY while the real OCR call runs (the phase is set by the Python script around pipeline.check()).
// stages.js (helpers + stage builders) is concatenated in front of this file by medcheck_ui/scene.py.
const VERSION = 6;
const ENGINE_URL = new URL('app/static/vendor/three/three.module.min.js', document.baseURI).href;
const SCENES = ['medicine', 'transformation', 'evidence', 'inspection', 'comparison'];
const TINT = { alert: [1.0, 0.62, 0.20], unable: [0.95, 0.76, 0.30], no_alert: [0.21, 0.82, 0.90], error: [0.55, 0.60, 0.67] };
const RIM = [0.13, 0.83, 0.93];
const SCAN_T = 3.98;                              // while the OCR runs the camera returns to the magnifier composition
const MAX_T_SPEED = 2.4;                          // the master clock never moves faster than this (scenes per second)

// Camera path through the five scenes: master clock t -> position, look-at, and a horizontal framing offset (used on wide screens
// so the caption on the left never covers the subject). Interpolated with a Catmull-Rom spline.
const KEYS = [
  { t: 0.0, p: [0.2, 0.35, 9.0], l: [0, 0.05, 0], ox: -2.3 },
  { t: 0.55, p: [-0.1, 0.2, 7.0], l: [0, 0.1, 0], ox: -1.8 },
  { t: 1.0, p: [1.2, 1.9, 8.8], l: [0, 1.5, 0], ox: -2.0 },
  { t: 1.5, p: [4.2, 2.2, 6.4], l: [0, 1.4, 0], ox: -1.6 },
  { t: 2.0, p: [5.2, 3.0, 3.6], l: [0, 2.2, -0.5], ox: -0.6 },
  { t: 2.35, p: [3.4, 3.6, 0.4], l: [0, 3.0, -6], ox: 0 },
  { t: 2.7, p: [1.6, 2.2, -2.5], l: [0, 0.6, -14], ox: 0 },
  { t: 3.0, p: [0, 0.6, -4.2], l: [0, 0.2, -18], ox: 0 },
  { t: 3.45, p: [0, 0.55, -15.5], l: [0, -0.1, -25.5], ox: 0 },
  { t: 3.75, p: [-0.3, 0.55, -18.0], l: [-0.2, -0.35, -25.2], ox: 0 },
  { t: 4.05, p: [-0.2, -0.05, -20.4], l: [-0.3, -0.55, -25.1], ox: 0 },
  { t: 4.4, p: [-0.1, 0.0, -20.0], l: [0, -0.5, -25], ox: 0 },
  { t: 4.75, p: [0, 0.4, -15.5], l: [0, 0.6, -23.5], ox: 0 },
  { t: 5.0, p: [0, 0.8, -10.5], l: [0, 1.15, -23.5], ox: 0 },        // panels sit low in frame, clear of the scene 5 caption
  { t: 5.5, p: [0, 1.2, -7.0], l: [0, 1.5, -23.5], ox: 0 },
];
const crom = (a, b, c, d, u) => 0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u);
function pathAt(t, out) {
  t = clamp(t, 0, KEYS[KEYS.length - 1].t);
  let i = 0; while (i < KEYS.length - 2 && t > KEYS[i + 1].t) i++;
  const k0 = KEYS[Math.max(i - 1, 0)], k1 = KEYS[i], k2 = KEYS[i + 1], k3 = KEYS[Math.min(i + 2, KEYS.length - 1)];
  const u = (t - k1.t) / (k2.t - k1.t);
  for (let c = 0; c < 3; c++) { out.p[c] = crom(k0.p[c], k1.p[c], k2.p[c], k3.p[c], u); out.l[c] = crom(k0.l[c], k1.l[c], k2.l[c], k3.l[c], u); }
  out.ox = crom(k0.ox, k1.ox, k2.ox, k3.ox, u);
}

function webglAvailable() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; }
}
function setMode(mode) { document.documentElement.setAttribute('data-mc-stage', mode); }

function create(data) {
  const st = { v: VERSION, disposed: false, timer: 0, raf: 0, undo: [], state: { phase: 'idle', status: null }, info: { frames: 0, level: 0 }, forceT: null };
  const on = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); st.undo.push(() => t.removeEventListener(ev, fn, o)); };
  st.calls = 0;
  st.set = (d) => {
    const prev = st.state.phase;
    st.state = { phase: (d && d.phase) || 'idle', status: (d && d.status) || null };
    document.documentElement.setAttribute('data-mc-phase', st.state.phase);
    if (st.hudText) st.hudText();
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
    document.querySelectorAll('.mc-scene').forEach((s) => s.style.removeProperty('--op'));
    if (window.__mcStage === st) delete window.__mcStage;
  };
  st.set(data);
  init(st, on).catch((e) => fail(st, e));
  return st;
}

function fail(st, e) {
  st.info.error = String(e && e.message || e);
  window.__mcLastError = st.info.error + ' | ' + String(e && e.stack || '').split('\n').slice(1, 4).join(' <- ');   // diagnostics only (never contains user data)
  st.dispose();
  setMode('fallback');          // the CSS shows the still artwork instead (after dispose, which resets the mode)
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
  renderer.shadowMap.autoUpdate = false;             // updated once per frame (the lens pass renders the scene a second time)
  renderer.setClearColor(0x000000, 0);
  on(canvas, 'webglcontextlost', (e) => { e.preventDefault(); fail(st, new Error('WebGL context lost')); });

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x061a3a, 0.028);
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 200);
  scene.add(camera);
  const disposables = [];
  const ctx = { THREE, renderer, scene, camera, pointMats: [], t: 0, time: 0, reduced, dt: 0.033,
    track: (o) => { disposables.push(o); return o; } };
  let hud = null, brackets = null;
  st.free = () => {
    scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { ['map', 'normalMap', 'bumpMap'].forEach((k) => { if (x[k]) x[k].dispose(); }); x.dispose(); });
    });
    disposables.forEach((d) => { try { d.dispose(); } catch (e) { /* ignore */ } });
    renderer.dispose(); renderer.forceContextLoss();
    canvas.remove(); if (hud) hud.remove(); if (brackets) brackets.remove();
    setMode('off');
  };

  // ---- image-based lighting built in code: a navy studio with long softboxes that streak across glass, foil and metal ----
  const pm = new THREE.PMREMGenerator(renderer);
  const room = new THREE.Scene();
  room.add(new THREE.Mesh(new THREE.BoxGeometry(26, 26, 26), new THREE.MeshBasicMaterial({ color: 0x0a1f40, side: THREE.BackSide })));
  const panel = (r, g, b, w, h, x, y, z) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.lookAt(0, 0, 0); room.add(m);
  };
  panel(6, 6, 6.5, 14, 2.2, 0, 9, 3);  panel(5, 5.4, 6, 12, 0.7, 0, 3.5, 9);
  panel(0.5, 3.6, 4.8, 2.5, 9, -10, 0, 3);  panel(2.6, 3.8, 5.2, 2.5, 7, 10, 1, 5);  panel(1.4, 2.2, 3.0, 12, 1.6, 0, -8, 4);
  const envTarget = ctx.track(pm.fromScene(room, 0.03));
  scene.environment = envTarget.texture;
  pm.dispose();
  room.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });

  // ---- lights: one rig for the medicine/water stage, one for the package stage; intensities follow the scene weights ----
  const keyA = new THREE.DirectionalLight(0xffffff, 2.4); keyA.position.set(3, 5, 4); scene.add(keyA);
  const rimA = new THREE.PointLight(new THREE.Color(...RIM), 42, 34, 1.6); rimA.position.set(-4, 2.5, 2.5); scene.add(rimA);
  const warmA = new THREE.PointLight(0xffa466, 14, 20, 1.8); warmA.position.set(4.5, 1.6, 3); scene.add(warmA);
  const spotB = new THREE.SpotLight(0xffffff, 0, 24, 0.72, 0.55, 1.5); spotB.position.set(-1.6, 3.6, -21.5); spotB.target.position.set(0, -0.3, -26);
  spotB.castShadow = true; spotB.shadow.mapSize.set(1024, 1024); spotB.shadow.bias = -0.0004; spotB.shadow.radius = 4;
  scene.add(spotB, spotB.target);
  const fillB = new THREE.PointLight(0x7fb6ff, 0, 14, 1.8); fillB.position.set(3.2, 1.0, -21); scene.add(fillB);

  // ---- stages ----
  const backdrop = buildBackdrop(THREE, ctx); scene.add(backdrop.mesh);
  const atm = buildAtmosphere(THREE, ctx); scene.add(atm.blobs); camera.add(atm.group);
  const capsule = buildCapsule(THREE, ctx); scene.add(capsule.group);
  const glassSt = buildGlass(THREE, ctx); scene.add(glassSt.group);
  const flow = buildFlow(THREE, ctx, glassSt); scene.add(flow.group);
  const carton = buildCarton(THREE, ctx); scene.add(carton.group, carton.world);
  const lens = buildLens(THREE, ctx); scene.add(lens.group, lens.light);
  const panels = buildPanels(THREE, ctx, carton); scene.add(panels.group);
  const stages = [capsule, glassSt, flow, carton, lens, panels];

  // ---- DOM overlays (they exist only while the 3D stage runs): brackets on the batch line, and the reading panel ----
  brackets = document.createElement('div'); brackets.id = 'mc-brackets'; brackets.setAttribute('aria-hidden', 'true');
  brackets.innerHTML = '<i></i><i></i><i></i><i></i>'; document.body.appendChild(brackets);
  hud = document.createElement('div'); hud.id = 'mc-hud'; hud.setAttribute('role', 'status');
  // the wording depends on where the app runs: a marker element (#mc-hosted) is rendered by the story when it is hosted
  const HUD_LOCAL = '<b>Reading the photo on this computer</b><span>Offline text recognition is reading it. This takes a few seconds.</span><em></em>';
  const HUD_HOSTED = '<b>Reading the photo on the hosting server</b><span>Text recognition is reading it. This takes a few seconds.</span><em></em>';
  st.hudText = () => { hud.innerHTML = document.getElementById('mc-hosted') ? HUD_HOSTED : HUD_LOCAL; };
  st.hudText();
  document.body.appendChild(hud);

  // ---- viewport ----
  const resize = () => {
    const w = Math.max(1, window.innerWidth), h = Math.max(1, window.innerHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    st.info.aspect = +camera.aspect.toFixed(3); st.info.canvasPx = [canvas.width, canvas.height];
    anchors = null; requestFrame();
  };
  on(window, 'resize', resize);

  // ---- scroll -> master clock: the five story sections give the breakpoints, measured from the real layout ----
  const scroller = () => document.querySelector('[data-testid="stMain"]');
  let anchors = null, anchorsAt = 0;
  const getAnchors = (now) => {
    if (anchors && now - anchorsAt < 350) return anchors;
    const sc = scroller(), secs = [...document.querySelectorAll('.mc-scene')];
    if (!sc || secs.length !== 5) return (anchors = null);
    const vh = window.innerHeight, base = sc.getBoundingClientRect().top, top0 = sc.scrollTop;
    const top = (el) => el.getBoundingClientRect().top - base + top0;
    const a = secs.map(top);
    const last = secs[4].getBoundingClientRect();
    a.push(Math.max(a[4] + 1, last.bottom - base + top0 - vh));          // t = 5 when the last scene's end reaches the bottom
    a.push(a[5] + vh * 0.75);                                            // t = 5.5 after the tool has risen into view
    for (let i = 1; i < a.length; i++) a[i] = Math.max(a[i], a[i - 1] + 1);
    anchorsAt = now; return (anchors = a);
  };
  const scrollT = (now) => {
    const sc = scroller(), A = getAnchors(now);
    if (!sc || !A) return 0;
    const s = sc.scrollTop;
    if (s <= A[0]) return 0;
    for (let i = 0; i < 6; i++) if (s <= A[i + 1]) return i + (s - A[i]) / (A[i + 1] - A[i]) * (i === 5 ? 0.5 : 1);
    return 5.5;
  };
  on(window, 'scroll', (e) => {
    const t = e.target;
    if (t !== document && !(t.getAttribute && t.getAttribute('data-testid') === 'stMain')) return;
    requestFrame();
  }, { capture: true, passive: true });
  const secs = () => [...document.querySelectorAll('.mc-scene')], dots = () => [...document.querySelectorAll('.mc-dots a')];
  const captions = (t) => {                                              // text fades follow the same clock
    secs().forEach((el, k) => {
      const f = clamp(t - k, 0, 1), inn = k === 0 ? 1 : smooth(f / 0.14), out = k === 4 ? 1 : 1 - smooth((f - 0.84) / 0.16);
      const v = (clamp(t - k + 0.0001, -1, 2) < 0 ? 0 : inn * out).toFixed(3);
      if (el.__op !== v) { el.__op = v; el.style.setProperty('--op', v); }
    });
    const idx = clamp(Math.floor(t + 0.02), 0, 4);
    dots().forEach((d, k) => d.classList.toggle('mc-on', k === idx));
    document.documentElement.style.setProperty('--mc-skip', (1 - smooth((t - 5.0) / 0.3)).toFixed(3));   // the skip link is not needed once the tool is reached
  };

  // ---- state ----
  const cur = { t: 0 };
  const path = { p: [0, 0, 0], l: [0, 0, 0], ox: 0 };
  let px = 0, py = 0, pxT = 0, pyT = 0, glowO = 0, ratioLevel = 0, lastRatio = 0, lite = false;
  const t0 = performance.now();
  const tint = new THREE.Color(...RIM), tmp = new THREE.Color(), v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), look = new THREE.Vector3();
  on(window, 'pointermove', (e) => { pxT = (e.clientX / window.innerWidth - 0.5) * 2; pyT = (e.clientY / window.innerHeight - 0.5) * 2; }, { passive: true });
  st.onResult = () => {                          // the verdict is where the user should look: ease the page to it
    st.resultAt = performance.now();
    setTimeout(() => {
      if (st.disposed || st.state.phase !== 'result') return;
      const a = [...document.querySelectorAll('[data-testid="stAlert"]')].find((x) => /^(Alert found|No alert found|Unable to verify|Expired|System error)/.test(x.innerText.trim()));
      if (a) a.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
    }, 650);
  };
  const ratio = () => (st.state.phase === 'scanning' ? 1 : Math.min(window.devicePixelRatio || 1, 1.5)) * (ratioLevel >= 2 ? 0.75 : ratioLevel === 1 ? 0.9 : 1);
  const goLite = () => {                          // governor step 2: cheaper glass and water, no shadows
    if (lite) return; lite = true;
    stages.forEach((s) => s.setLite && s.setLite());
    renderer.shadowMap.enabled = false; spotB.castShadow = false;
    scene.traverse((o) => { if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.needsUpdate = true; }); });
  };

  // the magnifier travels along the printed lines, then dwells on the batch line
  const lotY = toFace(0, TXT.rowsY[2] - 22)[1], lotX = toFace(40 + (TXT.valueStart + 3.5) * TXT.adv, 0)[0];
  const LENS_KEYS = [[3.3, -3.0, 1.2], [3.55, -1.8, 0.2], [3.8, 0.2, 0.0], [4.02, lotX, lotY + 0.02], [4.4, lotX + 0.35, lotY], [4.95, 3.0, 1.5]];
  const lensXY = (t, scanning, tm) => {
    if (scanning) return [lotX + (reduced ? 0 : Math.sin(tm * 1.25) * 1.15), lotY];
    let i = 0; while (i < LENS_KEYS.length - 2 && t > LENS_KEYS[i + 1][0]) i++;
    const a = LENS_KEYS[i], b = LENS_KEYS[i + 1], u = smooth((t - a[0]) / (b[0] - a[0]));
    return [lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
  };

  const cam2 = new THREE.PerspectiveCamera();
  const lensPass = (c, W, H) => {
    const L = lens, wasAtm = atm.group.visible;
    L.group.updateMatrixWorld(true); v1.copy(L.group.position).project(camera);
    const sx = (v1.x * 0.5 + 0.5) * W, sy = (-v1.y * 0.5 + 0.5) * H;
    v2.setFromMatrixColumn(camera.matrixWorld, 0).multiplyScalar(L.radius).add(L.group.position).project(camera);
    const rpx = Math.max(8, Math.abs((v2.x - v1.x) * 0.5 * W)), M = 2.4, sub = (2 * rpx) / M;
    cam2.copy(camera, false); cam2.aspect = camera.aspect; cam2.fov = camera.fov; cam2.near = camera.near; cam2.far = camera.far;
    cam2.setViewOffset(W, H, sx - sub / 2, sy - sub / 2, sub, sub);
    const k = (L.rt.width / sub) * (H / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))));
    ctx.pointMats.forEach((m) => { m.uniforms.uScale.value = k; });
    L.group.visible = false; atm.group.visible = false;
    renderer.setRenderTarget(L.rt); renderer.render(scene, cam2); renderer.setRenderTarget(null);
    L.group.visible = true; atm.group.visible = wasAtm;
  };

  const frame = (now, dt) => {      // (dt is reassigned below if it is not a finite number)
    const scanning = st.state.phase === 'scanning', res = st.state.phase === 'result';
    const tm = reduced ? 0 : (now - t0) / 1000;
    let tgt = st.forceT != null ? st.forceT : (scanning ? SCAN_T : scrollT(now));
    if (!Number.isFinite(tgt)) { st.info.badT = String(tgt); tgt = 0; }
    if (!Number.isFinite(dt)) { st.info.badDt = String(dt); dt = 0.033; }
    if (st.forceT != null || reduced) cur.t = tgt;
    else {                                   // inertia toward the scroll target, with a speed limit: a fast jump is a flight, never a cut
      const step = (tgt - cur.t) * (1 - Math.exp(-Math.min(dt, 0.25) * 5.5)), cap = (scanning ? 2 * MAX_T_SPEED : MAX_T_SPEED) * Math.min(dt, 0.1);
      cur.t += Math.abs(step) > cap ? Math.sign(step) * cap : step;
    }
    ctx.t = cur.t; ctx.time = tm; ctx.reduced = reduced; ctx.dt = dt;
    const W = window.innerWidth, H = window.innerHeight, wide = camera.aspect >= 1.1 ? 1 : 0;

    // camera
    pathAt(cur.t, path);
    px += (pxT - px) * 0.05; py += (pyT - py) * 0.05; const par = reduced ? 0 : 1;
    camera.position.set(path.p[0] + px * 0.35 * par, path.p[1] - py * 0.2 * par, path.p[2]);
    look.set(path.l[0] + path.ox * wide, path.l[1], path.l[2]);
    if (!wide) {                              // portrait: a portrait screen shows far less width, so the camera backs away along its view line
      const zoom = clamp(1.3 / camera.aspect, 1, 3.0);
      camera.position.sub(look).multiplyScalar(zoom).add(look);
    }
    camera.lookAt(look);

    // per-scene lighting weights
    const wA = Math.max(win(cur.t, -1, -1, 0.6, 1.3), win(cur.t, 0.6, 1.1, 2.4, 2.95)), wB = win(cur.t, 2.7, 3.3, 5.1, 5.8);
    keyA.intensity = 2.4 * wA; rimA.intensity = 42 * wA; warmA.intensity = 14 * wA * (1 - win(cur.t, 0.6, 1.1, 2.4, 2.9) * 0.6);
    spotB.intensity = 62 * wB; fillB.intensity = 8 * wB;

    // stages
    backdrop.update(ctx); atm.update(ctx);
    capsule.update(ctx); glassSt.update(ctx); flow.update(ctx); carton.update(ctx);

    // magnifier
    const lensVis = (cur.t > 3.28 && cur.t < 4.95 && carton.group.visible) || scanning;
    lens.group.visible = lensVis; lens.light.visible = lensVis; carton.glow.visible = lensVis;
    if (lensVis) {
      // The lens hovers 1.1 units in front of the package ON THE CAMERA'S RAY to the point being inspected, so the magnified
      // region is always exactly the printed text under the lens whatever the camera does (no parallax drift).
      const [lx, ly] = lensXY(cur.t, scanning, tm);
      v2.set(lx, ly + (carton.group.position.y - CARTON.y), FACE_Z + 0.01).sub(camera.position);
      const dist = v2.length(), hover = 1.1 + (reduced ? 0 : Math.sin(tm * 0.9) * 0.02);
      v2.normalize().multiplyScalar(Math.max(0.5, dist - hover)).add(camera.position);
      lens.group.position.copy(v2); lens.group.lookAt(camera.position);
      lens.light.position.set(lx, ly, FACE_Z + 1.0);
      const lw = Math.max(win(cur.t, 3.28, 3.5, 4.5, 4.9), scanning ? 1 : 0);
      lens.light.intensity = 0.5 * lw; carton.glow.position.set(lx, ly, FACE_Z + 0.002); carton.glow.material.opacity = 0.2 * lw;   // the glow sits under the printed ink
      lens.group.scale.setScalar(0.4 + 0.6 * lw);
    }
    panels.update(ctx);

    // the batch characters detach from the package in scene 5
    const dy = carton.group.position.y - CARTON.y, p = ctx.t;
    carton.chars.forEach((q, i) => {
      const lift = smooth(((p - 4.1) / 0.5) * 1.45 - i * 0.085), inkO = smooth((p - 3.2) / 0.3);
      const T = panels.tiles[i], a = q.print;
      q.m.position.set(lerp(a[0], T[0], lift), lerp(a[1] + dy, T[1], lift) + Math.sin(Math.PI * lift) * 0.5, lerp(a[2], T[2], lift) + Math.sin(Math.PI * lift) * 0.8);
      q.m.scale.setScalar(lerp(1, 1.4, lift));
      // ink #1c242d is a dark sRGB colour (about 0.012 linear); the characters turn cyan-white as they leave the pack
      q.m.material.color.setRGB(lerp(0.012, 0.6, lift), lerp(0.017, 0.93, lift), lerp(0.026, 1, lift));
      q.m.material.opacity = inkO * win(p, 3.0, 3.3, 5.8, 6.2);
      q.m.visible = carton.world.visible;
    });

    // result tint (a tint, never a verdict: no_alert is a calm cyan)
    const tc2 = res && TINT[st.state.status] ? TINT[st.state.status] : RIM;
    tint.setRGB(...tc2);
    const pulse = res && st.state.status === 'alert' && !reduced ? 0.5 + 0.5 * Math.sin(tm * 3.2) : 1;
    glowO += ((res ? 1 : 0) * (0.5 + 0.5 * pulse) - glowO) * 0.1;
    lens.ringMat.emissive.copy(tint); lens.ringMat.emissiveIntensity = glowO * 0.9 + (scanning ? 0.5 : 0);
    rimA.color.lerp(res ? tint : tmp.setRGB(...RIM), 0.06); lens.light.color.lerp(res ? tint : tmp.setRGB(...RIM), 0.1);
    canvas.style.opacity = (st.state.phase === 'scanning' ? 1 : lerp(1, 0.34, smooth((cur.t - 5.15) / 0.35))).toFixed(3);

    // brackets lock onto the printed batch line while scanning and for a moment after the result
    const showBr = (scanning || (res && st.resultAt && now - st.resultAt < 2600)) && carton.group.visible;
    if (showBr) {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const [px0, py0] of [[28, 196], [620, 196], [620, 268], [28, 268]]) {
        const w = toFace(px0, py0); v1.set(w[0], w[1] + dy, w[2]).project(camera);
        const sx = (v1.x * 0.5 + 0.5) * W, sy = (-v1.y * 0.5 + 0.5) * H;
        x0 = Math.min(x0, sx); y0 = Math.min(y0, sy); x1 = Math.max(x1, sx); y1 = Math.max(y1, sy);
      }
      Object.assign(brackets.style, { left: x0 + 'px', top: y0 + 'px', width: (x1 - x0) + 'px', height: (y1 - y0) + 'px', opacity: '1' });
      brackets.style.setProperty('--mc-tint', `${Math.round(tint.r * 255)},${Math.round(tint.g * 255)},${Math.round(tint.b * 255)}`);
      brackets.classList.toggle('mc-lock', !scanning);
    } else brackets.style.opacity = '0';
    captions(cur.t);

    // render: pass 1 draws the zoomed crop for the lens, pass 2 draws the scene
    const pr = ratio();
    if (pr !== lastRatio) { lastRatio = pr; renderer.setPixelRatio(pr); renderer.setSize(W, H, false); }
    const scale = renderer.domElement.height / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    renderer.shadowMap.needsUpdate = true;
    if (lensVis && (!lite || st.info.frames % 2 === 0)) lensPass(ctx, W, H);
    ctx.pointMats.forEach((m) => { m.uniforms.uScale.value = scale; });
    renderer.render(scene, camera);
    st.info.frames += 1; st.info.t = +cur.t.toFixed(3);
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
  st.stages = { capsule, glass: glassSt, flow, carton, lens, panels };
  st.goLite = goLite;                              // exposed so the lighter-quality tier can be exercised in tests

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
