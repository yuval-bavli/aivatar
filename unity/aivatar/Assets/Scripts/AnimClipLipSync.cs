using UnityEngine;
using System;
using System.Collections.Generic;

/// <summary>
/// Lip sync driven by the UE viseme animation clip.
/// Instead of scrubbing through the timeline (which hits intermediate poses),
/// this samples two viseme poses and blends bone transforms directly.
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class AnimClipLipSync : LipSyncBase
{
    [Header("Animation")]
    [Tooltip("The animation clip from viseme_animation.fbx")]
    public AnimationClip visemeClip;

    [Tooltip("Root of the viseme_animation model in the scene")]
    public GameObject animRoot;

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;
    [Range(50f, 200f)] public float lookAheadMs = 150f;

    // Viseme ID → animation frame
    private static readonly int[] VISEME_FRAMES = {
        0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140
    };
    private const int VISEME_COUNT = 15;

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private int lastVisemeIndex;
    private bool isPlaying;

    private AnimationClip runtimeClip;
    private float fps;

    // Pre-baked bone poses: one set per viseme
    private struct BonePose
    {
        public Vector3 localPosition;
        public Quaternion localRotation;
    }
    private BonePose[][] visemePoses; // [visemeId][boneIndex]
    private Transform[] trackedBones;
    private int boneCount;

    // Per-viseme weights with smoothing
    private float[] currentWeights;
    private float[] targetWeights;
    private float[] velocityWeights;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
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

        // Collect all facial bones from the hierarchy
        var allTransforms = animRoot.GetComponentsInChildren<Transform>(true);
        var facialBones = new List<Transform>();
        foreach (var t in allTransforms)
        {
            if (t.name.Contains("FACIAL") || t.name == "head" ||
                t.name.Contains("neck") || t.name.Contains("Jaw"))
                facialBones.Add(t);
        }
        trackedBones = facialBones.ToArray();
        boneCount = trackedBones.Length;

        // Pre-bake all viseme poses by sampling the animation at each viseme frame
        visemePoses = new BonePose[VISEME_COUNT][];
        for (int v = 0; v < VISEME_COUNT; v++)
        {
            float time = VISEME_FRAMES[v] / fps;
            runtimeClip.SampleAnimation(animRoot, time);

            visemePoses[v] = new BonePose[boneCount];
            for (int b = 0; b < boneCount; b++)
            {
                visemePoses[v][b] = new BonePose
                {
                    localPosition = trackedBones[b].localPosition,
                    localRotation = trackedBones[b].localRotation
                };
            }
        }

        // Reset to rest
        runtimeClip.SampleAnimation(animRoot, 0f);

        currentWeights = new float[VISEME_COUNT];
        targetWeights = new float[VISEME_COUNT];
        velocityWeights = new float[VISEME_COUNT];

        Debug.Log($"[AnimClipLipSync] Ready: {boneCount} bones, {VISEME_COUNT} poses baked");
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
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        Debug.Log($"[AnimClipLipSync] Play() — visemes={timeline?.visemes?.Count ?? 0} clip={clip?.length:F2}s");
    }

    void Update()
    {
        if (trackedBones == null || visemePoses == null) return;

        if (!isPlaying || activeTimeline == null)
        {
            // Fade all weights to zero (rest = viseme 0 = sil)
            Array.Clear(targetWeights, 0, VISEME_COUNT);
            SmoothAndApply();
            return;
        }

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            Array.Clear(targetWeights, 0, VISEME_COUNT);
            SmoothAndApply();
            return;
        }

        UpdateTargets(elapsedMs);
        SmoothAndApply();
    }

    private void UpdateTargets(float elapsedMs)
    {
        Array.Clear(targetWeights, 0, VISEME_COUNT);

        while (lastVisemeIndex < activeTimeline.visemes.Count - 1 &&
               activeTimeline.visemes[lastVisemeIndex + 1].timeMs <= elapsedMs)
            lastVisemeIndex++;

        if (lastVisemeIndex < 0 || lastVisemeIndex >= activeTimeline.visemes.Count) return;

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

        float timeUntilNext = nextMs - elapsedMs;

        if (nextId != curId && timeUntilNext < lookAheadMs)
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

    private void SmoothAndApply()
    {
        // Smooth each viseme weight independently
        for (int i = 0; i < VISEME_COUNT; i++)
            currentWeights[i] = Mathf.SmoothDamp(
                currentWeights[i], targetWeights[i],
                ref velocityWeights[i], smoothTime);

        // Apply weighted blend of bone poses
        // Start from the rest pose (viseme 0 = sil) as base
        var restPoses = visemePoses[0];

        for (int b = 0; b < boneCount; b++)
        {
            Vector3 pos = restPoses[b].localPosition;
            Quaternion rot = restPoses[b].localRotation;

            // Accumulate weighted deltas from non-rest visemes
            for (int v = 1; v < VISEME_COUNT; v++)
            {
                float w = currentWeights[v];
                if (w < 0.001f) continue;

                // Additive position delta
                pos += (visemePoses[v][b].localPosition - restPoses[b].localPosition) * w;

                // Blend rotation toward this viseme's rotation
                rot = Quaternion.Slerp(rot, visemePoses[v][b].localRotation, w);
            }

            trackedBones[b].localPosition = pos;
            trackedBones[b].localRotation = rot;
        }
    }
}
