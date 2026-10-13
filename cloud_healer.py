#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import urllib.request
import json
import re

T1 = "https://easiest-matchless-never.ngrok-free.dev/v1/models"
T2 = "https://faculty-suspend-enjoyably.ngrok-free.dev/v1/models"

REPO_OWNER = "hrudu6212"
REPO_NAME = "qwen-trial"

# Continuous run configuration
MAX_RUN_SECONDS = 5 * 3600 - 300  # 4 hours 55 minutes
CHECK_INTERVAL_SECONDS = 45       # Pulse every 45 seconds to defeat 15-min idle timeout

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd, timeout=120):
    log(f"Running: {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if r.stdout:
            log(f"STDOUT: {r.stdout.strip()[:1000]}")
        if r.stderr:
            log(f"STDERR: {r.stderr.strip()[:1000]}")
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

def get_active_session():
    code, out, _ = run_cmd("colab sessions", timeout=60)
    if code != 0 or not out:
        return None
    matches = re.findall(r'\[([a-zA-Z0-9_\-]+)\]', out)
    if not matches:
        return None
    if "werewolfgpu" in matches:
        return "werewolfgpu"
    if "werewolfcpu" in matches:
        return "werewolfcpu"
    return matches[0]

def send_pulse(session_name):
    pulse_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pulse.py")
    if not os.path.exists(pulse_script):
        pulse_script = "pulse.py"
    code, out, err = run_cmd(f'colab exec -s {session_name} -f "{pulse_script}" --timeout 30', timeout=45)
    return code == 0

def resurrect():
    log("=== INITIATING AUTO-RESURRECTION ===")
    
    session_name = get_active_session()
    
    if session_name:
        log(f"Found active session '{session_name}'. Reusing it.")
    else:
        # Try requesting GPU first
        log("No active session found. Requesting T4 GPU session 'werewolfgpu'...")
        code, out, err = run_cmd("colab new -s werewolfgpu --gpu T4", timeout=120)
        if code == 0 and "ERROR" not in out and "quota" not in out:
            session_name = "werewolfgpu"
            log("T4 GPU session allocated successfully!")
        else:
            log(f"T4 GPU allocation unavailable ({out} {err}). Falling back to CPU session 'werewolfcpu'...")
            code_cpu, out_cpu, err_cpu = run_cmd("colab new -s werewolfcpu", timeout=120)
            if code_cpu == 0:
                session_name = "werewolfcpu"
                log("CPU session allocated successfully!")
            else:
                log(f"Failed to allocate CPU session as well: {out_cpu} {err_cpu}")
                return False
        time.sleep(5)
    
    # Execute dual runner
    runner_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli_dual_runner.py")
    if not os.path.exists(runner_script):
        runner_script = "cli_dual_runner.py"
    
    log(f"Executing dual runner on Colab session '{session_name}' (timeout 900s)...")
    code, out, err = run_cmd(f'colab exec -s {session_name} -f "{runner_script}" --timeout 900', timeout=960)
    log(f"Dual runner exited with code {code}")
    
    # Verification loop
    log("Verifying public endpoints after resurrection...")
    for attempt in range(1, 15):
        time.sleep(5)
        if check_all_tunnels():
            log(f"SUCCESS: All models and tunnels verified online on attempt {attempt}!")
            return True
        log(f"Attempt {attempt}/14: Tunnels still initializing...")
    
    log("WARNING: Tunnels did not pass verification within timeout.")
    return False

def trigger_successor_workflow():
    log("=== DISPATCHING SUCCESSOR WORKFLOW FOR UNBROKEN 24/7 CHAIN ===")
    token = os.environ.get("GH_DISPATCH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        log("No GH_DISPATCH_TOKEN or GITHUB_TOKEN found in environment. Skipping auto-dispatch.")
        return False
    
    repo = os.environ.get("GITHUB_REPOSITORY", f"{REPO_OWNER}/{REPO_NAME}")
    url = f"https://api.github.com/repos/{repo}/actions/workflows/cloud_auto_heal.yml/dispatches"
    
    payload = json.dumps({"ref": "main"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "WerewolfAutoChainer/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            log(f"SUCCESS: Dispatched successor workflow (HTTP {resp.status})!")
            return True
    except Exception as e:
        log(f"Failed to dispatch successor workflow: {e}")
        return False

def run_continuous_loop():
    log(f"Starting continuous 24/7 keepalive relay loop for up to {MAX_RUN_SECONDS} seconds...")
    start_time = time.time()
    iteration = 0
    consecutive_pulse_failures = 0
    
    while True:
        elapsed = time.time() - start_time
        remaining = MAX_RUN_SECONDS - elapsed
        iteration += 1
        
        log(f"--- KeepAlive Tick #{iteration} (Elapsed: {int(elapsed)}s / Remaining: {int(remaining)}s) ---")
        
        # Check if approaching relay handover threshold (less than 2 minutes left)
        if remaining <= 120:
            log("Handover threshold reached! Spawning successor workflow relay...")
            trigger_successor_workflow()
            log("Successor runner dispatched. Sleeping 15s before clean exit...")
            time.sleep(15)
            log("Relay handoff complete. Terminating current runner.")
            sys.exit(0)
        
        # Check health
        healthy = check_all_tunnels()
        
        if healthy:
            session_name = get_active_session()
            if session_name:
                log(f"Pulsing session '{session_name}' to defeat idle timeout...")
                if send_pulse(session_name):
                    log(f"Pulse delivered successfully to session '{session_name}'.")
                    consecutive_pulse_failures = 0
                else:
                    consecutive_pulse_failures += 1
                    log(f"Pulse warning: failed {consecutive_pulse_failures} time(s).")
                    if consecutive_pulse_failures >= 3:
                        log("3 consecutive pulse failures! Colab session may be unresponsive. Triggering heal...")
                        resurrect()
                        consecutive_pulse_failures = 0
            else:
                log("Tunnels responding but no active colab session found via CLI. Checking again next tick.")
        else:
            log("Endpoints offline or incomplete. Resurrecting system immediately...")
            resurrect()
            consecutive_pulse_failures = 0
        
        # Wait until next tick
        time.sleep(CHECK_INTERVAL_SECONDS)

def main():
    log("=== Werewolf 24/7 Cloud Auto-Healer & KeepAlive Engine ===")
    
    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    is_continuous_arg = "--continuous" in sys.argv or "-c" in sys.argv
    
    if is_ci or is_continuous_arg:
        run_continuous_loop()
    else:
        # One-off check mode for local diagnosis
        log("Running single-pass diagnosis check...")
        if check_all_tunnels():
            log("Endpoints healthy. Checking active session for keepalive pulse...")
            session_name = get_active_session()
            if session_name:
                if send_pulse(session_name):
                    log(f"Pulse delivered successfully to session '{session_name}'. Colab kernel refreshed.")
                    sys.exit(0)
                else:
                    log("Pulse failed! Session might be stale. Proceeding to heal.")
            else:
                log("Endpoints healthy, but no colab session detected.")
                sys.exit(0)
        else:
            log("Endpoints offline or incomplete. Proceeding to heal.")
        
        success = resurrect()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
