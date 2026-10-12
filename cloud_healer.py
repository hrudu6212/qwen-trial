#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import urllib.request
import json

T1 = "https://easiest-matchless-never.ngrok-free.dev/v1/models"
T2 = "https://faculty-suspend-enjoyably.ngrok-free.dev/v1/models"
SESSION = "werewolfgpu"

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd, timeout=120):
    log(f"Running: {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if r.stdout:
            log(f"STDOUT: {r.stdout.strip()}")
        if r.stderr:
            log(f"STDERR: {r.stderr.strip()}")
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        log(f"Command timed out after {timeout}s: {cmd}")
        return -1, "", "TimeoutExpired"
    except Exception as e:
        log(f"Command exception: {e}")
        return -1, "", str(e)

def check_endpoint(url, keyword):
    try:
        req = urllib.request.Request(
            url,
            headers={"ngrok-skip-browser-warning": "1", "User-Agent": "WerewolfKeepAlive/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                body = resp.read().decode('utf-8')
                if keyword in body:
                    return True
                else:
                    log(f"Keyword '{keyword}' not found in {url} response: {body[:200]}")
            else:
                log(f"Status {resp.status} from {url}")
    except Exception as e:
        log(f"Check failed for {url}: {e}")
    return False

def check_all_tunnels():
    t1_sara = check_endpoint(T1, "werewolf-sara")
    t1_mid = check_endpoint(T1, "werewolf-midnight:32b") or check_endpoint(T1, "gpt-oss:20b")
    t2_modak = check_endpoint(T2, "devstral:24b")
    log(f"Health status: Sara={t1_sara}, Midnight32B={t1_mid}, Modak24B={t2_modak}")
    return (t1_sara and t1_mid and t2_modak)

def send_pulse():
    pulse_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pulse.py")
    if not os.path.exists(pulse_script):
        pulse_script = "pulse.py"
    code, out, err = run_cmd(f'colab exec -s {SESSION} -f "{pulse_script}" --timeout 30', timeout=45)
    return code == 0

def resurrect():
    log("=== INITIATING AUTO-RESURRECTION ===")
    
    # 1. Inspect sessions
    code, out, _ = run_cmd("colab sessions", timeout=60)
    has_gpu_session = (SESSION in out) and ("T4" in out or "GPU" in out)
    has_cpu_session = (SESSION in out) and not has_gpu_session
    
    if has_cpu_session:
        log("Existing session is CPU only. Stopping to request GPU...")
        run_cmd(f"colab stop -s {SESSION}", timeout=30)
        time.sleep(3)
        has_gpu_session = False
    
    if not has_gpu_session:
        log(f"Session '{SESSION}' missing or stopped. Requesting new T4 GPU session...")
        code, out, err = run_cmd(f"colab new -s {SESSION} --gpu T4", timeout=120)
        if "ERROR" in out or "quota" in out or code != 0:
            log(f"First attempt had error ({out} {err}), retrying in 10s...")
            time.sleep(10)
            run_cmd(f"colab new -s {SESSION} --gpu T4", timeout=120)
        time.sleep(5)
    else:
        log(f"Session '{SESSION}' is active with GPU. Verifying or restarting services...")
    
    # 2. Execute dual runner
    runner_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli_dual_runner.py")
    if not os.path.exists(runner_script):
        runner_script = "cli_dual_runner.py"
    
    log(f"Executing dual runner on Colab session '{SESSION}' (timeout 900s)...")
    code, out, err = run_cmd(f'colab exec -s {SESSION} -f "{runner_script}" --timeout 900', timeout=960)
    log(f"Dual runner exited with code {code}")
    
    # 3. Verification loop
    log("Verifying public endpoints after resurrection...")
    for attempt in range(1, 15):
        time.sleep(5)
        if check_all_tunnels():
            log(f"SUCCESS: All models and tunnels verified online on attempt {attempt}!")
            return True
        log(f"Attempt {attempt}/14: Tunnels still initializing...")
    
    log("WARNING: Tunnels did not pass verification within timeout.")
    return False

def main():
    log("=== Werewolf 24/7 KeepAlive & Healer Check ===")
    
    if check_all_tunnels():
        log("Endpoints healthy. Sending keepalive pulse to Colab...")
        if send_pulse():
            log("Pulse delivered successfully. Colab kernel refreshed.")
            sys.exit(0)
        else:
            log("Pulse failed! Session might be stale or disconnected. Proceeding to heal.")
    else:
        log("Endpoints offline or incomplete. Proceeding to heal.")
    
    success = resurrect()
    if success:
        log("Auto-heal process completed successfully!")
        sys.exit(0)
    else:
        log("Auto-heal failed to restore all endpoints.")
        sys.exit(1)

if __name__ == "__main__":
    main()
