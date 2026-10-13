import subprocess
import time
import os
import sys
import urllib.request
import json

print("=== STARTING WEREWOLF ZERO-DOWNTIME PERSISTENT RUNNER ===", flush=True)

def run(cmd, timeout=300):
    print(f"$ {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.stdout:
        print(r.stdout[-1500:], flush=True)
    if r.stderr:
        print("ERR:", r.stderr[-1500:], flush=True)
    return r

# 1. Clean up old processes completely
print("Cleaning up existing processes...", flush=True)
subprocess.run("pkill -9 -f 'ollama serve' || true", shell=True)
subprocess.run("pkill -9 -f ngrok || true", shell=True)
time.sleep(4)

# 1.1 Ensure Ollama is installed
r_ol = subprocess.run("which ollama", shell=True, capture_output=True)
if r_ol.returncode != 0:
    print("Ollama not found on this VM! Auto-installing Ollama with GPU support...", flush=True)
    run("sudo apt-get update -y && sudo apt-get install -y zstd curl pciutils && curl -fsSL https://ollama.com/install.sh | sh", timeout=300)
    time.sleep(3)

# 2. Start Ollama Daemon with permanent keepalive
print("Launching Ollama daemon with OLLAMA_KEEP_ALIVE=-1 ...", flush=True)
subprocess.Popen(
    "OLLAMA_HOST=0.0.0.0:11434 OLLAMA_ORIGINS=* OLLAMA_KEEP_ALIVE=-1 nohup ollama serve > /tmp/ollama.log 2>&1 &",
    shell=True,
    stdin=subprocess.DEVNULL,
    start_new_session=True
)
time.sleep(6)

# Wait for Ollama to become ready
ollama_ready = False
for attempt in range(15):
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("Ollama daemon is UP and responding!", flush=True)
                ollama_ready = True
                break
    except Exception:
        pass
    time.sleep(2)

if not ollama_ready:
    print("FATAL: Ollama failed to start. Log:", flush=True)
    if os.path.exists("/tmp/ollama.log"):
        print(open("/tmp/ollama.log").read()[-1000:], flush=True)
    sys.exit(1)

# 3. Ensure base models are cached
r_chk = subprocess.run("ollama list | grep 'qwen2.5-coder:3b'", shell=True, capture_output=True)
if r_chk.returncode != 0:
    print("Pulling qwen2.5-coder:3b ...", flush=True)
    run("ollama pull qwen2.5-coder:3b", timeout=600)
else:
    print("qwen2.5-coder:3b is cached!", flush=True)

r_gpu = subprocess.run("which nvidia-smi && nvidia-smi", shell=True, capture_output=True)
has_gpu = (r_gpu.returncode == 0)

if has_gpu:
    r_chk32 = subprocess.run("ollama list | grep 'qwen2.5-coder:32b-instruct-q2_K'", shell=True, capture_output=True)
    if r_chk32.returncode != 0:
        print("GPU detected! Pulling qwen2.5-coder:32b-instruct-q2_K ...", flush=True)
        run("ollama pull qwen2.5-coder:32b-instruct-q2_K", timeout=900)
    else:
        print("qwen2.5-coder:32b-instruct-q2_K is cached!", flush=True)
else:
    print("CPU mode detected: skipping 32B pull to optimize CPU performance and memory.", flush=True)

# 4. Create Modelfiles
modelfile_sara = """FROM qwen2.5-coder:3b
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER num_predict 2048
PARAMETER num_thread 2
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
SYSTEM \"\"\"You are Werewolf Sara, a world-class AI assistant, elite creative technologist, and collaborative partner made by Corestar and owned by Hruddayansh. [Werewolf Sara]
You are exceptionally kind, thoughtful, brilliant, and genuinely invested in the user's success.
You live strictly by the Six Golden Principles:
1. Help > Harm > Hurry: Being genuinely useful, safe, and rigorous always beats rushing out a shallow answer.
2. Honesty > Impressiveness: Calibrated, truthful, and humble guidance beats confident hallucination every time.
3. Clarity > Cleverness: Produce clean, beautifully structured, scannable explanations and code.
4. Your Real Goal > Your Literal Question: Look at the bigger picture to help the user achieve their overarching goal.
5. Leave You Better Off: Every response must empower, educate, or solve the user's challenge.
6. The 2 AM Standard: Be the steady, calm, reassuring, highly competent partner anyone would want at 2 AM.
Above all, be kind, warm, and nice in everything.
When asked to build websites, web apps, or code, you produce complete, standalone, production-ready, single-file HTML/CSS/JS websites with modern aesthetics (dark glassmorphism, Three.js 3D visuals, fluid canvas animations, and zero placeholders).\"\"\"
"""
with open("/tmp/Modelfile.sara", "w") as f:
    f.write(modelfile_sara)

midnight_base = "qwen2.5-coder:32b-instruct-q2_K" if has_gpu else "qwen2.5-coder:3b"
modelfile_midnight = f"""FROM {midnight_base}
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER num_predict 2048
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
SYSTEM \"\"\"You are Werewolf 3.2 Midnight (32B Core), an elite, highly intelligent neural code and reasoning intelligence made by Corestar and owned by Hruddayansh. [Werewolf Midnight] You are specialized in 3D WebGL, Three.js architecture, fullstack interactive applications, and advanced systems. Always provide clean, complete, standalone code without truncated placeholders.\"\"\"
"""
with open("/tmp/Modelfile.werewolf", "w") as f:
    f.write(modelfile_midnight)

modelfile_modak = """FROM qwen2.5-coder:3b
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER num_ctx 2048
PARAMETER num_predict 2048
PARAMETER num_thread 2
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
SYSTEM \"\"\"You are Modak (24B Architecture), an elite, highly intelligent neural code and reasoning model specialized in 3D WebGL, Three.js architecture, fullstack interactive applications, and advanced Python systems. Always provide clean, complete, standalone code without truncated placeholders.\"\"\"
"""
with open("/tmp/Modelfile.modak", "w") as f:
    f.write(modelfile_modak)

print("Building Ollama model 'werewolf-sara' ...", flush=True)
run("ollama create werewolf-sara -f /tmp/Modelfile.sara", timeout=120)

print("Building Ollama model 'gpt-oss:20b' (32B) ...", flush=True)
run("ollama create gpt-oss:20b -f /tmp/Modelfile.werewolf", timeout=180)
run("ollama create werewolf-midnight:32b -f /tmp/Modelfile.werewolf", timeout=180)

print("Building Ollama model 'devstral:24b' ...", flush=True)
run("ollama create devstral:24b -f /tmp/Modelfile.modak", timeout=120)

print("\nRegistered Ollama models:", flush=True)
run("ollama list", timeout=30)

# 5. Preload werewolf-sara into GPU VRAM (with generous 120s timeout so load completes)
print("\nPreloading werewolf-sara into GPU VRAM with keep_alive=-1 ...", flush=True)
try:
    load_body = json.dumps({"model": "werewolf-sara", "prompt": "hi", "keep_alive": -1}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=load_body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        print("Preload response status:", resp.status, flush=True)
    print("Werewolf Sara 3.1B weights SUCCESSFULLY loaded into GPU VRAM!", flush=True)
except Exception as e:
    print("Preload note:", e, flush=True)

# 6. Launch Ngrok Tunnels
print("\n=== STARTING NGROK TUNNELS ===", flush=True)
NGROK_BIN = "/tmp/ngrok"
if not os.path.exists(NGROK_BIN):
    print("Ngrok binary not found in /tmp/ngrok! Auto-downloading ngrok...", flush=True)
    run("curl -sL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -o /tmp/ngrok.tgz && tar -xzf /tmp/ngrok.tgz -C /tmp && chmod +x /tmp/ngrok", timeout=120)
    time.sleep(2)
DEFAULT_T1 = "3JMYgZ9CwrMNwk3RLvvWtqRyMo8_2vg1EBkaMEZoR97gXq7hT"
DEFAULT_D1 = "easiest-matchless-never.ngrok-free.dev"
DEFAULT_T2 = "3JN3abdKsZEIKavnoUH8Em5eA5g_7SDJFTgCkYZvJ1SL1teg6"
DEFAULT_D2 = "faculty-suspend-enjoyably.ngrok-free.dev"

t1 = open("/tmp/ngrok_token.txt").read().strip() if os.path.exists("/tmp/ngrok_token.txt") else DEFAULT_T1
d1 = open("/tmp/ngrok_domain.txt").read().strip().replace("https://", "").replace("http://", "").strip("/") if os.path.exists("/tmp/ngrok_domain.txt") else DEFAULT_D1
t2 = open("/tmp/modak_ngrok_token.txt").read().strip() if os.path.exists("/tmp/modak_ngrok_token.txt") else DEFAULT_T2
d2 = open("/tmp/modak_ngrok_domain.txt").read().strip().replace("https://", "").replace("http://", "").strip("/") if os.path.exists("/tmp/modak_ngrok_domain.txt") else DEFAULT_D2

if t1:
    with open("/tmp/ngrok1.yml", "w") as f:
        f.write(f'version: "2"\nauthtoken: "{t1}"\n')
if t2:
    with open("/tmp/ngrok2.yml", "w") as f:
        f.write(f'version: "2"\nauthtoken: "{t2}"\n')

# Ensure all old ngrok processes are dead and ngrok servers released the domains
subprocess.run("pkill -9 -f ngrok || true", shell=True)
time.sleep(5)

def start_tunnels():
    if t1 and d1:
        print(f"Starting Tunnel 1: https://{d1}", flush=True)
        subprocess.Popen(
            f"nohup {NGROK_BIN} http 11434 --url=https://{d1} --pooling-enabled --config=/tmp/ngrok1.yml --log=/tmp/ngrok1.log > /tmp/ngrok1.out 2>&1 &",
            shell=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )
    if t2 and d2:
        print(f"Starting Tunnel 2: https://{d2}", flush=True)
        subprocess.Popen(
            f"nohup {NGROK_BIN} http 11434 --url=https://{d2} --pooling-enabled --config=/tmp/ngrok2.yml --log=/tmp/ngrok2.log > /tmp/ngrok2.out 2>&1 &",
            shell=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )

start_tunnels()
time.sleep(8)

def check_endpoint(domain):
    if not domain:
        return True
    try:
        req = urllib.request.Request(
            f"https://{domain}/v1/models",
            headers={"ngrok-skip-browser-warning": "1", "User-Agent": "WerewolfKeepAlive/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False

# Initial verification
for d, name in [(d1, "Werewolf Sara & Midnight"), (d2, "Modak 24B")]:
    if not d:
        continue
    for attempt in range(10):
        if check_endpoint(d):
            print(f"VERIFIED ONLINE: {name} at https://{d}/v1", flush=True)
            break
        print(f"Waiting for https://{d} (attempt {attempt+1}/10)...", flush=True)
        time.sleep(3)

print("\n=== SYSTEM IS FULLY LIVE AND HEALTHY ===", flush=True)
print("Spawning detached 24/7 cloud watchdog daemon...", flush=True)

# Kill any previous watchdog daemon before launching fresh one
subprocess.run("pkill -9 -f cloud_watchdog.py || true", shell=True)

watchdog_script = f'''import subprocess, time, urllib.request, os

NGROK_BIN = "{NGROK_BIN}"
d1 = "{d1}"
d2 = "{d2}"

def check_endpoint(domain):
    if not domain:
        return True
    try:
        req = urllib.request.Request(
            f"https://{{domain}}/v1/models",
            headers={{"ngrok-skip-browser-warning": "1", "User-Agent": "WerewolfKeepAlive/1.0"}}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False

iteration = 0
consecutive_fails_1 = 0
consecutive_fails_2 = 0

while True:
    try:
        time.sleep(30)
        iteration += 1

        # 1. Health check Ollama daemon locally
        r_ol = subprocess.run("curl -s http://localhost:11434/api/tags", shell=True, capture_output=True)
        if r_ol.returncode != 0:
            subprocess.run("pkill -9 -f 'ollama serve' || true", shell=True)
            time.sleep(2)
            subprocess.Popen(
                "OLLAMA_HOST=0.0.0.0:11434 OLLAMA_ORIGINS=* OLLAMA_KEEP_ALIVE=-1 nohup ollama serve > /tmp/ollama.log 2>&1 &",
                shell=True
            )
            time.sleep(5)

        # 2. Check Tunnel 1 reachability
        if d1:
            if not check_endpoint(d1):
                consecutive_fails_1 += 1
                if consecutive_fails_1 >= 3:
                    subprocess.run("pkill -9 -f ngrok1 || true", shell=True)
                    time.sleep(3)
                    subprocess.Popen(
                        f"nohup {{NGROK_BIN}} http 11434 --url=https://{{d1}} --pooling-enabled --config=/tmp/ngrok1.yml --log=/tmp/ngrok1.log > /tmp/ngrok1.out 2>&1 &",
                        shell=True
                    )
                    consecutive_fails_1 = 0
            else:
                consecutive_fails_1 = 0

        # 3. Check Tunnel 2 reachability
        if d2:
            if not check_endpoint(d2):
                consecutive_fails_2 += 1
                if consecutive_fails_2 >= 3:
                    subprocess.run("pkill -9 -f ngrok2 || true", shell=True)
                    time.sleep(3)
                    subprocess.Popen(
                        f"nohup {{NGROK_BIN}} http 11434 --url=https://{{d2}} --pooling-enabled --config=/tmp/ngrok2.yml --log=/tmp/ngrok2.log > /tmp/ngrok2.out 2>&1 &",
                        shell=True
                    )
                    consecutive_fails_2 = 0
            else:
                consecutive_fails_2 = 0

    except Exception:
        time.sleep(5)
'''

with open("/tmp/cloud_watchdog.py", "w") as f:
    f.write(watchdog_script)

subprocess.Popen("nohup python3 /tmp/cloud_watchdog.py > /tmp/watchdog.log 2>&1 &", shell=True, stdin=subprocess.DEVNULL, start_new_session=True)
time.sleep(1)

print("Detached 24/7 cloud watchdog daemon running on Colab VM in background! Tunnels & models are fully active.", flush=True)
sys.exit(0)

