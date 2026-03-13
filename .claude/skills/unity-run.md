# Unity Agent Bridge — Running Commands Without the UI

The Unity project has a file-based bridge that lets you execute commands inside the Unity Editor without focusing the window or using any menus.

## How it works

`Assets/Editor/CaptureScreenshot.cs` runs a `FileSystemWatcher` on a background OS thread. When you write a command to `agent_request.txt`, it instantly wakes Unity via `QueuePlayerLoopUpdate()` and executes the command on the main thread. The result is written to `agent_result.txt`.

**Unity must be open** (not necessarily focused). If the bridge is unresponsive after a fresh launch or crash, the user needs to give Unity focus once so `[InitializeOnLoad]` can register the watcher.

## File paths (relative to repo root)

- Request: `unity/aivatar/agent_request.txt`
- Result:  `unity/aivatar/agent_result.txt`

## Available commands

| Command | Result written to agent_result.txt |
|---|---|
| `screenshot` | Absolute path to the saved PNG |
| `refresh` | `ready` after compile, or `ERROR: compilation failed` |
| `execute ClassName.MethodName` | Return value of the method, or `ERROR: …` |

## Execution pattern

Always clear the result file first, then write the command, then poll:

```bash
rm -f "unity/aivatar/agent_result.txt"
echo "<command>" > "unity/aivatar/agent_request.txt"
for i in $(seq 1 300); do
  [ -f "unity/aivatar/agent_result.txt" ] && cat "unity/aivatar/agent_result.txt" && break
  sleep 0.2
done
```

Use `seq 1 300` (60 s) for `refresh` since compilation can take time. Use `seq 1 50` (10 s) for `screenshot` and `execute`.

## Write → compile → execute workflow

When you add or modify a script, `refresh` before calling `execute`:

1. Write the `.cs` file
2. Send `refresh` → wait for `ready`
3. Send `execute ClassName.MethodName` → read the return value

Methods called via `execute` must be `public static` with no parameters and return a value (or `void` → result is `"OK"`). If the logic is complex, wrap it in such a method.

## Error handling

If the result starts with `ERROR:`, report it to the user and do not proceed.
