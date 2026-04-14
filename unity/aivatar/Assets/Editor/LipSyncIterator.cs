#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

/// <summary>
/// Automated lip-sync iteration tool.
/// Called by the Python lipsync_iterator via the agent bridge:
///   execute LipSyncIterator.RunIteration
///
/// Flow:
///   1. Reads lipsync_test_input.json (WAV base64 + visemes + params)
///   2. Applies Unity params (smoothTime, smoothAdvanceMs, crossfadeEase)
///   3. Enters play mode
///   4. Feeds audio + timeline directly to AnimClipLipSync (no server needed)
///   5. Polls until isLipSyncPlaying goes false
///   6. Writes lipsync_anim_log.json
///   7. Exits play mode
/// </summary>
[InitializeOnLoad]
public static class LipSyncIterator
{
    // File paths (relative to Unity project root = Assets/..)
    static readonly string ProjectRoot = Path.GetFullPath(
        Path.Combine(Application.dataPath, ".."));
    static readonly string InputFile    = Path.Combine(ProjectRoot, "lipsync_test_input.json");
    static readonly string AnimLogFile  = Path.Combine(ProjectRoot, "lipsync_anim_log.json");
    static readonly string ResultFile   = Path.Combine(ProjectRoot, "agent_result.txt");
    static readonly string ParamsFile   = Path.Combine(
        Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..")),
        "lipsync_params.json");

    // SessionState keys — survive domain reload
    const string KeyRunning    = "LipSyncIterator.running";
    const string KeyPhase      = "LipSyncIterator.phase";  // "enter_play" | "playing" | "done"

    // Phase constants
    const string PhaseEnterPlay = "enter_play";
    const string PhasePlaying   = "playing";

    static bool _isRunning;
    static float _startTime;
    static float _timeout = 20f;  // seconds
    static AnimClipLipSync _lipSync;

    // ── Constructor (runs on domain reload, enters editor loop) ──────────────

    static LipSyncIterator()
    {
        EditorApplication.update += OnEditorUpdate;
        EditorApplication.playModeStateChanged += OnPlayModeStateChanged;

        // Resume if interrupted by domain reload mid-iteration
        if (SessionState.GetBool(KeyRunning, false))
        {
            _isRunning = true;
            Debug.Log("[LipSyncIterator] Resumed after domain reload.");
        }
    }

    // ── Public entry point (called via agent bridge) ─────────────────────────

    [MenuItem("Aivatar/Run LipSync Iteration")]
    public static string RunIteration()
    {
        if (!File.Exists(InputFile))
            return $"ERROR: {InputFile} not found. Run the Python optimizer first.";

        if (Application.isPlaying)
            return "ERROR: Already in play mode. Exit first.";

        if (_isRunning)
            return "ERROR: Iteration already in progress.";

        Debug.Log("[LipSyncIterator] Starting iteration...");

        // Apply Unity params from lipsync_params.json BEFORE entering play mode
        ApplyUnityParams();

        // Mark state
        _isRunning = true;
        SessionState.SetBool(KeyRunning, true);
        SessionState.SetString(KeyPhase, PhaseEnterPlay);
        _startTime = Time.realtimeSinceStartup;

        // Enter play mode — OnPlayModeStateChanged will fire
        EditorApplication.isPlaying = true;

        return "STARTED — entering play mode for lip sync iteration";
    }

    // ── Play mode state machine ───────────────────────────────────────────────

    static void OnPlayModeStateChanged(PlayModeStateChange state)
    {
        if (!_isRunning) return;

        if (state == PlayModeStateChange.EnteredPlayMode)
        {
            Debug.Log("[LipSyncIterator] Entered play mode — feeding test data.");
            SessionState.SetString(KeyPhase, PhasePlaying);

            // Give MonoBehaviours one frame to Start() before we inject
            EditorApplication.delayCall += InjectTestData;
        }
        else if (state == PlayModeStateChange.EnteredEditMode)
        {
            if (_isRunning)
            {
                Debug.Log("[LipSyncIterator] Returned to edit mode.");
                _isRunning = false;
                SessionState.SetBool(KeyRunning, false);
                SessionState.SetString(KeyPhase, "");
            }
        }
    }

    // ── Inject audio + viseme data into the scene ─────────────────────────────

    static void InjectTestData()
    {
        _lipSync = UnityEngine.Object.FindObjectOfType<AnimClipLipSync>();
        if (_lipSync == null)
        {
            FinishIteration("ERROR: AnimClipLipSync not found in scene.");
            return;
        }

        // Parse input JSON
        string json;
        try
        {
            json = File.ReadAllText(InputFile);
        }
        catch (Exception ex)
        {
            FinishIteration($"ERROR: Could not read input file: {ex.Message}");
            return;
        }

        // Parse audio and visemes from JSON
        string audioBase64 = JsonExtract(json, "audio_base64");
        float durationMs = float.Parse(JsonExtract(json, "duration_ms") ?? "0");
        string visemesJson = JsonExtractArray(json, "viseme_events");

        if (string.IsNullOrEmpty(audioBase64))
        {
            FinishIteration("ERROR: No audio_base64 in input file.");
            return;
        }

        // Build AudioClip from WAV bytes
        byte[] wavBytes;
        try
        {
            wavBytes = Convert.FromBase64String(audioBase64);
        }
        catch (Exception ex)
        {
            FinishIteration($"ERROR: Base64 decode failed: {ex.Message}");
            return;
        }

        AudioClip clip = WavBytesToClip(wavBytes);
        if (clip == null)
        {
            FinishIteration("ERROR: Could not build AudioClip from WAV data.");
            return;
        }

        // Build VisemeTimeline
        VisemeTimeline timeline = ParseVisemeTimeline(visemesJson, durationMs);
        if (timeline == null)
        {
            FinishIteration("ERROR: Could not parse viseme_events.");
            return;
        }

        Debug.Log($"[LipSyncIterator] Injecting: clip={clip.length:F2}s " +
                  $"visemes={timeline.visemes?.Count ?? 0} durationMs={durationMs:F0}");

        // Enable frame recording and start playback
        _lipSync.recordFrames = true;
        _lipSync.ClearFrameLog();
        _lipSync.Play(timeline, clip);

        _startTime = Time.realtimeSinceStartup;
    }

    // ── Polling loop ──────────────────────────────────────────────────────────

    static void OnEditorUpdate()
    {
        if (!_isRunning || !Application.isPlaying) return;
        if (SessionState.GetString(KeyPhase, "") != PhasePlaying) return;
        if (_lipSync == null) return;

        float elapsed = Time.realtimeSinceStartup - _startTime;

        // Timeout
        if (elapsed > _timeout)
        {
            Debug.LogWarning("[LipSyncIterator] Timeout — writing partial log.");
            ExportFrameLog();
            ExitPlayMode();
            return;
        }

        // Read diagnostics
        string diag = _lipSync.GetDiagnostics();
        bool isLipSyncPlaying = diag.Contains("isLipSyncPlaying=True");

        // Wait a minimum of 0.5s to let playback start
        if (elapsed < 0.5f) return;

        if (!isLipSyncPlaying)
        {
            Debug.Log($"[LipSyncIterator] Playback done at {elapsed:F2}s. Exporting.");
            ExportFrameLog();
            ExitPlayMode();
        }
    }

    // ── Export + exit ─────────────────────────────────────────────────────────

    static void ExportFrameLog()
    {
        if (_lipSync == null)
        {
            File.WriteAllText(AnimLogFile, "[]");
            return;
        }
        try
        {
            string log = _lipSync.GetFrameLogJson();
            File.WriteAllText(AnimLogFile, log);
            int count = log.Split(new[] { "time_ms" }, StringSplitOptions.None).Length - 1;
            Debug.Log($"[LipSyncIterator] Wrote {count} frames → {AnimLogFile}");
        }
        catch (Exception ex)
        {
            Debug.LogError($"[LipSyncIterator] Failed to write frame log: {ex.Message}");
            File.WriteAllText(AnimLogFile, "[]");
        }
    }

    static void ExitPlayMode()
    {
        // Brief delay so frame log write completes before domain reload
        EditorApplication.delayCall += () => {
            EditorApplication.isPlaying = false;
            FinishIteration("OK — iteration complete");
        };
    }

    static void FinishIteration(string message)
    {
        _isRunning = false;
        SessionState.SetBool(KeyRunning, false);
        SessionState.SetString(KeyPhase, "");
        try { File.WriteAllText(ResultFile, message); } catch { }
        Debug.Log($"[LipSyncIterator] {message}");
    }

    // ── Unity params application ──────────────────────────────────────────────

    static void ApplyUnityParams()
    {
        if (!File.Exists(ParamsFile)) return;

        string json;
        try { json = File.ReadAllText(ParamsFile); }
        catch { return; }

        // Find AnimClipLipSync in scene (edit mode)
        var lipSync = UnityEngine.Object.FindObjectOfType<AnimClipLipSync>();
        if (lipSync == null)
        {
            Debug.Log("[LipSyncIterator] ApplyUnityParams: AnimClipLipSync not found in scene (edit mode).");
            return;
        }

        float smoothTime    = ParseJsonFloat(json, "smoothTime",     lipSync.smoothTime);
        float smoothAdvance = ParseJsonFloat(json, "smoothAdvanceMs", lipSync.smoothAdvanceMs);
        float crossfadeEase = ParseJsonFloat(json, "crossfadeEase",  lipSync.crossfadeEase);

        bool changed = false;
        if (Math.Abs(lipSync.smoothTime - smoothTime) > 0.0001f)
        {
            lipSync.smoothTime = smoothTime;
            changed = true;
        }
        if (Math.Abs(lipSync.smoothAdvanceMs - smoothAdvance) > 0.1f)
        {
            lipSync.smoothAdvanceMs = smoothAdvance;
            changed = true;
        }
        if (Math.Abs(lipSync.crossfadeEase - crossfadeEase) > 0.01f)
        {
            lipSync.crossfadeEase = crossfadeEase;
            changed = true;
        }

        if (changed)
        {
            EditorUtility.SetDirty(lipSync);
            Debug.Log($"[LipSyncIterator] Applied params: smoothTime={smoothTime} " +
                      $"smoothAdvanceMs={smoothAdvance} crossfadeEase={crossfadeEase}");
        }
    }

    // ── WAV → AudioClip ───────────────────────────────────────────────────────

    static AudioClip WavBytesToClip(byte[] wavBytes)
    {
        try
        {
            // Parse WAV header
            int pos = 12;
            int sampleRate = 22050;
            int channels = 1;
            int bitsPerSample = 16;
            byte[] pcmData = null;

            while (pos + 8 <= wavBytes.Length)
            {
                string id = Encoding.ASCII.GetString(wavBytes, pos, 4);
                int size = BitConverter.ToInt32(wavBytes, pos + 4);
                pos += 8;
                if (id == "fmt ")
                {
                    channels = BitConverter.ToInt16(wavBytes, pos + 2);
                    sampleRate = BitConverter.ToInt32(wavBytes, pos + 4);
                    bitsPerSample = BitConverter.ToInt16(wavBytes, pos + 14);
                    pos += size;
                }
                else if (id == "data")
                {
                    pcmData = new byte[Math.Min(size, wavBytes.Length - pos)];
                    Array.Copy(wavBytes, pos, pcmData, 0, pcmData.Length);
                    break;
                }
                else
                {
                    pos += size;
                }
            }

            if (pcmData == null) return null;

            // Convert 16-bit PCM to float samples
            int numSamples = pcmData.Length / 2;
            float[] samples = new float[numSamples];
            for (int i = 0; i < numSamples; i++)
            {
                short s = BitConverter.ToInt16(pcmData, i * 2);
                samples[i] = s / 32768f;
            }

            AudioClip clip = AudioClip.Create(
                "LipSyncIterClip", numSamples / channels, channels, sampleRate, false);
            clip.SetData(samples, 0);
            return clip;
        }
        catch (Exception ex)
        {
            Debug.LogError($"[LipSyncIterator] WavBytesToClip failed: {ex.Message}");
            return null;
        }
    }

    // ── VisemeTimeline parser ─────────────────────────────────────────────────

    static VisemeTimeline ParseVisemeTimeline(string visemesJson, float durationMs)
    {
        try
        {
            var timeline = new VisemeTimeline();
            timeline.text = "iteration_test";
            timeline.durationMs = durationMs;
            timeline.visemes = new List<VisemeEvent>();

            if (string.IsNullOrWhiteSpace(visemesJson) || visemesJson == "[]")
                return timeline;

            // Minimal JSON array parser: [{"time_ms":0,"viseme_id":0}, ...]
            int i = 0;
            while (i < visemesJson.Length)
            {
                int obj_start = visemesJson.IndexOf('{', i);
                if (obj_start < 0) break;
                int obj_end = visemesJson.IndexOf('}', obj_start);
                if (obj_end < 0) break;
                string obj = visemesJson.Substring(obj_start, obj_end - obj_start + 1);

                float timeMs   = ParseJsonFloat(obj, "time_ms", 0f);
                int visemeId   = (int)ParseJsonFloat(obj, "viseme_id", 0f);
                string vName   = VisemeIdToName(visemeId);

                timeline.visemes.Add(new VisemeEvent
                {
                    timeMs    = timeMs,
                    visemeId  = visemeId,
                    visemeName = vName,
                });
                i = obj_end + 1;
            }

            return timeline;
        }
        catch (Exception ex)
        {
            Debug.LogError($"[LipSyncIterator] ParseVisemeTimeline failed: {ex.Message}");
            return null;
        }
    }

    static string VisemeIdToName(int id)
    {
        string[] names = {
            "sil","PP","FF","TH","DD","kk","CH","SS","nn","RR",
            "aa","E","ih","oh","ou"
        };
        return (id >= 0 && id < names.Length) ? names[id] : "sil";
    }

    // ── Minimal JSON helpers ──────────────────────────────────────────────────

    static string JsonExtract(string json, string key)
    {
        // Handles "key": "value"  (string value)
        string q = $"\"{key}\"";
        int ki = json.IndexOf(q);
        if (ki < 0) return null;
        int colon = json.IndexOf(':', ki + q.Length);
        if (colon < 0) return null;
        int vs = colon + 1;
        while (vs < json.Length && json[vs] == ' ') vs++;
        if (vs >= json.Length) return null;
        if (json[vs] == '"')
        {
            int ve = json.IndexOf('"', vs + 1);
            return ve < 0 ? null : json.Substring(vs + 1, ve - vs - 1);
        }
        // Numeric
        int end = vs;
        while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '.' || json[end] == '-'))
            end++;
        return json.Substring(vs, end - vs);
    }

    static string JsonExtractArray(string json, string key)
    {
        string q = $"\"{key}\"";
        int ki = json.IndexOf(q);
        if (ki < 0) return null;
        int colon = json.IndexOf(':', ki + q.Length);
        if (colon < 0) return null;
        int bracket = json.IndexOf('[', colon);
        if (bracket < 0) return null;
        int depth = 0;
        for (int i = bracket; i < json.Length; i++)
        {
            if (json[i] == '[') depth++;
            else if (json[i] == ']') { depth--; if (depth == 0) return json.Substring(bracket, i - bracket + 1); }
        }
        return null;
    }

    static float ParseJsonFloat(string json, string key, float fallback)
    {
        string val = JsonExtract(json, key);
        if (val == null) return fallback;
        return float.TryParse(val, System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture, out float f) ? f : fallback;
    }
}
#endif
