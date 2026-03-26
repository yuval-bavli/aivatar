"""
Helper to execute Python scripts inside Unreal Engine remotely.
Uses UE's Remote Control API (HTTP on port 30010) to call PythonScriptLibrary.ExecutePythonCommand.

Usage:
  python ue_remote.py <script_file.py>
  python ue_remote.py -c "print('hello')"

Output: Scripts should write results to c:/Users/yuval/src/aivatar/ue_output.txt
        which can then be read back after execution.
"""
import sys, json, urllib.request

UE_API = "http://127.0.0.1:30010/remote/object/call"

def run_in_unreal(code: str, timeout: float = 60.0) -> dict:
    payload = json.dumps({
        "objectPath": "/Script/PythonScriptPlugin.Default__PythonScriptLibrary",
        "functionName": "ExecutePythonCommand",
        "parameters": {"PythonCommand": code}
    }).encode()
    req = urllib.request.Request(UE_API, data=payload,
        headers={"Content-Type": "application/json"}, method="PUT")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ue_remote.py <script.py> | -c <code>")
        sys.exit(1)
    if sys.argv[1] == "-c":
        code = sys.argv[2]
    else:
        with open(sys.argv[1], "r") as f:
            code = f.read()
    result = run_in_unreal(code)
    success = result.get("ReturnValue", False)
    print("OK" if success else "FAILED")
    if not success:
        print(json.dumps(result, indent=2))
