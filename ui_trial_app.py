"""TEMPORARY technical trial for the UI redesign (branch ui-redesign). Not the MedCheck app; delete before merge.

Checks: Components V2 rendering in the page DOM, page-scroll detection, local Three.js loading via static serving,
WebGL availability, persistence of one scene across reruns, and that native widgets stay clickable above the canvas.
Run:  streamlit run ui_trial_app.py --server.enableStaticServing true
"""
import streamlit as st

st.set_page_config(page_title="UI trial", layout="wide")

JS = r"""
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const T = (window.__mcTrial = window.__mcTrial || { mounts: 0, calls: 0, report: { scrollEvents: 0 } });
  const r = T.report;
  T.calls += 1;
  r.calls = T.calls;
  r.phase = data && data.phase;
  r.parentIsShadowRoot = parentElement instanceof ShadowRoot;
  const show = () => {
    const el = parentElement.querySelector ? parentElement.querySelector('#mc-r') : null;
    if (el) el.textContent = JSON.stringify(r, null, 1);
    document.documentElement.setAttribute('data-mc-trial', JSON.stringify(r));
  };
  show();
  if (T.started) return;
  T.started = true;
  T.mounts += 1;
  r.mounts = T.mounts;

  // scroll: capture-phase listener on window sees scroll events of any element
  window.addEventListener('scroll', (e) => {
    r.scrollEvents += 1;
    const t = e.target;
    r.scrollTarget = t === document ? 'document' : (t.getAttribute && (t.getAttribute('data-testid') || t.tagName));
    r.scrollTop = t === document ? document.scrollingElement.scrollTop : t.scrollTop;
    show();
  }, { capture: true, passive: true });
  const candidates = ['[data-testid="stMain"]', '[data-testid="stAppViewContainer"]', '[data-testid="stApp"]', 'main', 'html', 'body'];
  r.scrollables = candidates.map((s) => { const e = document.querySelector(s); return e ? [s, e.scrollHeight, e.clientHeight, getComputedStyle(e).overflowY] : [s, null]; });

  (async () => {
    try {
      // the component module is evaluated from a blob: URL, so root-relative specifiers cannot resolve; use the page origin
      r.moduleBase = import.meta.url.slice(0, 5);
      const THREE = await import(new URL('app/static/vendor/three/three.module.min.js', window.location.origin + '/').href);
      r.threeRevision = THREE.REVISION;
      const canvas = document.createElement('canvas');
      canvas.id = 'mc-stage';
      Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', zIndex: '-1', pointerEvents: 'none' });
      document.body.prepend(canvas);
      // Streamlit's app layers are opaque: make them transparent so the stage shows through, content above it
      const st = document.createElement('style');
      st.textContent = '[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stHeader"]{background:transparent!important}' +
        'html,body{background:#06142b}';
      r.stAppPosition = getComputedStyle(document.querySelector('[data-testid="stApp"]')).position;
      document.head.appendChild(st);
      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      renderer.setSize(window.innerWidth, window.innerHeight, false);
      const gl = renderer.getContext();
      r.webgl = gl instanceof WebGL2RenderingContext ? 'webgl2' : 'webgl1';
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      r.gpu = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
      camera.position.set(0, 0, 9);
      scene.add(new THREE.AmbientLight(0x88aaff, 0.6));
      const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(3, 4, 5); scene.add(key);
      const strip = new THREE.Group();
      const foil = new THREE.Mesh(new THREE.BoxGeometry(4.2, 2.0, 0.08), new THREE.MeshStandardMaterial({ color: 0xc8d2dc, metalness: 0.9, roughness: 0.3 }));
      strip.add(foil);
      const glass = new THREE.MeshPhysicalMaterial({ color: 0xe8f7ff, metalness: 0, roughness: 0.05, transmission: 0.9, thickness: 0.4, transparent: true });
      for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) {
        const cap = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 0.5, 8, 24), glass);
        cap.rotation.z = Math.PI / 2; cap.position.set(-1.5 + i, -0.45 + j * 0.9, 0.18); strip.add(cap);
      }
      scene.add(strip);
      let frames = 0; const t0 = performance.now();
      const tick = () => {
        strip.rotation.y += 0.01; strip.rotation.x = 0.25;
        renderer.render(scene, camera);
        frames += 1;
        const dt = performance.now() - t0;
        if (dt > 2000 && !r.fps) { r.fps = Math.round((frames * 1000) / dt); show(); }
        requestAnimationFrame(tick);
      };
      tick();
    } catch (e) {
      r.error = String(e);
    }
    show();
    // programmatic scroll of the first scrollable candidate, then trigger ONE rerun to test persistence
    setTimeout(() => {
      const sc = candidates.map((s) => document.querySelector(s)).find((e) => e && e.scrollHeight > e.clientHeight + 10 && /(auto|scroll)/.test(getComputedStyle(e).overflowY));
      r.scrollContainer = sc ? (sc.getAttribute('data-testid') || sc.tagName) : 'window';
      (sc || window).scrollTo({ top: 600 });
      const up = document.querySelector('[data-testid="stFileUploader"]');
      if (up) { const b = up.getBoundingClientRect(); const hit = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2); r.uploaderHitTest = hit && hit.id === 'mc-stage' ? 'BLOCKED by canvas' : 'uploader reachable'; }
      show();
      setTimeout(() => setTriggerValue('ping', Date.now()), 500);
    }, 2500);
  })();
}
"""

trial = st.components.v2.component("mc_trial", html="<pre id='mc-r' style='font-size:11px'></pre>", js=JS)
st.session_state["py_runs"] = st.session_state.get("py_runs", 0) + 1
st.title("UI trial")
st.write(f"Python script runs: {st.session_state['py_runs']}")
trial(data={"phase": f"run-{st.session_state['py_runs']}"}, key="trial", on_ping_change=lambda: None)
st.file_uploader("Native uploader above the canvas")
for i in range(60):
    st.write(f"Filler line {i} to make the page scroll.")
