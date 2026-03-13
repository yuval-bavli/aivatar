using UnityEngine;
using System;

[RequireComponent(typeof(AudioSource))]
public class ProLipSync : MonoBehaviour
{
    [Header("Core References")]
    public SkinnedMeshRenderer faceMesh;
    public VisemeMapping mappingProfile;
    private AudioSource audioSource;

    [Header("Realism Settings")]
    [Range(50, 200)] public float lookAheadMs = 150f;
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;
    [Range(1.0f, 1.5f)] public float maxTotalWeight = 1.2f;

    // Internal State
    private VisemeTimeline activeTimeline;
    private int[] mappedIndices = new int[22]; // Caches the actual mesh indices
    private float[] currentWeights = new float[22];
    private float[] targetWeights = new float[22];
    private float[] velocityWeights = new float[22];
    
    private bool isPlaying = false;
    private int lastVisemeIndex = 0; // Optimization: don't search from 0 every frame

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

    public void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline = timeline;
        lastVisemeIndex = 0;
        
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null) return;

        // PRO UPGRADE: Use AudioSource time, NOT Time.time. 
        // This prevents lips from drifting if the device drops frames.
        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
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