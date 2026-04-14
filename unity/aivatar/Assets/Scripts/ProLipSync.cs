using UnityEngine;
using System;

[RequireComponent(typeof(AudioSource))]
public class ProLipSync : LipSyncBase
{
    [Header("Core References")]
    public SkinnedMeshRenderer faceMesh;
    public VisemeMapping mappingProfile;
    private AudioSource audioSource;

    [Header("Realism Settings")]
    [Range(50, 200)] public float lookAheadMs = 150f;
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;
    [Range(1.0f, 1.5f)] public float maxTotalWeight = 1.2f;

    [Header("Sync")]
    [Tooltip("Compensate for audio hardware latency. Increase if mouth moves before sound is heard.")]
    [Range(-200f, 200f)] public float audioLatencyMs = 0f;

    [Header("Debug")]
    [Tooltip("Log viseme transitions to Console for sync diagnosis")]
    public bool debugLog = false;

    // Internal State
    private VisemeTimeline activeTimeline;
    private int[] mappedIndices = new int[22]; // Caches the actual mesh indices
    private float[] currentWeights = new float[22];
    private float[] targetWeights = new float[22];
    private float[] velocityWeights = new float[22];
    
    private bool isPlaying = false;
    private int lastVisemeIndex = 0; // Optimization: don't search from 0 every frame
    private int playFrameCount = 0;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        InitializeMapping();
    }

    private void InitializeMapping()
    {
        // Fill with -1 (unmapped) by default
        for (int i = 0; i < mappedIndices.Length; i++) mappedIndices[i] = -1;

        if (mappingProfile == null || faceMesh == null) return;

        // Cache the actual blendshape indices based on the string names
        foreach (var map in mappingProfile.mappings)
        {
            if (map.azureId >= 0 && map.azureId < 22)
            {
                int meshIndex = faceMesh.sharedMesh.GetBlendShapeIndex(map.blendShapeName);
                mappedIndices[map.azureId] = meshIndex;
                
                if (meshIndex == -1)
                    Debug.LogWarning($"BlendShape '{map.blendShapeName}' not found on {faceMesh.name}");
            }
        }
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline = timeline;
        lastVisemeIndex = 0;

        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        playFrameCount = 0;

        if (debugLog)
        {
            Debug.Log($"[LipSync] Play: {timeline.visemes.Count} visemes, " +
                      $"clip={clip.length:F3}s, timeline={timeline.durationMs:F0}ms, " +
                      $"smoothAdvance={smoothTime * 700f:F0}ms");
            for (int i = 0; i < Mathf.Min(timeline.visemes.Count, 20); i++)
            {
                var v = timeline.visemes[i];
                Debug.Log($"  [{i}] t={v.timeMs:F0}ms viseme={v.visemeId} ({v.visemeName})");
            }
        }
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null) return;

        // PRO UPGRADE: Use AudioSource time, NOT Time.time.
        // This prevents lips from drifting if the device drops frames.
        // Advance by ~70% of smoothTime to compensate for SmoothDamp response lag,
        // so blendshapes reach target weight at the same time audio plays.
        float smoothAdvanceMs = smoothTime * 700f;
        float elapsedMs = Mathf.Max(0f, audioSource.time * 1000f + smoothAdvanceMs - audioLatencyMs);

        playFrameCount++;
        if (playFrameCount > 3 && !audioSource.isPlaying && audioSource.time == 0f)
        {
            isPlaying = false;
            ResetTargets();
            ApplySmoothing();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplySmoothing();
    }

    private void UpdateTargets(float elapsedMs)
    {
        Array.Clear(targetWeights, 0, targetWeights.Length);

        // Optimization: Start searching from the last known index instead of 0
        int curIdx = lastVisemeIndex;
        while (curIdx < activeTimeline.visemes.Count - 1 &&
               activeTimeline.visemes[curIdx + 1].timeMs <= elapsedMs)
        {
            curIdx++;
        }

        if (debugLog && curIdx != lastVisemeIndex)
        {
            var v = activeTimeline.visemes[curIdx];
            Debug.Log($"[LipSync] audioT={audioSource.time * 1000f:F0}ms " +
                      $"effectiveT={elapsedMs:F0}ms -> viseme {v.visemeId} (event t={v.timeMs:F0}ms)");
        }

        lastVisemeIndex = curIdx;

        if (curIdx >= 0 && curIdx < activeTimeline.visemes.Count)
        {
            int curId = activeTimeline.visemes[curIdx].visemeId;
            int nextId = curId;
            float nextTimeMs = activeTimeline.durationMs;

            // Find next distinct viseme for co-articulation
            for (int j = curIdx + 1; j < activeTimeline.visemes.Count; j++)
            {
                if (activeTimeline.visemes[j].visemeId != curId)
                {
                    nextId = activeTimeline.visemes[j].visemeId;
                    nextTimeMs = activeTimeline.visemes[j].timeMs;
                    break;
                }
            }

            float timeUntilNext = nextTimeMs - elapsedMs;

            if (nextId != curId && timeUntilNext < lookAheadMs && nextId < 22)
            {
                float blend = 1.0f - (timeUntilNext / lookAheadMs);
                if (curId < 22) targetWeights[curId] = 1.0f - blend;
                targetWeights[nextId] = blend;
            }
            else if (curId < 22)
            {
                targetWeights[curId] = 1.0f;
            }
        }

        // Clamp total weight
        float total = 0;
        for (int i = 0; i < targetWeights.Length; i++) total += targetWeights[i];
        
        if (total > maxTotalWeight)
        {
            float scale = maxTotalWeight / total;
            for (int i = 0; i < targetWeights.Length; i++) targetWeights[i] *= scale;
        }
    }

    private void ApplySmoothing()
    {
        for (int i = 0; i < 22; i++)
        {
            currentWeights[i] = Mathf.SmoothDamp(
                currentWeights[i], 
                targetWeights[i], 
                ref velocityWeights[i], 
                smoothTime
            );

            // Only apply if this ID was successfully mapped to a mesh BlendShape
            int meshIndex = mappedIndices[i];
            if (meshIndex != -1)
            {
                faceMesh.SetBlendShapeWeight(meshIndex, currentWeights[i] * 100f);
            }
        }
    }

    private void ResetTargets()
    {
        Array.Clear(targetWeights, 0, targetWeights.Length);
    }
}