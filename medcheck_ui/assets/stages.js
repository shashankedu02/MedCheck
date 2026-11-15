// ===== MedCheck cinematic stages (decorative; no data ever enters here) =====
// Five connected stages in ONE persistent scene. Everything is a pure function of the master clock t (0..5), so scrolling
// backwards or quickly is always coherent. Concatenated with scene.js (the core) into one ES module by medcheck_ui/scene.py.
const TAU = Math.PI * 2;
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (u) => { u = clamp(u, 0, 1); return u * u * (3 - 2 * u); };
const lerp = (a, b, u) => a + (b - a) * u;
const win = (t, a, b, c, d) => (t <= a || t >= d ? 0 : t < b ? smooth((t - a) / (b - a)) : t <= c ? 1 : smooth((d - t) / (d - c)));
function makeRand(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function mkCanvas(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), c); return c; }

// Illustrative placeholder text shown on the carton and in the evidence scene. It is NOT a real batch number: a test checks it
// is absent from (and far from) the CDSCO dataset. The characters are placed on a fixed monospace grid.
const TXT = { W: 640, H: 320, adv: 42, rowsY: [78, 168, 258], lines: ['Mfd.  01/2026', 'Exp.  12/2028', 'Lot.  XQ240001'], valueStart: 6, font: '700 62px Consolas, "Courier New", monospace' };
function drawText(g, color, skipBatch, w, scale = 1) {
  g.setTransform(scale, 0, 0, scale, 0, 0);
  g.fillStyle = color; g.font = TXT.font; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
  TXT.lines.forEach((line, r) => {
    for (let i = 0; i < line.length; i++) {
      if (line[i] === ' ' || (skipBatch && r === 2 && i >= TXT.valueStart)) continue;
      g.fillText(line[i], 40 + i * TXT.adv + TXT.adv / 2, TXT.rowsY[r], w);
    }
  });
}
function textSamples() {                         // glyph pixel positions used by the particles
  const c = mkCanvas(TXT.W, TXT.H, (g) => drawText(g, '#fff', false));
  const d = c.getContext('2d').getImageData(0, 0, TXT.W, TXT.H).data, pts = [];
  for (let y = 0; y < TXT.H; y += 2) for (let x = 0; x < TXT.W; x += 2) if (d[(y * TXT.W + x) * 4 + 3] > 140) pts.push([x, y]);
  return pts;
}

// World layout
const SC = 0.0046;                                   // world units per text-bitmap pixel on the carton
const CARTON = { x: 0, y: -0.2, z: -26, w: 5.4, h: 1.6, d: 2.0 };
const FACE_Z = CARTON.z + CARTON.d / 2;
const toFace = (px, py, dz = 0.006) => [CARTON.x - 2.35 + px * SC, CARTON.y + 0.68 - py * SC, FACE_Z + dz];
const PLANE_A = [-3.0, 0.25, -18], PLANE_B = [3.0, 0.25, -18], PS = 0.00625;   // evidence text planes
const toPlane = (P, px, py) => [P[0] + (px - TXT.W / 2) * PS, P[1] + (TXT.H / 2 - py) * PS, P[2]];
const PANEL_L = [-2.75, 0.15, -23.5], PANEL_R = [2.75, 0.15, -23.5];

// ---- point sprites with per-point size/alpha/colour (one ShaderMaterial for all sprite layers) ----
const SPRITE_VS = `attribute float aSize; attribute float aAlpha; attribute vec3 aColor; uniform float uScale; varying float vA; varying vec3 vC;
void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv; gl_PointSize = aSize * uScale / max(0.1, -mv.z); vA = aAlpha; vC = aColor; }`;
const SPRITE_FS = `uniform sampler2D uMap; varying float vA; varying vec3 vC;
void main(){ vec4 t = texture2D(uMap, gl_PointCoord); gl_FragColor = vec4(vC * t.rgb, t.a * vA); }`;
function sprites(THREE, ctx, n, tex, blending) {
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(n * 3), size = new Float32Array(n).fill(0.05), alpha = new Float32Array(n), col = new Float32Array(n * 3).fill(1);
  const A = (arr, k, name) => { const a = new THREE.BufferAttribute(arr, k); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); };
  A(pos, 3, 'position'); A(size, 1, 'aSize'); A(alpha, 1, 'aAlpha'); A(col, 3, 'aColor');
  const mat = new THREE.ShaderMaterial({ uniforms: { uMap: { value: tex }, uScale: { value: 800 } }, vertexShader: SPRITE_VS, fragmentShader: SPRITE_FS,
    transparent: true, depthWrite: false, blending });
  const pts = new THREE.Points(g, mat); pts.frustumCulled = false;
  ctx.pointMats.push(mat);
  const touch = () => ['position', 'aSize', 'aAlpha', 'aColor'].forEach((k) => { g.attributes[k].needsUpdate = true; });
  return { pts, pos, size, alpha, col, n, touch, g, mat };
}
const discTex = (THREE, ctx, ring) => ctx.track(new THREE.CanvasTexture(mkCanvas(64, 64, (g) => {
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  if (ring) { gr.addColorStop(0, 'rgba(180,225,255,0.04)'); gr.addColorStop(0.72, 'rgba(190,230,255,0.18)'); gr.addColorStop(0.88, 'rgba(235,248,255,0.95)'); gr.addColorStop(1, 'rgba(235,248,255,0)'); }
  else { gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(190,235,255,0.55)'); gr.addColorStop(1, 'rgba(120,210,255,0)'); }
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  if (ring) { g.fillStyle = 'rgba(255,255,255,0.9)'; g.beginPath(); g.arc(22, 21, 4.5, 0, TAU); g.fill(); }
})));

// ---- backdrop: an opaque sphere that follows the camera (so glass and water can refract it) ----
function buildBackdrop(THREE, ctx) {
  const rnd = makeRand(3);
  const bokeh = (g, w, h, n, palette, rMin, rMax) => {
    for (let i = 0; i < n; i++) {
      const x = rnd() * w, y = rnd() * h, r = rMin + rnd() * (rMax - rMin), c = palette[Math.floor(rnd() * palette.length)];
      const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, c[0]); gr.addColorStop(0.72, c[1]); gr.addColorStop(1, c[2]);
      g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
    }
  };
  const dark = mkCanvas(1024, 512, (g, c) => {
    const gr = g.createLinearGradient(0, 0, 0, c.height); gr.addColorStop(0, '#07173a'); gr.addColorStop(0.55, '#06142b'); gr.addColorStop(1, '#040d1f');
    g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
    bokeh(g, c.width, c.height, 16, [['rgba(40,110,255,0.26)', 'rgba(30,90,230,0.14)', 'rgba(30,90,230,0)']], 40, 120);
    bokeh(g, c.width, c.height, 9, [['rgba(255,176,96,0.5)', 'rgba(255,150,80,0.28)', 'rgba(255,150,80,0)']], 18, 54);
  });
  const bright = mkCanvas(1024, 512, (g, c) => {
    const gr = g.createLinearGradient(0, 0, 0, c.height);   // bright above the horizon, falling to the deep navy of the table below it
    gr.addColorStop(0, '#0b5aa8'); gr.addColorStop(0.3, '#1d86cf'); gr.addColorStop(0.44, '#0f5aa6'); gr.addColorStop(0.52, '#07224a'); gr.addColorStop(0.6, '#06142b'); gr.addColorStop(1, '#040d1f');
    g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
    const cl = g.createRadialGradient(512, 190, 0, 512, 190, 330); cl.addColorStop(0, 'rgba(210,240,255,0.8)'); cl.addColorStop(1, 'rgba(210,240,255,0)');
    g.fillStyle = cl; g.fillRect(0, 0, c.width, c.height * 0.52);
    bokeh(g, c.width, c.height * 0.5, 64, [['rgba(150,215,255,0.55)', 'rgba(120,200,255,0.3)', 'rgba(120,200,255,0)'], ['rgba(40,120,220,0.5)', 'rgba(30,100,200,0.25)', 'rgba(30,100,200,0)']], 14, 70);
  });
  const mk = (c) => { const t = ctx.track(new THREE.CanvasTexture(c)); t.colorSpace = THREE.SRGBColorSpace; return t; };
  const mat = new THREE.ShaderMaterial({
    uniforms: { a: { value: mk(dark) }, b: { value: mk(bright) }, mixv: { value: 0 }, tint: { value: new THREE.Color(1, 1, 1) } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform sampler2D a; uniform sampler2D b; uniform float mixv; uniform vec3 tint; varying vec2 vUv; void main(){ gl_FragColor = vec4(mix(texture2D(a, vUv).rgb, texture2D(b, vUv).rgb, mixv) * tint, 1.0);\n#include <tonemapping_fragment>\n#include <colorspace_fragment>\n}',
    side: THREE.BackSide, depthWrite: false, fog: false });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(70, 48, 24), mat); mesh.renderOrder = -10; mesh.frustumCulled = false;
  return { mesh, update: (c) => { mesh.position.copy(c.camera.position); mesh.rotation.y = c.t * 0.12; mat.uniforms.mixv.value = win(c.t, 0.55, 1.15, 2.15, 2.7); } };
}

// ---- foreground bokeh (attached to the camera) and soft out-of-focus capsules (scene 1 depth) ----
function buildAtmosphere(THREE, ctx) {
  const g = new THREE.Group();
  const fg = sprites(THREE, ctx, 42, discTex(THREE, ctx, false), THREE.AdditiveBlending), r = makeRand(8);
  const base = [];
  for (let i = 0; i < fg.n; i++) {
    base.push([(r() - 0.5) * 11, (r() - 0.5) * 6.5, -3.5 - r() * 7, r()]);
    fg.size[i] = 0.5 + r() * 1.7;
    const warm = r() < 0.35; fg.col[i * 3] = warm ? 1 : 0.35; fg.col[i * 3 + 1] = warm ? 0.66 : 0.62; fg.col[i * 3 + 2] = warm ? 0.38 : 1;
  }
  g.add(fg.pts);
  const blobTex = ctx.track(new THREE.CanvasTexture(mkCanvas(256, 128, (c) => {
    c.filter = 'blur(10px)'; const gr = c.createLinearGradient(30, 0, 226, 0); gr.addColorStop(0, '#9fd8ff'); gr.addColorStop(0.5, '#3a8cff'); gr.addColorStop(1, '#1b4fd8');
    c.fillStyle = gr; c.beginPath(); c.roundRect(34, 36, 188, 56, 28); c.fill();
  })));
  const blobs = new THREE.Group();
  [[-4.2, 1.6, -5.5, 0.6, 3.2], [3.8, -1.4, -6.5, -0.9, 3.8], [-2.2, -2.2, -4.5, 0.3, 2.4], [5.2, 2.2, -8, -0.4, 4.4], [0.6, 3.1, -9, 0.8, 3.6]].forEach(([x, y, z, rot, s]) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s / 2), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    m.position.set(x, y, z); m.rotation.z = rot; blobs.add(m);
  });
  return { fg, blobs, group: g,
    update: (c) => {
      const w1 = win(c.t, -1, -1, 0.6, 1.3), w2 = win(c.t, 0.6, 1.1, 2.3, 2.9);
      blobs.visible = w1 > 0.002; blobs.children.forEach((m, i) => { m.material.opacity = 0.34 * w1; m.rotation.z += c.reduced ? 0 : 0.0006 * (i % 2 ? 1 : -1); });
      const a = (0.5 * Math.max(w1, w2) + 0.14) * (1 - win(c.t, 3.0, 3.4, 5.0, 5.2) * 0.7);
      for (let i = 0; i < fg.n; i++) {
        const b = base[i], tm = c.reduced ? 0 : c.time;
        fg.pos[i * 3] = b[0] + Math.sin(tm * 0.1 + i) * 0.4; fg.pos[i * 3 + 1] = ((b[1] + tm * 0.05 * (0.4 + b[3]) + 3.25) % 6.5) - 3.25; fg.pos[i * 3 + 2] = b[2];
        fg.alpha[i] = a * (0.25 + 0.6 * b[3]);
      }
      fg.touch();
    } };
}

// ---- scene 1: the glass capsule ----
function buildCapsule(THREE, ctx) {
  const g = new THREE.Group();
  const R = 0.5, L = 1.5;
  const glass = new THREE.MeshPhysicalMaterial({ color: 0xd6e8ff, metalness: 0, roughness: 0.03, transmission: 1, thickness: 0.55, ior: 1.5,
    attenuationColor: new THREE.Color(0x3b78ff), attenuationDistance: 1.3, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.7, specularIntensity: 1 });
  const lite = new THREE.MeshPhysicalMaterial({ color: 0xbcd6ff, transparent: true, opacity: 0.28, roughness: 0.04, clearcoat: 1, envMapIntensity: 1.7, depthWrite: false });
  const outer = new THREE.Mesh(new THREE.CapsuleGeometry(R, L, 16, 56), glass);
  const inner = new THREE.Mesh(new THREE.CapsuleGeometry(R * 0.84, L * 0.92, 16, 48),   // translucent gel so the glitter inside stays visible
    new THREE.MeshPhysicalMaterial({ color: 0x0a2b9e, roughness: 0.22, metalness: 0.15, clearcoat: 1, emissive: 0x0a2fb8, emissiveIntensity: 0.5, envMapIntensity: 1.1, transparent: true, opacity: 0.74, depthWrite: false }));
  inner.renderOrder = 1;
  const seam = new THREE.Mesh(new THREE.TorusGeometry(R + 0.012, 0.02, 16, 72), glass); seam.rotation.x = Math.PI / 2;
  g.add(inner, outer, seam);
  const glitter = sprites(THREE, ctx, 950, discTex(THREE, ctx, false), THREE.AdditiveBlending), r = makeRand(17), gp = [];
  glitter.pts.renderOrder = 2;
  for (let i = 0; i < glitter.n; i++) {
    let x, y, z; do { x = (r() - 0.5) * 2 * R * 0.8; z = (r() - 0.5) * 2 * R * 0.8; } while (x * x + z * z > (R * 0.8) ** 2);
    y = (r() - 0.5) * (L + R * 1.2); gp.push([x, y, z, r()]);
    glitter.pos[i * 3] = x; glitter.pos[i * 3 + 1] = y; glitter.pos[i * 3 + 2] = z; glitter.size[i] = 0.03 + r() * 0.06;
    glitter.col[i * 3] = 0.75; glitter.col[i * 3 + 1] = 0.9; glitter.col[i * 3 + 2] = 1;
  }
  g.add(glitter.pts);
  g.position.set(0, 0.05, 0); g.rotation.z = 0.78;
  return { group: g, setLite: () => { outer.material = lite; seam.material = lite; },
    update: (c) => {
      const w = win(c.t, -1, -1, 0.55, 1.2);
      g.visible = w > 0.002; if (!g.visible) return;
      const tm = c.reduced ? 0 : c.time;
      g.rotation.y = tm * 0.22 + c.t * 0.9; g.position.y = 0.05 + Math.sin(tm * 0.8) * 0.06 - smooth((c.t - 0.55) / 0.65) * 0.9;
      g.scale.setScalar(lerp(1, 0.55, smooth((c.t - 0.55) / 0.65)));
      for (let i = 0; i < glitter.n; i++) glitter.alpha[i] = 0.35 + 0.65 * Math.abs(Math.sin(tm * (1.4 + gp[i][3] * 2) + gp[i][3] * 40));
      glitter.touch();
    } };
}

// ---- scene 2: glass of water, effervescent tablet, bubbles, dissolving particles ----
const TAB = (t) => {                                // tablet state (pure function of t)
  const f = t - 1;
  const drop = smooth((f - 0.08) / 0.55);
  const y = lerp(3.9, 0.62, 1 - Math.pow(1 - drop, 2.2));
  const d = smooth((t - 1.28) / 0.66);              // dissolve 0..1
  const e = smooth((t - 1.18) / 0.12) * (1 - smooth((t - 2.0) / 0.4));   // fizz intensity
  return { y, d, e, x: 0.16 * Math.sin(f * 9) * (1 - drop * 0.6), z: 0.1 * Math.cos(f * 7) * (1 - drop * 0.6), rx: 0.5 + f * 2.6, rz: f * 1.9, s: 1 - 0.94 * Math.pow(d, 1.25) };
};
function buildGlass(THREE, ctx) {
  const g = new THREE.Group();
  const prof = [[0, 0], [0.7, 0], [0.8, 0.03], [0.84, 0.12], [0.98, 3.0], [0.95, 3.035], [0.92, 3.0], [0.76, 0.3], [0, 0.3]].map(([r, y]) => new THREE.Vector2(r, y));
  const glassMat = new THREE.MeshPhysicalMaterial({ color: 0xdaf0ff, transparent: true, opacity: 0.16, roughness: 0.02, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02,
    envMapIntensity: 2.4, side: THREE.DoubleSide, depthWrite: false });
  const glass = new THREE.Mesh(new THREE.LatheGeometry(prof, 72), glassMat); glass.renderOrder = 5;
  const waterMat = new THREE.MeshPhysicalMaterial({ color: 0x8fd0ff, metalness: 0, roughness: 0.02, transmission: 0.97, thickness: 1.8, ior: 1.33,
    attenuationColor: new THREE.Color(0x1d7fe0), attenuationDistance: 1.8, envMapIntensity: 1.3, depthWrite: false });
  const waterLite = new THREE.MeshPhysicalMaterial({ color: 0x4aa8ee, transparent: true, opacity: 0.32, roughness: 0.03, envMapIntensity: 1.2, depthWrite: false });
  const water = new THREE.Mesh(new THREE.CylinderGeometry(0.905, 0.755, 2.0, 72, 1, false), waterMat); water.position.y = 1.3; water.renderOrder = 1;
  const rip = ctx.track(new THREE.CanvasTexture(mkCanvas(256, 256, (c) => {
    const id = c.createImageData(256, 256), r = makeRand(31);
    for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) { const v = 128 + 50 * Math.sin(x * 0.18 + Math.sin(y * 0.11) * 2) * Math.cos(y * 0.15) + (r() - 0.5) * 18; const k = (y * 256 + x) * 4; id.data[k] = v; id.data[k + 1] = 128 + 40 * Math.cos(x * 0.13 + y * 0.09); id.data[k + 2] = 255; id.data[k + 3] = 255; }
    c.putImageData(id, 0, 0);
  })));
  rip.wrapS = rip.wrapT = THREE.RepeatWrapping; rip.repeat.set(2, 2);
  const surf = new THREE.Mesh(new THREE.CircleGeometry(0.905, 72), new THREE.MeshPhysicalMaterial({ color: 0xbfe4ff, transparent: true, opacity: 0.5, roughness: 0.05, normalMap: rip, normalScale: new THREE.Vector2(0.5, 0.5), clearcoat: 1, envMapIntensity: 1.8, depthWrite: false, side: THREE.DoubleSide }));
  surf.rotation.x = -Math.PI / 2; surf.position.y = 2.3; surf.renderOrder = 2;
  const foamTex = ctx.track(new THREE.CanvasTexture(mkCanvas(256, 256, (c) => {
    const r = makeRand(41);
    for (let i = 0; i < 260; i++) { const x = r() * 256, y = r() * 256, rad = 3 + r() * 11; const gr = c.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, 'rgba(255,255,255,0.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = gr; c.beginPath(); c.arc(x, y, rad, 0, TAU); c.fill(); }
  })));
  const foam = new THREE.Mesh(new THREE.CircleGeometry(0.86, 64), new THREE.MeshBasicMaterial({ map: foamTex, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, fog: false }));
  foam.rotation.x = -Math.PI / 2; foam.position.y = 2.306; foam.renderOrder = 3;
  const table = new THREE.Mesh(new THREE.CircleGeometry(16, 64), new THREE.MeshStandardMaterial({ color: 0x0b1d3a, roughness: 0.16, metalness: 0.7, envMapIntensity: 1.1 }));
  table.rotation.x = -Math.PI / 2; table.position.y = -0.002;
  const tabGeo = new THREE.LatheGeometry([[0, 0.065], [0.33, 0.065], [0.4, 0.05], [0.425, 0], [0.4, -0.05], [0.33, -0.065], [0, -0.065]].map(([r, y]) => new THREE.Vector2(r, y)), 40);
  const bump = ctx.track(new THREE.CanvasTexture(mkCanvas(128, 128, (c) => { const r = makeRand(5); for (let i = 0; i < 1400; i++) { const v = 90 + r() * 120; c.fillStyle = `rgb(${v},${v},${v})`; c.fillRect(r() * 128, r() * 128, 2, 2); } })));
  const tablet = new THREE.Mesh(tabGeo, new THREE.MeshStandardMaterial({ color: 0xeef3f8, roughness: 0.62, bumpMap: bump, bumpScale: 1.4, envMapIntensity: 0.7 }));
  const bubS = sprites(THREE, ctx, 240, discTex(THREE, ctx, true), THREE.NormalBlending), bubL = sprites(THREE, ctx, 60, discTex(THREE, ctx, true), THREE.NormalBlending);
  const dis = sprites(THREE, ctx, 2400, discTex(THREE, ctx, false), THREE.AdditiveBlending);
  [bubS, bubL].forEach((b) => { b.pts.renderOrder = 6; });
  dis.pts.renderOrder = 6;
  const rr = makeRand(77), bs = [], bl = [];
  for (let i = 0; i < bubS.n; i++) { bs.push([rr() * TAU, Math.sqrt(rr()), 0.5 + rr(), rr(), 0.6 + rr() * 1.2]); bubS.size[i] = 0.05 + rr() * 0.05; }
  for (let i = 0; i < bubL.n; i++) { bl.push([rr() * TAU, Math.sqrt(rr()), 0.4 + rr() * 0.6, rr(), 0.5 + rr()]); bubL.size[i] = 0.11 + rr() * 0.09; }
  g.add(table, glass, water, surf, foam, tablet, bubS.pts, bubL.pts);
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(1.6, 48), new THREE.MeshBasicMaterial({ map: ctx.track(new THREE.CanvasTexture(mkCanvas(128, 128, (c) => { const gr = c.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(0,0,0,0.6)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = gr; c.fillRect(0, 0, 128, 128); }))), transparent: true, depthWrite: false, fog: false }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.003; g.add(shadow);
  return { group: g, dis, setLite: () => { water.material = waterLite; },
    update: (c) => {
      const w = win(c.t, 0.55, 1.1, 2.3, 2.85);
      g.visible = w > 0.002; dis.pts.visible = c.t > 1.1 && c.t < 3.75;
      if (g.visible) {
        const S = TAB(c.t), tm = c.reduced ? 0 : c.time;
        tablet.position.set(S.x, S.y, S.z); tablet.rotation.set(S.rx, 0, S.rz); tablet.scale.setScalar(Math.max(0.0001, S.s)); tablet.visible = S.s > 0.04 && S.y < 4.2;
        const waterTop = 2.3, inWater = S.y < waterTop;
        rip.offset.x = tm * 0.012; rip.offset.y = tm * 0.008;
        foam.material.opacity = 0.62 * smooth((c.t - 1.4) / 0.4) * (1 - smooth((c.t - 2.2) / 0.5)) * (0.8 + 0.2 * Math.sin(tm * 2));
        waterMat.attenuationColor.setRGB(lerp(0.17, 0.5, S.d * 0.6), lerp(0.56, 0.78, S.d * 0.5), lerp(0.9, 0.98, S.d * 0.5));
        const emit = inWater ? S.e : 0;
        [[bubS, bs, 1.3], [bubL, bl, 0.9]].forEach(([b, arr]) => {
          for (let i = 0; i < b.n; i++) {
            const a = arr[i], ph = (tm * 0.35 * a[2] + a[3]) % 1, rise = Math.pow(ph, 0.9);
            const y0 = Math.max(0.35, S.y), y = y0 + (waterTop - y0) * rise, rad = 0.06 + a[1] * (0.12 + 0.5 * rise) * (0.4 + S.d * 0.6);
            b.pos[i * 3] = S.x + Math.cos(a[0] + tm * a[4] * 0.5) * rad; b.pos[i * 3 + 1] = y; b.pos[i * 3 + 2] = S.z + Math.sin(a[0] + tm * a[4] * 0.5) * rad;
            b.alpha[i] = emit * (ph < 0.97 ? 0.9 : 0) * (i / b.n < 0.25 + emit * 0.75 ? 1 : 0);
          }
          b.touch();
        });
      } else { bubS.alpha.fill(0); bubL.alpha.fill(0); bubS.touch(); bubL.touch(); }
    } };
}

// ---- scenes 2 -> 3 -> 4: ONE particle flow (swirl, exit, rows, glyphs, print) with two reader beams ----
function buildFlow(THREE, ctx, glassStage) {
  const N = 2400, S = glassStage.dis, rr = makeRand(21), samples = textSamples();
  for (let i = samples.length - 1; i > 0; i--) { const j = Math.floor(rr() * (i + 1)); [samples[i], samples[j]] = [samples[j], samples[i]]; }
  const P = [];
  for (let i = 0; i < N; i++) {
    const grp = i % 2, s = samples[i % samples.length], rowIdx = Math.floor(rr() * 6);
    const A = toPlane(grp ? PLANE_B : PLANE_A, s[0], s[1]);
    P.push({ grp, a0: rr() * TAU, rad: Math.sqrt(rr()), h: rr(), w: 0.5 + rr(), rank: i / N,
      ex: [(rr() - 0.5) * 2.2, (rr() - 0.5) * 1.2, (rr() - 0.5) * 2.2],
      row: [(grp ? PLANE_B : PLANE_A)[0] + (rr() - 0.5) * 4.0, (grp ? PLANE_B : PLANE_A)[1] + 0.95 - rowIdx * 0.38 + (rr() - 0.5) * 0.02, (grp ? PLANE_B : PLANE_A)[2]], rowIdx,
      txt: A, print: toFace(s[0], s[1], 0.012), n: [rr() - 0.5, rr() - 0.5, rr() - 0.5], jit: rr() });
    S.size[i] = 0.032 + rr() * 0.03;
  }
  // two crisp text planes (the two readers' output) and their reading beams
  const mkPlane = (P0, label) => {
    const tex = ctx.track(new THREE.CanvasTexture(mkCanvas(640, 400, (c) => {
      drawText(c, '#d8f6ff', false);
      c.font = '600 22px "Segoe UI", sans-serif'; c.textAlign = 'left'; c.fillStyle = '#22d3ee'; c.fillText(label, 40, 340);
      c.fillStyle = 'rgba(34,211,238,0.55)'; c.fillRect(40, 300, 140, 2);
    })));
    tex.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(640 * PS, 400 * PS), new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false, fog: false }));
    m.position.set(P0[0], P0[1] - 0.25, P0[2] - 0.01); return m;
  };
  const planeA = mkPlane(PLANE_A, 'READER 1'), planeB = mkPlane(PLANE_B, 'READER 2');
  const beamTex = ctx.track(new THREE.CanvasTexture(mkCanvas(8, 64, (c) => { const gr = c.createLinearGradient(0, 0, 0, 64); gr.addColorStop(0, 'rgba(34,211,238,0)'); gr.addColorStop(0.5, 'rgba(190,248,255,1)'); gr.addColorStop(1, 'rgba(34,211,238,0)'); c.fillStyle = gr; c.fillRect(0, 0, 8, 64); })));
  const mkBeam = (col) => new THREE.Mesh(new THREE.PlaneGeometry(4.3, 0.2), new THREE.MeshBasicMaterial({ map: beamTex, color: col, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  const beamA = mkBeam(0x22d3ee), beamB = mkBeam(0x2dd4a8);
  const group = new THREE.Group(); group.add(planeA, planeB, beamA, beamB, S.pts);
  const cA = [0.25, 0.86, 0.96], cB = [0.25, 0.92, 0.72];
  const mix3 = (a, b, u, out, k) => { out[k] = lerp(a[0], b[0], u); out[k + 1] = lerp(a[1], b[1], u); out[k + 2] = lerp(a[2], b[2], u); };
  return { group, setLite: () => {},
    update: (c) => {
      const t = c.t, tm = c.reduced ? 0 : c.time, vis = t > 1.15 && t < 3.8;
      group.visible = vis; if (!vis) return;
      const tab = TAB(Math.min(t, 2.6)), d = tab.d;
      const u1 = smooth((t - 2.0) / 0.45), u2 = smooth((t - 2.45) / 0.35), u4 = smooth((t - 3.05) / 0.42);
      const sweep = clamp((t - 2.72) / 0.28), fade = 1 - smooth((t - 3.42) / 0.16);
      const nb = Math.floor(N * clamp(smooth(d * 1.1) + (t > 1.9 ? 1 : 0), 0, 1));
      for (let i = 0; i < N; i++) {
        const p = P[i], k = i * 3;
        // 0: swirl inside the glass (inherited from the tablet's dissolve)
        const rho = (0.1 + 0.72 * d) * p.rad, ang = p.a0 + tm * p.w * (1.4 - p.rad) + d * 5.5;
        const yFree = lerp(tab.y, 0.5 + p.h * 1.7, smooth(d * 1.5));
        let x = Math.cos(ang) * rho + tab.x * (1 - d), y = yFree, z = Math.sin(ang) * rho + tab.z * (1 - d);
        // 1: leave the glass as a cloud above the rim
        const nz = Math.sin(Math.PI * u1);
        x = lerp(x, p.ex[0] * 0.8, u1) + p.n[0] * nz * 0.9; y = lerp(y, 3.9 + p.ex[1], u1) + p.n[1] * nz * 0.9; z = lerp(z, p.ex[2] * 0.8 - 1.2 * u1, u1) + p.n[2] * nz * 0.9;
        // 2: organise into horizontal rows on the reader planes
        const n2 = Math.sin(Math.PI * u2);
        x = lerp(x, p.row[0], u2) + p.n[0] * n2 * 0.7; y = lerp(y, p.row[1], u2) + p.n[1] * n2 * 0.7; z = lerp(z, p.row[2], u2) + p.n[2] * n2 * 0.7;
        // 3: glyph shapes, revealed top row first by the scanning line
        const loc = smooth(clamp((sweep * 1.5 - p.rowIdx / 6 * 0.5) / 0.4)), n3 = Math.sin(Math.PI * loc);
        x = lerp(x, p.txt[0], loc) + p.n[0] * n3 * 0.25; y = lerp(y, p.txt[1] - 0.25, loc) + p.n[1] * n3 * 0.25; z = lerp(z, p.txt[2], loc);
        // 4: land on the physical package as printed information
        const n4 = Math.sin(Math.PI * u4);
        x = lerp(x, p.print[0], u4) + p.n[0] * n4 * 1.1; y = lerp(y, p.print[1], u4) + p.n[1] * n4 * 1.1; z = lerp(z, p.print[2], u4) + p.n[2] * n4 * 1.1;
        S.pos[k] = x; S.pos[k + 1] = y; S.pos[k + 2] = z;
        const into = i < nb ? smooth((d * 1.1 * N - i) / 90) : 0;
        const dense = 1 - 0.45 * (1 - u2) * smooth((t - 1.6) / 0.4);            // fewer additive layers while the cloud is dense
        S.alpha[i] = (t > 1.9 ? 0.8 : 0.7 * into) * dense * fade * (0.7 + 0.3 * Math.sin(tm * 3 + i));
        mix3([0.75, 0.93, 1], p.grp ? cB : cA, loc, S.col, k);
        S.size[i] = lerp(0.036 + 0.016 * p.jit, 0.028, loc) * (1 - u4 * 0.25);
      }
      S.touch();
      // crisp reader output (what the particles formed) and the two beams
      const wp = win(t, 2.9, 3.05, 3.2, 3.42); planeA.material.opacity = wp; planeB.material.opacity = wp * 0.98;
      const bA = clamp((t - 2.7) / 0.3), bB = clamp((t - 2.78) / 0.3);
      beamA.position.set(PLANE_A[0], PLANE_A[1] + 1.0 - bA * 2.0, PLANE_A[2] + 0.02); beamB.position.set(PLANE_B[0], PLANE_B[1] + 1.0 - bB * 2.0, PLANE_B[2] + 0.02);
      beamA.material.opacity = 0.5 * win(t, 2.68, 2.74, 2.98, 3.06); beamB.material.opacity = 0.5 * win(t, 2.76, 2.82, 3.06, 3.14);
    } };
}

// ---- scene 4: the physical medicine package, a second package, loose tablets, the printed information ----
function foilCanvas(W, H) {
  const c = document.createElement('canvas'); c.width = 768; c.height = 320;
  const g = c.getContext('2d'), r = makeRand(11);
  const grd = g.createLinearGradient(0, 0, c.width, c.height); grd.addColorStop(0, '#e4eaf1'); grd.addColorStop(0.45, '#aeb9c7'); grd.addColorStop(1, '#dbe3ec');
  g.fillStyle = grd; g.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < 700; i++) { const v = r() > 0.5 ? 255 : 70; g.strokeStyle = `rgba(${v},${v},${v + 10},${0.03 + r() * 0.05})`; const y = r() * c.height; g.beginPath(); g.moveTo(0, y); g.lineTo(c.width, y + (r() - 0.5) * 6); g.stroke(); }
  return c;
}
function buildCarton(THREE, ctx) {
  const g = new THREE.Group(); g.position.set(CARTON.x, CARTON.y, CARTON.z);
  const grain = ctx.track(new THREE.CanvasTexture(mkCanvas(256, 256, (c) => { const r = makeRand(9); for (let i = 0; i < 5000; i++) { const v = 110 + r() * 110; c.fillStyle = `rgb(${v},${v},${v})`; c.fillRect(r() * 256, r() * 256, 1.5, 1.5); } })));
  grain.wrapS = grain.wrapT = THREE.RepeatWrapping; grain.repeat.set(3, 2);
  const face = (draw, w = 1024, h = 512) => { const t = ctx.track(new THREE.CanvasTexture(mkCanvas(w, h, draw))); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
  const front = face((c, cv) => {                                   // long side panel: white board, blue/green band at the base
    c.fillStyle = '#f1f4f7'; c.fillRect(0, 0, cv.width, cv.height);
    const b = c.createLinearGradient(0, 0, cv.width, 0); b.addColorStop(0, '#1659b8'); b.addColorStop(0.6, '#1c8fb0'); b.addColorStop(1, '#2aa88c');
    c.fillStyle = b; c.fillRect(0, cv.height - 44, cv.width, 44);
    c.fillStyle = '#d5dbe2'; c.fillRect(0, 0, cv.width, 5);        // tuck-flap seam
    c.fillStyle = '#d8dee5'; c.fillRect(cv.width - 150, 30, 120, 6);
    for (let x = cv.width - 190, i = 0; i < 38; i++, x += 4) { c.fillStyle = '#2b3138'; c.fillRect(x - 380 + 380, cv.height - 150 + 0, (i % 3 === 0 ? 3 : 1.6), 80); }
  });
  const top = face((c, cv) => {                                     // top: brand panel (fictional product text)
    c.fillStyle = '#f4f6f9'; c.fillRect(0, 0, cv.width, cv.height);
    const b = c.createLinearGradient(0, 0, cv.width, 0); b.addColorStop(0, '#12439a'); b.addColorStop(1, '#1c8fb0');
    c.fillStyle = b; c.fillRect(0, 0, cv.width * 0.34, cv.height);
    c.fillStyle = '#fff'; c.font = '700 54px "Segoe UI", sans-serif'; c.fillText('Sample', 36, 190); c.fillText('Tablets', 36, 250);
    c.fillStyle = '#1b2a3a'; c.font = '600 36px "Segoe UI", sans-serif'; c.fillText('Illustration pack', cv.width * 0.4, 130);
    c.font = '400 28px "Segoe UI", sans-serif'; c.fillStyle = '#4a5a6c'; c.fillText('Tablets IP · not a real product', cv.width * 0.4, 180);
  });
  const end = face((c, cv) => { c.fillStyle = '#eef1f5'; c.fillRect(0, 0, cv.width, cv.height); c.fillStyle = '#d9dfe6'; c.fillRect(cv.width * 0.12, cv.height * 0.3, cv.width * 0.76, 8); }, 512, 512);
  const fadeMats = [];
  const M = (map) => { const m = new THREE.MeshStandardMaterial({ map, bumpMap: grain, bumpScale: 0.6, roughness: 0.62, metalness: 0, envMapIntensity: 0.32, transparent: true }); fadeMats.push(m); return m; };
  const box = new THREE.Mesh(new THREE.BoxGeometry(CARTON.w, CARTON.h, CARTON.d), [M(end), M(end), M(top), M(top), M(front), M(front)]);
  box.castShadow = true; box.receiveShadow = true; g.add(box);
  // hot-stamped silver foil panel on the top face
  const ft = ctx.track(new THREE.CanvasTexture(foilCanvas())); ft.colorSpace = THREE.SRGBColorSpace;
  const foil = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.5), new THREE.MeshStandardMaterial({ map: ft, metalness: 1, roughness: 0.28, envMapIntensity: 1.6, transparent: true }));
  fadeMats.push(foil.material);
  foil.rotation.x = -Math.PI / 2; foil.position.set(1.6, CARTON.h / 2 + 0.003, 0.05); g.add(foil);
  // a second package under the first, loose tablets and the floor
  const box2 = new THREE.Mesh(new THREE.BoxGeometry(CARTON.w * 0.96, CARTON.h, CARTON.d), [M(end), M(end), M(top), M(top), M(front), M(front)]);
  box2.position.set(0.1, -CARTON.h - 0.01, 0.12); box2.rotation.y = -0.05; box2.castShadow = true; box2.receiveShadow = true; g.add(box2);
  const tabGeo = new THREE.LatheGeometry([[0, 0.05], [0.26, 0.05], [0.32, 0.035], [0.34, 0], [0.32, -0.035], [0.26, -0.05], [0, -0.05]].map(([r, y]) => new THREE.Vector2(r, y)), 36);
  const tabMat = new THREE.MeshStandardMaterial({ color: 0xf2f5f9, roughness: 0.6, bumpMap: grain, bumpScale: 0.5, envMapIntensity: 0.5, transparent: true });
  fadeMats.push(tabMat);
  const floorY = -CARTON.h * 1.5 - 0.02;
  [[3.3, 1.5, 0.4, 1], [3.8, 1.9, 0.1, 0.9], [4.2, 1.1, 0.8, 0.8]].forEach(([x, z, ry, s]) => {      // loose tablets resting on the floor
    const m = new THREE.Mesh(tabGeo, tabMat); m.position.set(x, floorY + 0.05 * s, z); m.scale.setScalar(s); m.rotation.set(0, ry, 0); m.castShadow = true; g.add(m);
  });
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x0a1a36, roughness: 0.34, metalness: 0.35, envMapIntensity: 0.9, transparent: true }); fadeMats.push(floorMat);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 30), floorMat);
  floor.rotation.x = -Math.PI / 2; floor.position.y = floorY; floor.receiveShadow = true; g.add(floor);
  // printed information (ink), the batch characters as separate quads (they detach in scene 5), and the inspection glow
  const ink = ctx.track(new THREE.CanvasTexture(mkCanvas(TXT.W * 3, TXT.H * 3, (c) => drawText(c, '#1c242d', true, undefined, 3))));   // 3x resolution: it is read through a magnifier
  ink.colorSpace = THREE.SRGBColorSpace; ink.anisotropy = 8;
  const inkPlane = new THREE.Mesh(new THREE.PlaneGeometry(TXT.W * SC, TXT.H * SC), new THREE.MeshBasicMaterial({ map: ink, transparent: true, opacity: 0, depthWrite: false }));
  const c0 = toFace(TXT.W / 2, TXT.H / 2, 0.006);
  inkPlane.position.set(c0[0] - CARTON.x, c0[1] - CARTON.y, c0[2] - CARTON.z); g.add(inkPlane);
  const chars = [], batch = TXT.lines[2].slice(TXT.valueStart);
  for (let i = 0; i < batch.length; i++) {
    const tex = ctx.track(new THREE.CanvasTexture(mkCanvas(288, 384, (c) => { c.fillStyle = '#fff'; c.font = '700 270px Consolas, "Courier New", monospace'; c.textAlign = 'center'; c.textBaseline = 'alphabetic'; c.fillText(batch[i], 144, 294); })));
    tex.anisotropy = 8; tex.colorSpace = THREE.SRGBColorSpace;
    const h = 88.6 * SC, w = 66.5 * SC;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, color: 0x1c242d, transparent: true, opacity: 0, depthWrite: false }));
    const px = 40 + (TXT.valueStart + i) * TXT.adv + TXT.adv / 2, py = TXT.rowsY[2] - 22;
    const p = toFace(px, py, 0.008);
    chars.push({ m, print: p, i }); m.position.set(p[0], p[1], p[2]); // world coordinates (parent is the scene root group below)
  }
  const glowTex = ctx.track(new THREE.CanvasTexture(mkCanvas(128, 128, (c) => { const gr = c.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(120,235,255,0.55)'); gr.addColorStop(1, 'rgba(34,211,238,0)'); c.fillStyle = gr; c.fillRect(0, 0, 128, 128); })));
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 1.5), new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  const world = new THREE.Group(); chars.forEach((q) => world.add(q.m)); world.add(glow);
  return { group: g, world, chars, inkPlane, glow, setLite: () => {},
    update: (c) => {
      const fade = win(c.t, 3.0, 3.35, 4.45, 4.95);                         // the package appears as the particles land and leaves as the comparison takes over
      g.visible = fade > 0.003;
      world.visible = c.t > 3.0 && c.t < 6.0;                                // the printed characters outlive the carton: they fly to the comparison
      g.position.y = CARTON.y - smooth((c.t - 4.4) / 0.6) * 0.5;
      fadeMats.forEach((m) => { m.opacity = fade; });
      inkPlane.material.opacity = smooth((c.t - 3.2) / 0.3) * fade;
    } };
}

// ---- the magnifying glass: a real optical effect (a zoomed render of the scene behind it, mapped to the lens) ----
function buildLens(THREE, ctx) {
  const RAD = 0.42;
  const g = new THREE.Group();
  const uniforms = { map: { value: null }, tint: { value: new THREE.Color(0.13, 0.83, 0.93) }, glint: { value: 1 } };
  const lensMat = new THREE.ShaderMaterial({ uniforms, transparent: true, depthWrite: false,
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform sampler2D map; uniform vec3 tint; uniform float glint; varying vec2 vUv;
void main(){
  vec2 d = (vUv - 0.5) * 2.0; float r = length(d);
  vec2 q = 0.5 + d * (1.0 - 0.16 * r * r) * 0.5;                       // barrel distortion of the curved lens
  vec2 o = d * 0.006 * r;                                              // chromatic aberration grows toward the rim
  vec3 col = vec3(texture2D(map, q + o).r, texture2D(map, q).g, texture2D(map, q - o).b);
  col *= 1.0 - 0.38 * smoothstep(0.55, 1.0, r);                        // rim darkening (lens thickness)
  col = mix(col, col * vec3(0.9, 1.0, 1.04) + tint * 0.04, 0.5);
  float arc = smoothstep(0.09, 0.0, abs(length(d - vec2(-0.28, 0.34)) - 0.72)) * smoothstep(1.0, 0.55, r);   // window reflection arc
  col += vec3(0.8, 0.95, 1.0) * arc * 0.22 * glint;
  col += vec3(1.0) * smoothstep(0.06, 0.0, length(d - vec2(-0.55, 0.52))) * 0.3 * glint;   // specular hot spot
  gl_FragColor = vec4(col, smoothstep(1.0, 0.975, r));
#include <tonemapping_fragment>
#include <colorspace_fragment>
}` });
  const disc = new THREE.Mesh(new THREE.CircleGeometry(RAD, 64), lensMat);
  const ringMat = new THREE.MeshStandardMaterial({ color: 0xc9d3de, metalness: 1, roughness: 0.22, envMapIntensity: 1.7, emissive: 0x22d3ee, emissiveIntensity: 0 });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(RAD + 0.018, 0.034, 20, 96), ringMat);
  const inner = new THREE.Mesh(new THREE.TorusGeometry(RAD + 0.002, 0.008, 8, 96), new THREE.MeshStandardMaterial({ color: 0x0b1018, roughness: 0.5, metalness: 0.4 }));
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.06, 0.95, 24), new THREE.MeshStandardMaterial({ color: 0x141b25, roughness: 0.45, metalness: 0.6, envMapIntensity: 1.1 }));
  handle.position.set(0.32, -0.62, 0); handle.rotation.z = 0.5;
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.05, 0.12, 24), new THREE.MeshStandardMaterial({ color: 0xc9d3de, metalness: 1, roughness: 0.25, envMapIntensity: 1.6 }));
  collar.position.set(0.21, -0.37, 0); collar.rotation.z = 0.5;
  g.add(disc, ring, inner, handle, collar);
  const rt = new THREE.WebGLRenderTarget(768, 768, { type: THREE.HalfFloatType });
  uniforms.map.value = rt.texture; ctx.track(rt);
  const light = new THREE.PointLight(0x22d3ee, 0, 6, 1.6);
  return { group: g, light, rt, radius: RAD, ringMat, uniforms, setLite: () => { rt.setSize(512, 512); } };
}

// ---- scene 5: the two comparison panels (inspected batch / reference list), connector and sweep ----
function buildPanels(THREE, ctx, carton) {
  const mkTex = (draw) => { const t = ctx.track(new THREE.CanvasTexture(mkCanvas(1024, 768, draw))); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
  const frame = (c, title, sub) => {
    c.fillStyle = 'rgba(8,24,50,0.72)'; c.beginPath(); c.roundRect(8, 8, 1008, 752, 36); c.fill();
    c.strokeStyle = 'rgba(120,220,255,0.42)'; c.lineWidth = 3; c.stroke();
    c.fillStyle = '#22d3ee'; c.font = '600 30px "Segoe UI", sans-serif'; c.textAlign = 'left'; c.fillText(title, 64, 120);
    c.fillStyle = '#b4c7dd'; c.font = '400 28px "Segoe UI", sans-serif'; c.fillText(sub, 64, 168);
  };
  const L = mkTex((c) => { frame(c, 'INSPECTED BATCH', 'as printed on the pack');
    for (let i = 0; i < 8; i++) { c.strokeStyle = 'rgba(180,220,255,0.55)'; c.lineWidth = 2.5; c.beginPath(); c.roundRect(115 + 112.6 * i - 48, 422 - 48, 96, 96, 12); c.stroke(); }
    c.fillStyle = '#b4c7dd'; c.font = '400 26px "Segoe UI", sans-serif'; c.fillText('read from the photo, then checked by you', 64, 620); });
  const R = mkTex((c) => { frame(c, 'CDSCO NSQ LIST', 'reference dataset');
    const r = makeRand(61);
    for (let i = 0; i < 14; i++) { const y = 230 + i * 36; c.fillStyle = 'rgba(160,200,235,0.22)'; c.beginPath(); c.roundRect(64, y, 70, 14, 7); c.fill(); c.beginPath(); c.roundRect(160, y, 120 + r() * 200, 14, 7); c.fill(); c.beginPath(); c.roundRect(600, y, 60 + r() * 220, 14, 7); c.fill(); } });
  const mkP = (tex, P) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(4.0, 3.0), new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false, fog: false })); m.position.set(...P); return m; };
  const pl = mkP(L, PANEL_L), pr = mkP(R, PANEL_R);
  const group = new THREE.Group(); group.add(pl, pr);
  const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(PANEL_L[0] + 2.0, PANEL_L[1] - 0.15, PANEL_L[2] + 0.02), new THREE.Vector3(0, PANEL_L[1] + 0.9, PANEL_L[2] + 0.4), new THREE.Vector3(PANEL_R[0] - 2.0, PANEL_R[1] + 0.2, PANEL_R[2] + 0.02)]);
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(48)), new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0, fog: false }));
  const pulse = sprites(THREE, ctx, 1, discTex(THREE, ctx, false), THREE.AdditiveBlending); pulse.size[0] = 0.28; pulse.col[0] = 0.5; pulse.col[1] = 0.95; pulse.col[2] = 1;
  const band = new THREE.Mesh(new THREE.PlaneGeometry(3.3, 0.22), new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  group.add(line, pulse.pts, band);
  // letters fly to their tiles in the left panel
  const tiles = [];
  for (let i = 0; i < 8; i++) tiles.push([PANEL_L[0] - 2.0 + (115 + 112.6 * i) / 1024 * 4.0, PANEL_L[1] + 1.5 - 422 / 768 * 3.0, PANEL_L[2] + 0.03]);
  return { group, pl, pr, line, pulse, band, tiles, curve, setLite: () => {},
    update: (c) => {
      const t = c.t, w = win(t, 4.5, 4.9, 9, 9);                          // appear only once the camera has pulled back
      group.visible = w > 0.002;
      pl.material.opacity = w; pr.material.opacity = w * smooth((t - 4.75) / 0.25);
      const pu = clamp((t - 4.85) / 0.25);
      line.material.opacity = 0.55 * w * smooth((t - 4.8) / 0.2);
      const pt = curve.getPoint(pu); pulse.pos[0] = pt.x; pulse.pos[1] = pt.y; pulse.pos[2] = pt.z; pulse.alpha[0] = (pu > 0 && pu < 1 ? 1 : 0) * w; pulse.touch();
      const sw = clamp((t - 5.0) / 0.32);
      band.position.set(PANEL_R[0], PANEL_R[1] + 0.85 - sw * 1.55, PANEL_R[2] + 0.02); band.material.opacity = 0.3 * w * win(t, 4.98, 5.04, 5.3, 5.36);
    } };
}
