using UnityEngine;
using System;
using System.Collections.Generic;

/// <summary>
/// Lip sync driven by the UE viseme animation clip.
/// Bakes bone poses from viseme_animation, then applies them at runtime
/// to a separate visible model by matching bone names.
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class AnimClipLipSync : LipSyncBase
{
    [Header("Animation")]
    [Tooltip("The animation clip from viseme_animation.fbx")]
    public AnimationClip visemeClip;

    [Tooltip("Root of the viseme_animation model (source of poses)")]
    public GameObject animRoot;

    [Tooltip("Root of the VISIBLE model to apply poses to. If null, uses animRoot.")]
    public GameObject targetRoot;

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime = 0.03f;
    [Range(20f, 200f)] public float lookAheadMs = 80f;

    [Tooltip("Shift timeline forward to compensate for SmoothDamp settling (ms). " +
             "Rule of thumb: ~1.8 × smoothTime × 1000.")]
    [Range(0f, 300f)] public float smoothAdvanceMs = 40f;

    [Tooltip("If true, continuously crossfade from current to next viseme across the whole gap " +
             "(rather than holding static until lookAheadMs). Prevents 'stuck viseme' on slow speech.")]
    public bool continuousCrossfade = true;

    [Tooltip("When continuousCrossfade is on, this is the ease exponent. 1 = linear, " +
             ">1 biases toward the current viseme (holds longer then transitions faster).")]
    [Range(0.5f, 4f)] public float crossfadeEase = 1.5f;

    [Tooltip("Max crossfade window (ms) when next viseme is silence (v=0). Keeps mouth from " +
             "slowly closing across WAV trailing silence.")]
    [Range(50f, 400f)] public float closeOutMs = 150f;

    [Tooltip("Extra platform-specific offset (ms). Positive = shift visemes earlier.")]
    [Range(-100f, 100f)] public float audioLatencyMs = 0f;

    [Header("Debug")]
    public bool debugLog = false;

    [Header("Recording")]
    [Tooltip("When true, each Update() frame is logged for offline sync analysis.")]
    public bool recordFrames = false;

    // Viseme ID → animation frame
    private static readonly int[] VISEME_FRAMES = {
        0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140
    };
    private const int VISEME_COUNT = 15;

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private int lastVisemeIndex;
    private bool isPlaying;
    private int playFrameCount;

    private AnimationClip runtimeClip;
    private float fps;

    // Pre-baked bone poses indexed by name from the animation source
    private struct BonePose
    {
        public Vector3 localPosition;
        public Quaternion localRotation;
    }
    // visemePoses[visemeId] = dict of boneName -> pose
    private Dictionary<string, BonePose>[] visemePoses;

    // Runtime: bones on the VISIBLE model that we actually move
    private Transform[] targetBones;
    private string[] targetBoneNames;
    private int boneCount;

    // Per-viseme weights with smoothing
    private float[] currentWeights;
    private float[] targetWeights;
    private float[] velocityWeights;

    private float _debugLogTimer = 0f;
    private float _playStartRealtime; // fallback: realtime when Play() was called (always advances)
    private float _clipDuration;      // clip length in seconds

    // Frame recording
    private struct FrameRecord
    {
        public float timeMs;
        public int topVisemeId;
        public float topWeight;
        public float audioMs;
    }
    private List<FrameRecord> _frameLog;

    /// <summary>Returns a snapshot of runtime state for external validation.</summary>
    public string GetDiagnostics()
    {
        if (currentWeights == null) return "NOT_READY";
        int topVis = -1; float topW = 0f;
        for (int i = 0; i < VISEME_COUNT; i++)
            if (currentWeights[i] > topW) { topW = currentWeights[i]; topVis = i; }
        float audioT = audioSource != null ? audioSource.time * 1000f : -1f;
        float wallMs = isPlaying ? (Time.realtimeSinceStartup - _playStartRealtime) * 1000f : -1f;
        bool playing = audioSource != null && audioSource.isPlaying;
        int visCount = activeTimeline?.visemes?.Count ?? 0;
        return $"playing={playing} audioMs={audioT:F0} wallMs={wallMs:F0} " +
               $"frame={Time.frameCount} " +
               $"topViseme={topVis} topWeight={topW:F3} " +
               $"isLipSyncPlaying={isPlaying} lastIdx={lastVisemeIndex} visemeCount={visCount}";
    }

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        Application.runInBackground = true;
    }

    void Start()
    {
        if (visemeClip == null || animRoot == null)
        {
            Debug.LogError("[AnimClipLipSync] visemeClip or animRoot not assigned.");
            return;
        }

        runtimeClip = Instantiate(visemeClip);
        runtimeClip.legacy = true;
        fps = visemeClip.frameRate > 0 ? visemeClip.frameRate : 30f;

        // Collect facial bone names from the animation source
        var srcTransforms = animRoot.GetComponentsInChildren<Transform>(true);
        var facialNames = new HashSet<string>();
        foreach (var t in srcTransforms)
        {
            if (t.name.Contains("FACIAL") || t.name == "head" ||
                t.name.Contains("neck") || t.name.Contains("Jaw"))
                facialNames.Add(t.name);
        }

        // Bake poses from animation source, keyed by bone name
        visemePoses = new Dictionary<string, BonePose>[VISEME_COUNT];
        for (int v = 0; v < VISEME_COUNT; v++)
        {
            float time = VISEME_FRAMES[v] / fps;
            runtimeClip.SampleAnimation(animRoot, time);

            visemePoses[v] = new Dictionary<string, BonePose>();
            foreach (var t in srcTransforms)
            {
                if (facialNames.Contains(t.name))
                {
                    visemePoses[v][t.name] = new BonePose
                    {
                        localPosition = t.localPosition,
                        localRotation = t.localRotation
                    };
                }
            }
        }

        // Reset animation source to rest pose
        runtimeClip.SampleAnimation(animRoot, 0f);

        // Find matching bones on the TARGET model (the visible one)
        var applyRoot = targetRoot != null ? targetRoot : animRoot;
        var tgtTransforms = applyRoot.GetComponentsInChildren<Transform>(true);
        var matchedBones = new List<Transform>();
        var matchedNames = new List<string>();
        foreach (var t in tgtTransforms)
        {
            if (facialNames.Contains(t.name) && visemePoses[0].ContainsKey(t.name))
            {
                matchedBones.Add(t);
                matchedNames.Add(t.name);
            }
        }
        targetBones = matchedBones.ToArray();
        targetBoneNames = matchedNames.ToArray();
        boneCount = targetBones.Length;

        currentWeights = new float[VISEME_COUNT];
        targetWeights = new float[VISEME_COUNT];
        velocityWeights = new float[VISEME_COUNT];

        Debug.Log($"[AnimClipLipSync] Ready: {facialNames.Count} source bones, " +
                  $"{boneCount} matched on target '{applyRoot.name}', {VISEME_COUNT} poses baked");
    }

    void OnDestroy()
    {
        if (runtimeClip != null)
            Destroy(runtimeClip);
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline = timeline;
        lastVisemeIndex = 0;

        audioSource.Stop();
        audioSource.clip = clip;
        audioSource.loop = false;
        audioSource.Play();

        isPlaying = true;
        playFrameCount = 0;
        _playStartRealtime = Time.realtimeSinceStartup;
        _clipDuration = clip.length;

        if (recordFrames)
            _frameLog = new List<FrameRecord>(512);

        Debug.Log($"[AnimClipLipSync] Play() — visemes={timeline?.visemes?.Count ?? 0} " +
                  $"clip={clip?.length:F2}s sampleRate={clip?.frequency}");
    }

    void Update()
    {
        if (targetBones == null || visemePoses == null) return;

        if (!isPlaying || activeTimeline == null)
        {
            if (currentWeights != null)
            {
                Array.Clear(targetWeights, 0, VISEME_COUNT);
                SmoothAndApply();
            }
            return;
        }

        // Use audioSource.time if it advances; otherwise fall back to realtime.
        // Unity 6 can return time=0 permanently for runtime-created clips.
        float audioTimeMs;
        if (audioSource.timeSamples > 0 || audioSource.time > 0f)
            audioTimeMs = audioSource.time * 1000f;
        else
            audioTimeMs = (Time.realtimeSinceStartup - _playStartRealtime) * 1000f;
        float elapsedMs = Mathf.Max(0f, audioTimeMs + smoothAdvanceMs + audioLatencyMs);

        playFrameCount++;
        float wallElapsed = Time.realtimeSinceStartup - _playStartRealtime;

        // End detection: stop as soon as audio reports done OR wall-clock exceeds clip length.
        // playFrameCount > 10 guard prevents false-positive before playback starts.
        // wallElapsed > _clipDuration * 0.3f guard prevents stopping if audioSource.isPlaying
        // briefly returns false on the very first frames before the clip starts.
        bool audioStopped = !audioSource.isPlaying
                            && playFrameCount > 10
                            && wallElapsed > _clipDuration * 0.3f;
        bool pastClipEnd = playFrameCount > 10 && wallElapsed > _clipDuration + 0.05f;
        if (audioStopped || pastClipEnd)
        {
            isPlaying = false;
            Array.Clear(targetWeights, 0, VISEME_COUNT);
            SmoothAndApply();
            return;
        }

        UpdateTargets(elapsedMs);
        SmoothAndApply();

        // Per-frame recording for offline sync analysis
        if (recordFrames && _frameLog != null)
        {
            int topVis = 0; float topW = 0f;
            for (int i = 0; i < VISEME_COUNT; i++)
                if (currentWeights[i] > topW) { topW = currentWeights[i]; topVis = i; }
            float rawAudioMs = audioSource != null ? audioSource.time * 1000f : 0f;
            _frameLog.Add(new FrameRecord
            {
                timeMs = elapsedMs,
                topVisemeId = topVis,
                topWeight = topW,
                audioMs = rawAudioMs,
            });
        }

        if (debugLog)
        {
            _debugLogTimer -= Time.deltaTime;
            if (_debugLogTimer <= 0f)
            {
                _debugLogTimer = 1f;
                int top = -1; float topW = 0f;
                for (int i = 0; i < VISEME_COUNT; i++)
                    if (currentWeights[i] > topW) { topW = currentWeights[i]; top = i; }
                Debug.Log($"[AnimClipLipSync] t={elapsedMs:F0}ms topViseme={top}(w={topW:F2}) playing={audioSource.isPlaying}");
            }
        }
    }

    private void UpdateTargets(float elapsedMs)
    {
        Array.Clear(targetWeights, 0, VISEME_COUNT);

        while (lastVisemeIndex < activeTimeline.visemes.Count - 1 &&
               activeTimeline.visemes[lastVisemeIndex + 1].timeMs <= elapsedMs)
            lastVisemeIndex++;

        // At or past the last event (always the trailing silence from the scheduler):
        // leave targetWeights cleared so SmoothDamp decays to the rest pose immediately
        // instead of holding the last mouth shape until AudioSource reports done.
        if (lastVisemeIndex < 0 || lastVisemeIndex >= activeTimeline.visemes.Count - 1)
            return;

        int curId = Mathf.Clamp(activeTimeline.visemes[lastVisemeIndex].visemeId, 0, VISEME_COUNT - 1);
        int nextId = curId;
        float nextMs = activeTimeline.durationMs;

        for (int j = lastVisemeIndex + 1; j < activeTimeline.visemes.Count; j++)
        {
            if (activeTimeline.visemes[j].visemeId != curId)
            {
                nextId = Mathf.Clamp(activeTimeline.visemes[j].visemeId, 0, VISEME_COUNT - 1);
                nextMs = activeTimeline.visemes[j].timeMs;
                break;
            }
        }

        float curMs = activeTimeline.visemes[lastVisemeIndex].timeMs;
        float timeUntilNext = nextMs - elapsedMs;
        float gap = Mathf.Max(1f, nextMs - curMs);

        if (nextId == curId)
        {
            targetWeights[curId] = 1f;
        }
        else if (continuousCrossfade)
        {
            if (nextId == 0)
            {
                // Close-to-silence: start closing immediately from curMs so the mouth
                // doesn't hold the last phoneme while the WAV's trailing silence plays.
                // windowEnd is clamped to nextMs so we never overshoot the silence event.
                float windowEnd = Mathf.Min(curMs + closeOutMs, nextMs);
                float t = Mathf.Clamp01((elapsedMs - curMs) / Mathf.Max(1f, windowEnd - curMs));
                targetWeights[curId] = 1f - t;
                // targetWeights[0] stays 0; SmoothDamp decays to rest naturally
            }
            else
            {
                // Continuous crossfade across the whole gap — mouth is always in motion
                float t = Mathf.Clamp01((elapsedMs - curMs) / gap);
                float blend = Mathf.Pow(t, crossfadeEase);
                targetWeights[curId] = 1f - blend;
                targetWeights[nextId] = blend;
            }
        }
        else if (timeUntilNext < lookAheadMs)
        {
            float blend = 1f - (timeUntilNext / lookAheadMs);
            targetWeights[curId] = 1f - blend;
            targetWeights[nextId] = blend;
        }
        else
        {
            targetWeights[curId] = 1f;
        }
    }

    /// <summary>
    /// Returns the recorded frame log as a JSON array string.
    /// Call after isLipSyncPlaying goes false.
    /// Format: [{"time_ms":…,"top_viseme_id":…,"top_weight":…,"audio_ms":…}, …]
    /// </summary>
    public string GetFrameLogJson()
    {
        if (_frameLog == null || _frameLog.Count == 0)
            return "[]";
        var sb = new System.Text.StringBuilder();
        sb.Append('[');
        for (int i = 0; i < _frameLog.Count; i++)
        {
            var f = _frameLog[i];
            if (i > 0) sb.Append(',');
            sb.Append($"{{\"time_ms\":{f.timeMs:F1},\"top_viseme_id\":{f.topVisemeId}," +
                      $"\"top_weight\":{f.topWeight:F4},\"audio_ms\":{f.audioMs:F1}}}");
        }
        sb.Append(']');
        return sb.ToString();
    }

    /// <summary>Clear the recorded frame log.</summary>
    public void ClearFrameLog()
    {
        _frameLog?.Clear();
    }

    private void SmoothAndApply()
    {
        for (int i = 0; i < VISEME_COUNT; i++)
            currentWeights[i] = Mathf.SmoothDamp(
                currentWeights[i], targetWeights[i],
                ref velocityWeights[i], smoothTime);

        // Rest pose from viseme 0 (silence)
        var restPoses = visemePoses[0];

        for (int b = 0; b < boneCount; b++)
        {
            string name = targetBoneNames[b];
            if (!restPoses.TryGetValue(name, out var rest)) continue;

            Vector3 pos = rest.localPosition;
            Quaternion rot = rest.localRotation;

            for (int v = 1; v < VISEME_COUNT; v++)
            {
                float w = currentWeights[v];
                if (w < 0.001f) continue;

                if (!visemePoses[v].TryGetValue(name, out var pose)) continue;

                pos += (pose.localPosition - rest.localPosition) * w;
                rot = Quaternion.Slerp(rot, pose.localRotation, w);
            }

            targetBones[b].localPosition = pos;
            targetBones[b].localRotation = rot;
        }
    }
}
