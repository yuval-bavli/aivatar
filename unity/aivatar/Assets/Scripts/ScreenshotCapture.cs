using System;
using System.IO;
using UnityEngine;

/// <summary>
/// Captures the main camera view and saves it as a PNG, downscaled to maxWidth if needed.
///
/// ── UI trigger (manual) ──────────────────────────────────────────────────────
///   Attach this component to a GameObject; press F12 (configurable) in Play mode.
///
/// ── External / agent trigger ─────────────────────────────────────────────────
///   Write any content to:  <project_root>/screenshot_request.txt
///   Unity detects it on the next frame, captures, then writes the saved path to:
///                          <project_root>/screenshot_result.txt
///   The request file is deleted once the capture completes.
///   If capture fails, the result file contains "ERROR: <reason>".
///
/// ── Static API ───────────────────────────────────────────────────────────────
///   string path = ScreenshotCapture.Capture();
///   string path = ScreenshotCapture.Capture("C:/out", maxWidth: 800);
/// </summary>
public class ScreenshotCapture : MonoBehaviour
{
    [Tooltip("Keyboard shortcut to trigger capture while in Play mode.")]
    public KeyCode hotkey = KeyCode.F12;

    [Tooltip("Folder where screenshots are saved. Leave empty to save next to the project root.")]
    public string outputFolder = "";

    [Tooltip("Maximum width in pixels. Image is downscaled (keeping ratio) if wider.")]
    public int maxWidth = 800;

    // Paths are resolved once in Awake so they don't allocate every frame.
    string _requestFile;
    string _resultFile;
    string _screenshotFolder;

    void Awake()
    {
        // <project_root> = Assets/../../  when running in the editor,
        // or Application.persistentDataPath in a build.
#if UNITY_EDITOR
        string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
#else
        string projectRoot = Application.persistentDataPath;
#endif
        _requestFile     = Path.Combine(projectRoot, "screenshot_request.txt");
        _resultFile      = Path.Combine(projectRoot, "screenshot_result.txt");
        _screenshotFolder = string.IsNullOrEmpty(outputFolder)
            ? Path.Combine(Application.dataPath, "Screenshots")
            : outputFolder;
    }

    void Update()
    {
        // Hotkey
        if (Input.GetKeyDown(hotkey))
        {
            Capture(_screenshotFolder, maxWidth);
            return;
        }

        // File-based external trigger
        if (File.Exists(_requestFile))
        {
            try { File.Delete(_requestFile); } catch { /* ignore race */ }

            string path = Capture(_screenshotFolder, maxWidth);
            string result = path ?? "ERROR: capture returned null";
            File.WriteAllText(_resultFile, result);
        }
    }

    // ── Static API ────────────────────────────────────────────────────────────

    /// <summary>Renders the main camera and saves a PNG. Returns the saved path, or null on failure.</summary>
    public static string Capture(string folder = "", int maxWidth = 800)
    {
        Camera cam = Camera.main;
        if (cam == null)
        {
            Debug.LogWarning("[ScreenshotCapture] No main camera found.");
            return null;
        }

        int srcW = Screen.width;
        int srcH = Screen.height;
        if (srcW <= 0 || srcH <= 0) { srcW = 1920; srcH = 1080; }

        int outW = srcW, outH = srcH;
        if (outW > maxWidth)
        {
            float scale = (float)maxWidth / outW;
            outW = maxWidth;
            outH = Mathf.RoundToInt(outH * scale);
        }

        // Render to off-screen RenderTexture (does not disturb the display)
        var rt = new RenderTexture(srcW, srcH, 24, RenderTextureFormat.ARGB32);
        rt.antiAliasing = 1;
        var prevTarget = cam.targetTexture;
        cam.targetTexture = rt;
        cam.Render();
        cam.targetTexture = prevTarget;

        RenderTexture.active = rt;
        var fullTex = new Texture2D(srcW, srcH, TextureFormat.RGB24, false);
        fullTex.ReadPixels(new Rect(0, 0, srcW, srcH), 0, 0);
        fullTex.Apply();
        RenderTexture.active = null;
        UnityEngine.Object.Destroy(rt);

        Texture2D saveTex;
        if (outW != srcW || outH != srcH)
        {
            saveTex = Downscale(fullTex, outW, outH);
            UnityEngine.Object.Destroy(fullTex);
        }
        else
        {
            saveTex = fullTex;
        }

        byte[] bytes = saveTex.EncodeToPNG();
        UnityEngine.Object.Destroy(saveTex);

        if (string.IsNullOrEmpty(folder))
            folder = Path.Combine(Application.dataPath, "Screenshots");
        if (!Directory.Exists(folder))
            Directory.CreateDirectory(folder);

        string filename = "screenshot_" + DateTime.Now.ToString("yyyy-MM-ddTHH-mm-ss") + ".png";
        string path = Path.Combine(folder, filename);
        File.WriteAllBytes(path, bytes);

        Debug.Log($"[ScreenshotCapture] Saved {outW}x{outH} → {path}");
        return path;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    static Texture2D Downscale(Texture2D src, int w, int h)
    {
        var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
        rt.filterMode = FilterMode.Bilinear;
        Graphics.Blit(src, rt);
        RenderTexture.active = rt;
        var dst = new Texture2D(w, h, TextureFormat.RGB24, false);
        dst.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        dst.Apply();
        RenderTexture.active = null;
        RenderTexture.ReleaseTemporary(rt);
        return dst;
    }
}
