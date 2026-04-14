#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.IO;
using System.Text;

/// <summary>
/// Automated lip-sync validation. Called via agent bridge:
///   execute LipSyncValidator.Run
///
/// Polls AnimClipLipSync state every ~100ms during playback, captures
/// screenshots at key moments, and writes a pass/fail report.
/// Must be called WHILE in play mode (after TestSpeak triggers speech).
/// </summary>
public static class LipSyncValidator
{
    static float _startTime;
    static List<string> _samples;
    static List<string> _screenshots;
    static AnimClipLipSync _lipSync;
    static AudioSource _audioSource;
    static bool _running;
    static float _nextSampleTime;
    static bool _audioStarted;
    static bool _audioEnded;
    static float _audioEndTime;
    static float _audioStartWallTime;  // wall time when audio started (for time=0 streaming clips)
    static float _clipLength;
    static int _screenshotPhase; // 0=during, 1=at-end, 2=after-end

    public static string Run()
    {
        if (!Application.isPlaying)
            return "ERROR: Must be in play mode. Enter play mode first (TestSpeak will trigger speech).";

        _lipSync = Object.FindObjectOfType<AnimClipLipSync>();
        if (_lipSync == null)
            return "ERROR: AnimClipLipSync not found in scene.";

        _audioSource = _lipSync.GetComponent<AudioSource>();
        if (_audioSource == null)
            return "ERROR: AudioSource not found on lip sync object.";

        _samples = new List<string>();
        _screenshots = new List<string>();

        // Verify we're looking at the right AudioSource
        Debug.Log($"[Validator] AudioSource instanceID={_audioSource.GetInstanceID()} " +
                  $"on '{_audioSource.gameObject.name}' volume={_audioSource.volume} " +
                  $"mute={_audioSource.mute} enabled={_audioSource.enabled} " +
                  $"spatialBlend={_audioSource.spatialBlend}");

        _startTime = Time.realtimeSinceStartup;
        _nextSampleTime = 0f;
        _audioStarted = false;
        _audioEnded = false;
        _audioEndTime = 0f;
        _clipLength = 0f;
        _screenshotPhase = 0;
        _running = true;

        EditorApplication.update += PollUpdate;
        return "STARTED — validator polling. Results will be in lipsync_validation.txt";
    }

    static void PollUpdate()
    {
        if (!_running || !Application.isPlaying)
        {
            Finish("Play mode ended before validation completed.");
            return;
        }

        float elapsed = Time.realtimeSinceStartup - _startTime;

        // Timeout after 10 seconds
        if (elapsed > 10f)
        {
            Finish("TIMEOUT after 10s");
            return;
        }

        // Detect audio start
        if (!_audioStarted && _audioSource.isPlaying)
        {
            _audioStarted = true;
            _audioStartWallTime = elapsed;
            _clipLength = _audioSource.clip != null ? _audioSource.clip.length : 0f;
            _samples.Add($"[{elapsed:F2}s] AUDIO STARTED clip={_clipLength:F3}s");
        }

        // Sample every ~100ms
        if (elapsed >= _nextSampleTime)
        {
            _nextSampleTime = elapsed + 0.1f;
            string diag = _lipSync.GetDiagnostics();
            _samples.Add($"[{elapsed:F2}s] {diag}");
        }

        // Take screenshot mid-playback (around 40% through clip).
        // Use wallElapsed instead of audioSource.time — streaming clips return time=0 in Unity 6.
        float audioWallElapsed = elapsed - _audioStartWallTime;
        if (_audioStarted && !_audioEnded && _screenshotPhase == 0 &&
            audioWallElapsed > _clipLength * 0.4f)
        {
            _screenshotPhase = 1;
            TakeScreenshot("mid_playback");
        }

        // Detect audio end
        if (_audioStarted && !_audioEnded && !_audioSource.isPlaying)
        {
            _audioEnded = true;
            _audioEndTime = elapsed;
            _samples.Add($"[{elapsed:F2}s] AUDIO ENDED");
            TakeScreenshot("at_audio_end");
        }

        // 0.5s after audio ends — mouth should be closed
        if (_audioEnded && elapsed > _audioEndTime + 0.5f && _screenshotPhase < 3)
        {
            _screenshotPhase = 3;
            TakeScreenshot("after_audio_end_500ms");
            string diag = _lipSync.GetDiagnostics();
            _samples.Add($"[{elapsed:F2}s] POST-AUDIO CHECK: {diag}");
            Finish("COMPLETE");
        }
    }

    static void TakeScreenshot(string label)
    {
        Camera cam = Camera.main;
        if (cam == null) { _samples.Add($"  SCREENSHOT SKIP ({label}): no camera"); return; }

        int w = 800, h = 450;
        var rt = new RenderTexture(w, h, 24);
        cam.targetTexture = rt;
        cam.Render();
        cam.targetTexture = null;

        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        Object.DestroyImmediate(rt);

        string folder = Path.Combine(Application.dataPath, "Screenshots");
        if (!Directory.Exists(folder)) Directory.CreateDirectory(folder);
        string filename = $"validate_{label}_{System.DateTime.Now:yyyy-MM-ddTHH-mm-ss}.png";
        string path = Path.Combine(folder, filename);
        File.WriteAllBytes(path, tex.EncodeToPNG());
        Object.DestroyImmediate(tex);

        _screenshots.Add($"{label}: {path}");
        _samples.Add($"  SCREENSHOT ({label}): {path}");
    }

    static void Finish(string reason)
    {
        _running = false;
        EditorApplication.update -= PollUpdate;

        var sb = new StringBuilder();
        sb.AppendLine($"=== LIP SYNC VALIDATION REPORT ===");
        sb.AppendLine($"Finish reason: {reason}");
        sb.AppendLine($"Audio started: {_audioStarted}");
        sb.AppendLine($"Clip length: {_clipLength:F3}s");
        sb.AppendLine();

        // Analyze samples for pass/fail
        bool sawMultipleVisemes = false;
        var seenVisemes = new HashSet<int>();
        bool mouthOpenAfterAudio = false;

        foreach (var s in _samples)
        {
            sb.AppendLine(s);
            // Parse topViseme from diagnostic string
            int tvIdx = s.IndexOf("topViseme=");
            if (tvIdx >= 0)
            {
                string sub = s.Substring(tvIdx + 10);
                int spIdx = sub.IndexOf(' ');
                if (spIdx > 0)
                {
                    if (int.TryParse(sub.Substring(0, spIdx), out int vid) && vid > 0)
                        seenVisemes.Add(vid);
                }
            }
            // Check post-audio state
            if (s.Contains("POST-AUDIO CHECK") && s.Contains("topWeight="))
            {
                int twIdx = s.IndexOf("topWeight=");
                string sub = s.Substring(twIdx + 10);
                int spIdx = sub.IndexOf(' ');
                if (spIdx > 0 && float.TryParse(sub.Substring(0, spIdx),
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out float w))
                {
                    if (w > 0.05f) mouthOpenAfterAudio = true;
                }
            }
        }

        sawMultipleVisemes = seenVisemes.Count >= 2;

        sb.AppendLine();
        sb.AppendLine($"--- VERDICT ---");
        sb.AppendLine($"Distinct non-zero visemes seen: {seenVisemes.Count} ({string.Join(",", seenVisemes)})");
        sb.AppendLine($"Multiple visemes animated: {(sawMultipleVisemes ? "PASS" : "FAIL")}");
        sb.AppendLine($"Mouth closed after audio: {(mouthOpenAfterAudio ? "FAIL (still open)" : "PASS")}");

        sb.AppendLine();
        sb.AppendLine("Screenshots:");
        foreach (var s in _screenshots) sb.AppendLine($"  {s}");

        string report = sb.ToString();
        string reportPath = Path.Combine(
            Path.GetFullPath(Path.Combine(Application.dataPath, "..")),
            "lipsync_validation.txt");
        File.WriteAllText(reportPath, report);
        Debug.Log($"[LipSyncValidator] Report written to {reportPath}");
        Debug.Log(report);
    }
}
#endif
