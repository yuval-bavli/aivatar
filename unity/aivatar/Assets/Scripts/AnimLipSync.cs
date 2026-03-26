using UnityEngine;
using System;
using System.Collections.Generic;

/// <summary>
/// Lip sync driven by pre-baked bone poses from the UE viseme animation.
/// In the Editor, call AnimLipSyncSetup.Setup() to extract bone poses from
/// viseme_animation.fbx and wire everything up.
/// At runtime, interpolates between stored bone poses based on Azure TTS viseme events.
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class AnimLipSync : LipSyncBase
{
    [Header("Viseme Bone Poses (set by Editor script)")]
    public AnimLipSyncData poseData;

    [Header("Target (the viseme_animation root)")]
    public Transform animModelRoot;

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;
    [Range(50f, 200f)] public float lookAheadMs = 150f;

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private int lastVisemeIndex;
    private bool isPlaying;

    // Runtime interpolation state
    private float[] currentWeights;
    private float[] targetWeights;
    private float[] velocityWeights;

    // Cached bone references (resolved from poseData.boneNames at Start)
    private Transform[] bones;
    private Vector3[] restPositions;
    private Quaternion[] restRotations;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
    }

    void Start()
    {
        if (poseData == null)
        {
            Debug.LogError("[AnimLipSync] poseData not assigned. Run Aivatar > Setup AnimLipSync.");
            return;
        }
        if (animModelRoot == null)
        {
            Debug.LogError("[AnimLipSync] animModelRoot not assigned.");
            return;
        }

        // Resolve bone references by name
        int boneCount = poseData.boneNames.Length;
        bones = new Transform[boneCount];
        restPositions = new Vector3[boneCount];
        restRotations = new Quaternion[boneCount];

        // Build a name→Transform lookup from the hierarchy
        var boneLookup = new Dictionary<string, Transform>();
        foreach (var t in animModelRoot.GetComponentsInChildren<Transform>(true))
        {
            if (!boneLookup.ContainsKey(t.name))
                boneLookup[t.name] = t;
        }

        int found = 0;
        for (int i = 0; i < boneCount; i++)
        {
            if (boneLookup.TryGetValue(poseData.boneNames[i], out var t))
            {
                bones[i] = t;
                restPositions[i] = t.localPosition;
                restRotations[i] = t.localRotation;
                found++;
            }
        }

        Debug.Log($"[AnimLipSync] Resolved {found}/{boneCount} bones, {poseData.visemeCount} visemes");

        currentWeights = new float[poseData.visemeCount];
        targetWeights = new float[poseData.visemeCount];
        velocityWeights = new float[poseData.visemeCount];
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline = timeline;
        lastVisemeIndex = 0;
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        Debug.Log($"[AnimLipSync] Play() — visemes={timeline?.visemes?.Count ?? 0} clip={clip?.length:F2}s");
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null || poseData == null) return;

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            Array.Clear(targetWeights, 0, targetWeights.Length);
            ApplyPose();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplyPose();
    }

    private void UpdateTargets(float elapsedMs)
    {
        Array.Clear(targetWeights, 0, targetWeights.Length);

        while (lastVisemeIndex < activeTimeline.visemes.Count - 1 &&
               activeTimeline.visemes[lastVisemeIndex + 1].timeMs <= elapsedMs)
            lastVisemeIndex++;

        if (lastVisemeIndex < 0 || lastVisemeIndex >= activeTimeline.visemes.Count) return;

        int curId = activeTimeline.visemes[lastVisemeIndex].visemeId;
        int nextId = curId;
        float nextMs = activeTimeline.durationMs;

        for (int j = lastVisemeIndex + 1; j < activeTimeline.visemes.Count; j++)
        {
            if (activeTimeline.visemes[j].visemeId != curId)
            {
                nextId = activeTimeline.visemes[j].visemeId;
                nextMs = activeTimeline.visemes[j].timeMs;
                break;
            }
        }

        float timeUntilNext = nextMs - elapsedMs;

        if (nextId != curId && timeUntilNext < lookAheadMs &&
            nextId < poseData.visemeCount)
        {
            float blend = 1f - (timeUntilNext / lookAheadMs);
            if (curId < poseData.visemeCount) targetWeights[curId] = 1f - blend;
            if (nextId < poseData.visemeCount) targetWeights[nextId] = blend;
        }
        else if (curId < poseData.visemeCount)
        {
            targetWeights[curId] = 1f;
        }
    }

    private void ApplyPose()
    {
        if (bones == null || poseData == null) return;

        // Smooth weights
        for (int i = 0; i < poseData.visemeCount; i++)
            currentWeights[i] = Mathf.SmoothDamp(
                currentWeights[i], targetWeights[i],
                ref velocityWeights[i], smoothTime);

        // Apply weighted bone poses
        int boneCount = bones.Length;
        for (int b = 0; b < boneCount; b++)
        {
            if (bones[b] == null) continue;

            Vector3 pos = restPositions[b];
            Quaternion rot = restRotations[b];

            for (int v = 0; v < poseData.visemeCount; v++)
            {
                float w = currentWeights[v];
                if (w < 0.001f) continue;

                // Get the delta from rest for this viseme+bone
                var pose = poseData.GetPose(v, b);
                pos += (pose.localPosition - restPositions[b]) * w;
                rot = Quaternion.Slerp(rot,
                    Quaternion.Slerp(restRotations[b], pose.localRotation, w),
                    1f); // accumulate rotation blending
            }

            bones[b].localPosition = pos;
            bones[b].localRotation = rot;
        }
    }
}
