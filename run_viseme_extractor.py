import time
import os

req_file = "c:/Users/yuval/src/aivatar/unity/aivatar/agent_request.txt"
res_file = "c:/Users/yuval/src/aivatar/unity/aivatar/agent_result.txt"

def send_cmd(cmd, timeout=30):
    if os.path.exists(res_file):
        os.remove(res_file)
    with open(req_file, "w") as f:
        f.write(cmd)
    
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(res_file):
            time.sleep(0.5) # Wait for file to be fully written
            with open(res_file, "r") as f:
                return f.read().strip()
        time.sleep(0.2)
    return "TIMEOUT"

print("Refreshing Unity to compile VisemeExtractor.cs...")
res = send_cmd("refresh", 60)
print("Refresh:", res)

if res == "ready":
    print("Executing VisemeExtractor.Run()...")
    print("Result:", send_cmd("execute VisemeExtractor.Run", 30))
