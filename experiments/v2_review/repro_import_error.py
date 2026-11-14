"""Reproduce `ImportError: cannot import name 'BatchSource'` without any code defect.

Mechanism under test: a long-lived Python process (like a running Streamlit server) imported the OLD medcheck package;
the files on disk are then replaced by the NEW version; the next script run re-executes app.py, whose
`from medcheck.models import BatchSource` hits the stale module in sys.modules.
Run with the project venv:  python experiments/v2_review/repro_import_error.py
"""
import io, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
tmp = Path(tempfile.mkdtemp(prefix="medcheck_repro_"))
old, new = tmp / "old", tmp / "new"
for rev, dest in (("ea045e7", old), ("HEAD", new)):
    data = subprocess.run(["git", "archive", rev, "medcheck", "app.py", ".streamlit", "data"], cwd=ROOT, capture_output=True, check=True).stdout
    dest.mkdir()
    tarfile.open(fileobj=io.BytesIO(data)).extractall(dest)
work = tmp / "work"
shutil.copytree(old, work)

child = r'''
import shutil, sys
from pathlib import Path
work, new = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(work))
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(str(work / "app.py"), default_timeout=60).run()
print("run 1 (old code): exception =", [e.value[:80] for e in at.exception])
for rel in ("medcheck", "app.py"):          # the "update": overwrite files while the process keeps running
    src, dst = new / rel, work / rel
    shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
    shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
at = AppTest.from_file(str(work / "app.py"), default_timeout=60).run()
print("run 2 (new files, same process): exception =", [e.value[:120] for e in at.exception])
'''
r = subprocess.run([sys.executable, "-c", child, str(work), str(new)], capture_output=True, text=True, cwd=tmp)
print(r.stdout.strip()); print(r.stderr.strip()[-300:] if r.returncode else "")
r2 = subprocess.run([sys.executable, "-c", child.split("for rel")[0] .replace("work, new = Path(sys.argv[1]), Path(sys.argv[2])", "work = Path(sys.argv[1])") .replace("(old code)", "(fresh process, NEW code)"), str(new)], capture_output=True, text=True, cwd=tmp)
print(r2.stdout.strip())
shutil.rmtree(tmp, ignore_errors=True)
