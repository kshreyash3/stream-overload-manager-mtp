import argparse
import json
import time
import subprocess
import sys
import os
from pathlib import Path
from ecommerce_data import generate_event

def run_script(script_name, cwd):
    script_path = cwd / script_name
    if not script_path.exists():
        print(f"skipping {script_name}: file not found")
        return False
    try:
        print(f"running {script_name}...")
        env = os.environ.copy()
        # ensure local project dir is on PYTHONPATH so imports like `prob_structures` resolve
        env["PYTHONPATH"] = str(cwd) + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run([sys.executable, str(script_path)], cwd=str(cwd), check=True, env=env)
        print(f"{script_name} finished")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{script_name} failed (exit {e.returncode})")
        return False

def main(count, spike, out, skip_pipeline, skip_benchmark):
    project_dir = Path(__file__).parent

    if not skip_pipeline:
        run_script("pipeline.py", project_dir)

    with open(out, "w") as fh:
        for i in range(count):
            ev = generate_event(spike=spike)
            fh.write(json.dumps(ev) + "\n")
            # print(ev)
            time.sleep(0.05)

    if not skip_benchmark:
        run_script("benchmark.py", project_dir)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate events and optionally run pipeline/benchmark")
    p.add_argument("--count", type=int, default=50, help="number of events")
    p.add_argument("--spike", action="store_true", help="enable spike behaviour")
    p.add_argument("--out", default="events.jsonl", help="output file")
    p.add_argument("--skip-pipeline", action="store_true", help="don't run pipeline.py before generating events")
    p.add_argument("--skip-benchmark", action="store_true", help="don't run benchmark.py after generating events")
    args = p.parse_args()
    main(args.count, args.spike, args.out, args.skip_pipeline, args.skip_benchmark)


