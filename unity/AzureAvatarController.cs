using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class AzureAvatarController : MonoBehaviour
{
    [Header("Mesh References")]
    public SkinnedMeshRenderer faceMesh;
    public Transform leftEyebrow;
    public Transform rightEyebrow;

    [Header("Realism Settings")]
    public float lookAheadMs = 150f;     // Matches your "Realistic" request
    public float smoothTime = 0.08f;     // The "weight" of the muscles
    public float maxTotalWeight = 1.2f;  // Prevents mesh tearing
    public float browRaiseAmount = 0.02f;

    [Header("State")]
    public bool isSpeaking = false;

    private VisemeTimeline activeTimeline;
    private float startTime;
    private float[] currentWeights = new float[22]; 
    private float[] targetWeights = new float[22];
    private float[] velocityWeights = new float[22]; // For SmoothDamp

    private Vector3 browNeutralPosL;
    private Vector3 browNeutralPosR;

    void Start() {
        if (leftEyebrow) browNeutralPosL = leftEyebrow.localPosition;
        if (rightEyebrow) browNeutralPosR = rightEyebrow.localPosition;
    }

    public void PlaySpeech(VisemeTimeline timeline) {
        activeTimeline = timeline;
        startTime = Time.time;
        isSpeaking = true;
    }

    void Update() {
        if (!isSpeaking || activeTimeline == null) {
            HandleIdleExpressions();
            return;
        }

        float elapsedMs = (Time.time - startTime) * 1000f;

        // End of sequence check
        if (elapsedMs > activeTimeline.durationMs + 200f) {
            isSpeaking = false;
            return;
        }

        CalculateVisemeWeights(elapsedMs);
        AnimateFace();
    }

    private void CalculateVisemeWeights(float elapsedMs) {
        System.Array.Clear(targetWeights, 0, targetWeights.Length);

        // 1. Binary Search for current viseme index
        int curIdx = -1;
        for (int i = 0; i < activeTimeline.visemes.Count; i++) {
            if (activeTimeline.visemes[i].timeMs <= elapsedMs) curIdx = i;
            else break;
        }

        if (curIdx != -1) {
            int curId = activeTimeline.visemes[curIdx].visemeId;
            
            // 2. Look ahead for next viseme to start cross-fading
            int nextId = curId;
            float nextTimeMs = activeTimeline.durationMs;

            for (int j = curIdx + 1; j < activeTimeline.visemes.Count; j++) {
                if (activeTimeline.visemes[j].visemeId != curId) {
                    nextId = activeTimeline.visemes[j].visemeId;
                    nextTimeMs = activeTimeline.visemes[j].timeMs;
                    break;
                }
            }

            float timeUntilNext = nextTimeMs - elapsedMs;

            // 3. Realistic Smoothing Logic
            if (nextId != curId && timeUntilNext < lookAheadMs) {
                float blend = 1.0f - (timeUntilNext / lookAheadMs);
                targetWeights[curId] = 1.0f - blend;
                targetWeights[nextId] = blend;
            } else {
                targetWeights[curId] = 1.0f;
            }
        }

        // 4. Clamp Weights
        float total = 0;
        foreach (float w in targetWeights) total += w;
        if (total > maxTotalWeight) {
            float scale = maxTotalWeight / total;
            for (int i = 0; i < targetWeights.Length; i++) targetWeights[i] *= scale;
        }
    }

    private void AnimateFace() {
        // Apply SmoothDamp to all weights for "Muscle Mass" feel
        for (int i = 0; i < currentWeights.Length; i++) {
            currentWeights[i] = Mathf.SmoothDamp(currentWeights[i], targetWeights[i], ref velocityWeights[i], smoothTime);
            
            if (i < faceMesh.sharedMesh.blendShapeCount) {
                faceMesh.SetBlendShapeWeight(i, currentWeights[i] * 100f);
            }
        }

        // Eyebrow Raise Layer
        if (leftEyebrow && rightEyebrow) {
            float raise = isSpeaking ? browRaiseAmount : 0f;
            Vector3 targetL = browNeutralPosL + new Vector3(0, raise, 0);
            leftEyebrow.localPosition = Vector3.Lerp(leftEyebrow.localPosition, targetL, Time.deltaTime * 5f);
            rightEyebrow.localPosition = Vector3.Lerp(rightEyebrow.localPosition, targetL, Time.deltaTime * 5f);
        }
    }

    private void HandleIdleExpressions() {
        // Slowly return mouth to neutral
        for (int i = 0; i < currentWeights.Length; i++) {
            currentWeights[i] = Mathf.SmoothDamp(currentWeights[i], 0, ref velocityWeights[i], smoothTime * 2);
            if (i < faceMesh.sharedMesh.blendShapeCount)
                faceMesh.SetBlendShapeWeight(i, currentWeights[i] * 100f);
        }
        // Reset Brows
        if (leftEyebrow) leftEyebrow.localPosition = Vector3.Lerp(leftEyebrow.localPosition, browNeutralPosL, Time.deltaTime * 2f);
    }
}