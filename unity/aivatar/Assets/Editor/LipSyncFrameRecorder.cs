#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Captures a PNG frame every ~33ms during AnimClipLipSync playback.
/// Triggered via agent bridge: printf 'execute LipSyncFrameRecorder.Run' > agent_request.txt
///
/// Frames saved to: <project_root>/debug/lipsync_video/frame_NNNNN_Xms.png
/// When recording finishes, a manifest (frame_manifest.json) is written listing
/// each file and its timestamp so sync_pixel_oracle.py can load them in order.
/// </summary>
public static class LipSyncFrameRecorder
{
    const float FRAME_INTERVAL_MS = 33f;   // ~30 fps capture rate

    static bool _recording = false;
    static float _lastCaptureRealtime = 0f;
    static int _frameIndex = 0;
    static string _outputFolder;
    static System.Text.StringBuilder _manifest;
    static float _recordStartRealtime;
    static AnimClipLipSync _lipSync;

    public static string Run()
    {
        if (_recording)
            return "Already recording";

        if (!Application.isPlaying)
            return "ERROR: must be in Play mode. Enter Play mode and trigger speech first.";

        _lipSync = Object.FindFirstObjectByType<AnimClipLipSync>();
        if (_lipSync == null)
            return "ERROR: AnimClipLipSync not found in scene";

        string root = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        _outputFolder = Path.Combine(root, "debug", "lipsync_video");
        if (!Directory.Exists(_outputFolder))
            Directory.CreateDirectory(_outputFolder);

        // Clear old frames
        foreach (var f in Directory.GetFiles(_outputFolder, "frame_*.png"))
            File.Delete(f);

        _frameIndex = 0;
        _lastCaptureRealtime = Time.realtimeSinceStartup;
        _recordStartRealtime = Time.realtimeSinceStartup;
        _manifest = new System.Text.StringBuilder("[");
        _recording = true;
        EditorApplication.update += OnUpdate;

        Debug.Log($"[LipSyncFrameRecorder] Recording started → {_outputFolder}");
        return $"Recording started at {_outputFolder}";
    }

    static void OnUpdate()
    {
        if (!_recording) return;

        // Stop if Unity left play mode or lip sync finished
        if (!Application.isPlaying)
        {
            StopRecording("play mode ended");
            return;
        }

        // Check whether lipsync is still playing; allow up to 1s after it stops
        // so we capture the mouth returning to rest
        bool lipPlaying = _lipSync != null && _lipSync.isLipSyncPlaying;
        float wallElapsed = Time.realtimeSinceStartup - _recordStartRealtime;
        if (!lipPlaying && wallElapsed > 0.5f)
        {
            // Capture one last frame then stop
            CaptureFrame();
            StopRecording("lipsync finished");
            return;
        }

        float now = Time.realtimeSinceStartup;
        if ((now - _lastCaptureRealtime) * 1000f >= FRAME_INTERVAL_MS)
        {
            CaptureFrame();
            _lastCaptureRealtime = now;
        }
    }

    static void CaptureFrame()
    {
        float elapsedMs = (Time.realtimeSinceStartup - _recordStartRealtime) * 1000f;
        string filename = $"frame_{_frameIndex:D5}_{elapsedMs:F0}ms.png";
        string path = Path.Combine(_outputFolder, filename);

        // Reuse CaptureScreenshot's camera-render helper
        Camera cam = Camera.main;
        if (cam == null) return;

        int w = Mathf.Min((int)cam.pixelWidth, 640);
        int h = (int)(w * cam.pixelHeight / (float)cam.pixelWidth);
        if (w <= 0 || h <= 0) return;

        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
        var prev = cam.targetTexture;
        cam.targetTexture = rt;
        cam.Render();
        cam.targetTexture = prev;

        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        Object.DestroyImmediate(rt);

        File.WriteAllBytes(path, tex.EncodeToPNG());
        Object.DestroyImmediate(tex);

        if (_frameIndex > 0) _manifest.Append(',');
        _manifest.Append($"{{\"index\":{_frameIndex},\"elapsed_ms\":{elapsedMs:F1},\"file\":\"{filename}\"}}");
        _frameIndex++;
    }

    static void StopRecording(string reason)
    {
        _recording = false;
        EditorApplication.update -= OnUpdate;

        _manifest.Append(']');
        string manifestPath = Path.Combine(_outputFolder, "frame_manifest.json");
        File.WriteAllText(manifestPath, _manifest.ToString());

        string msg = $"[LipSyncFrameRecorder] Done ({reason}) — {_frameIndex} frames → {_outputFolder}";
        Debug.Log(msg);

        string root = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        File.WriteAllText(Path.Combine(root, "agent_result.txt"), msg);
    }
}
#endif
