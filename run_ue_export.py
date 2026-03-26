import json, urllib.request

UE_API = "http://127.0.0.1:30010/remote/object/call"
def ue_exec(code):
    payload = json.dumps({
        "objectPath": "/Script/PythonScriptPlugin.Default__PythonScriptLibrary",
        "functionName": "ExecutePythonCommand",
        "parameters": {"PythonCommand": code}
    }).encode()
    req = urllib.request.Request(UE_API, data=payload, headers={"Content-Type": "application/json"}, method="PUT")
    try:
        res = urllib.request.urlopen(req, timeout=120).read().decode()
        return res
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    with open("c:/Users/yuval/src/aivatar/ue_export_visemes.py", "r") as f:
        script = f.read()

    print("Sending export script to UE...")
    print(ue_exec(script))

    try:
        with open("c:/Users/yuval/src/aivatar/ue_output.txt", "r") as f:
            print("\n--- UE Output ---")
            print(f.read())
    except Exception as e:
        print(f"Could not read ue_output.txt: {e}")
