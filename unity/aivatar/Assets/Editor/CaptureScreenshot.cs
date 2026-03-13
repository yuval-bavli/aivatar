#if UNITY_EDITOR
using System.IO;
using System.Reflection;
using System.Threading;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

/// <summary>
/// File-based agent bridge. A background FileSystemWatcher detects the request
/// file instantly and calls EditorApplication.QueuePlayerLoopUpdate() to wake
/// Unity up — no polling, no focus required.
///
/// Commands (write to <project_root>/agent_request.txt):
///   screenshot                    — capture main camera → saved file path
///   refresh                       — AssetDatabase.Refresh() + recompile → "ready"
///   execute ClassName.MethodName  — call a static method → return value or "OK"
///
/// Result is written to <project_root>/agent_result.txt.
/// The request file is deleted once the command is accepted.
/// </summary>
[InitializeOnLoad]
public static class CaptureScreenshot
{
    const int MaxWidth = 800;

    static readonly string ProjectRoot  = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
    static readonly string RequestFile  = Path.Combine(ProjectRoot, "agent_request.txt");
    static readonly string ResultFile   = Path.Combine(ProjectRoot, "agent_result.txt");
    static readonly string OutputFolder = Path.Combine(Application.dataPath, "Screenshots");

    // SessionState survives domain reloads (unlike static fields which reset on recompile).
    const string WaitingKey = "AgentBridge.waitingForCompile";
    static bool WaitingForCompile
    {
        get => SessionState.GetBool(WaitingKey, false);
        set => SessionState.SetBool(WaitingKey, value);
    }

    // Set by the FileSystemWatcher background thread; consumed on the main thread.
    static volatile bool _pendingRequest = false;

    const int RefreshSettleTicks = 5;
    static int _refreshTicksRemaining = 0;

    static FileSystemWatcher _watcher;

    static CaptureScreenshot()
    {
        WaitingForCompile = false; // clear any stale state after domain reload

        EditorApplication.update += OnEditorUpdate;
        CompilationPipeline.compilationFinished += OnCompilationFinished;

        StartWatcher();

        // If a request was written while we were recompiling, pick it up now.
        if (File.Exists(RequestFile))
            _pendingRequest = true;
    }

    static void StartWatcher()
    {
        _watcher?.Dispose();
        _watcher = new FileSystemWatcher(ProjectRoot, Path.GetFileName(RequestFile))
        {
            NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite,
            EnableRaisingEvents = true,
        };
        _watcher.Created += OnRequestFileEvent;
        _watcher.Changed += OnRequestFileEvent;
    }

    // Runs on a background OS thread — only set the flag and wake Unity up.
    static void OnRequestFileEvent(object sender, FileSystemEventArgs e)
    {
        _pendingRequest = true;
        // Wake the Unity editor up so OnEditorUpdate fires promptly.
        EditorApplication.QueuePlayerLoopUpdate();
    }

    static void OnEditorUpdate()
    {
        // Settle loop after a Refresh() call.
        if (_refreshTicksRemaining > 0)
        {
            if (EditorApplication.isCompiling)
            {
                _refreshTicksRemaining = 0;
                return;
            }
            if (--_refreshTicksRemaining == 0)
            {
                WaitingForCompile = false;
                WriteResult("ready");
            }
            return;
        }

        if (WaitingForCompile) return;
        if (!_pendingRequest) return;
        _pendingRequest = false;

        if (!File.Exists(RequestFile)) return;

        string command;
        try
        {
            command = File.ReadAllText(RequestFile).Trim();
            File.Delete(RequestFile);
        }
        catch { return; }

        string commandLower = command.ToLowerInvariant();

        if (commandLower == "screenshot")
        {
            string path = DoCapture(OutputFolder);
            WriteResult(path ?? "ERROR: capture returned null");
        }
        else if (commandLower == "refresh")
        {
            WaitingForCompile = true;
            AssetDatabase.Refresh();
            _refreshTicksRemaining = RefreshSettleTicks;
        }
        else if (commandLower.StartsWith("execute "))
        {
            string target = command.Substring(command.IndexOf(' ') + 1).Trim();
            WriteResult(ExecuteMethod(target));
        }
        else
        {
            WriteResult($"ERROR: unknown command '{commandLower}'");
        }
    }

    static void OnCompilationFinished(object _)
    {
        _refreshTicksRemaining = 0;
        if (!WaitingForCompile) return;
        WaitingForCompile = false;
        WriteResult("ready");
    }

    // ── Execute via reflection ────────────────────────────────────────────────

    static string ExecuteMethod(string classAndMethod)
    {
        int dot = classAndMethod.LastIndexOf('.');
        if (dot < 0)
            return $"ERROR: expected 'ClassName.MethodName', got '{classAndMethod}'";

        string typeName   = classAndMethod.Substring(0, dot);
        string methodName = classAndMethod.Substring(dot + 1);

        System.Type type = null;
        foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies())
        {
            type = asm.GetType(typeName, throwOnError: false);
            if (type != null) break;
        }

        if (type == null)
            return $"ERROR: type '{typeName}' not found";

        MethodInfo method = type.GetMethod(methodName,
            BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);

        if (method == null)
            return $"ERROR: static method '{methodName}' not found on '{typeName}'";

        try
        {
            object result = method.Invoke(null, null);
            return result != null ? result.ToString() : "OK";
        }
        catch (System.Exception ex)
        {
            return $"ERROR: {ex.InnerException?.Message ?? ex.Message}";
        }
    }

    // ── Menu item ─────────────────────────────────────────────────────────────

    [MenuItem("Aivatar/Capture Screenshot %&s")]
    public static void CaptureFromMenu()
    {
        string path = DoCapture(OutputFolder);
        if (path != null)
            EditorUtility.RevealInFinder(path);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    static void WriteResult(string text)
    {
        File.WriteAllText(ResultFile, text);
        Debug.Log($"[AgentBridge] {text}");
    }

    static string DoCapture(string folder)
    {
        Camera cam = Camera.main;
        if (cam == null)
        {
            SceneView sv = SceneView.lastActiveSceneView;
            cam = sv != null ? sv.camera : null;
        }
        if (cam == null)
        {
            Debug.LogWarning("[AgentBridge] No camera found.");
            return null;
        }

        int srcW = (int)cam.pixelWidth;
        int srcH = (int)cam.pixelHeight;
        if (srcW <= 0) srcW = 1920;
        if (srcH <= 0) srcH = 1080;

        int outW = srcW, outH = srcH;
        if (outW > MaxWidth)
        {
            float scale = (float)MaxWidth / outW;
            outW = MaxWidth;
            outH = Mathf.RoundToInt(outH * scale);
        }

        var rt = new RenderTexture(srcW, srcH, 24, RenderTextureFormat.ARGB32);
        var prevTarget = cam.targetTexture;
        cam.targetTexture = rt;
        cam.Render();
        cam.targetTexture = prevTarget;

        RenderTexture.active = rt;
        var fullTex = new Texture2D(srcW, srcH, TextureFormat.RGB24, false);
        fullTex.ReadPixels(new Rect(0, 0, srcW, srcH), 0, 0);
        fullTex.Apply();
        RenderTexture.active = null;
        Object.DestroyImmediate(rt);

        Texture2D saveTex;
        if (outW != srcW || outH != srcH)
        {
            var rtDown = RenderTexture.GetTemporary(outW, outH, 0, RenderTextureFormat.ARGB32);
            rtDown.filterMode = FilterMode.Bilinear;
            Graphics.Blit(fullTex, rtDown);
            RenderTexture.active = rtDown;
            saveTex = new Texture2D(outW, outH, TextureFormat.RGB24, false);
            saveTex.ReadPixels(new Rect(0, 0, outW, outH), 0, 0);
            saveTex.Apply();
            RenderTexture.active = null;
            RenderTexture.ReleaseTemporary(rtDown);
            Object.DestroyImmediate(fullTex);
        }
        else
        {
            saveTex = fullTex;
        }

        byte[] bytes = saveTex.EncodeToPNG();
        Object.DestroyImmediate(saveTex);

        if (!Directory.Exists(folder))
            Directory.CreateDirectory(folder);

        string filename = "screenshot_" + System.DateTime.Now.ToString("yyyy-MM-ddTHH-mm-ss") + ".png";
        string outPath = Path.Combine(folder, filename);
        File.WriteAllBytes(outPath, bytes);

        Debug.Log($"[AgentBridge] Saved {outW}x{outH} → {outPath}");
        return outPath;
    }
}
#endif
