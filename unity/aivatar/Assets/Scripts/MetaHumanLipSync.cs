using UnityEngine;
using System;
using System.Collections.Generic;

/// <summary>
/// Drives MetaHuman facial bones directly for viseme lip sync.
/// Unlike blendshape-based approaches, bone rotation produces natural
/// articulated jaw movement instead of linear vertex stretching.
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class MetaHumanLipSync : LipSyncBase
{
    [Header("Core References")]
    public SkinnedMeshRenderer faceMesh;

    [Header("Realism Settings")]
    [Range(50, 200)] public float lookAheadMs = 150f;
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private bool isPlaying;
    private int lastVisemeIndex;

    // Bone references
    private Transform[] bones;
    private Vector3[] restPos;
    private Quaternion[] restRot;

    // Per-viseme weights (smoothed)
    private float[] currentWeights = new float[15];
    private float[] targetWeights = new float[15];
    private float[] velocityWeights = new float[15];

    // Bone names we drive
    static readonly string[] BoneNames = {
        "FACIAL_C_Jaw",               // 0
        "FACIAL_C_LipLower",          // 1
        "FACIAL_C_LipUpper",          // 2
        "FACIAL_L_LipCorner",         // 3
        "FACIAL_R_LipCorner",         // 4
        "FACIAL_C_LowerLipRotation",  // 5
        "FACIAL_L_LipLower",          // 6
        "FACIAL_R_LipLower",          // 7
        "FACIAL_L_LipUpper",          // 8
        "FACIAL_R_LipUpper",          // 9
        "FACIAL_C_MouthLower",        // 10 - inner mouth lower (gums area)
        "FACIAL_C_MouthUpper",        // 11 - inner mouth upper (gums area)
        "FACIAL_C_TeethLower",        // 12 - lower teeth
        "FACIAL_C_TeethUpper",        // 13 - upper teeth
        "FACIAL_C_Tongue1",           // 14 - tongue base (counter-rotate vs jaw)
        "FACIAL_C_Tongue2",           // 15 - tongue mid
    };
    const int BONE_COUNT = 16;

    // Per-viseme bone adjustments: [visemeId][boneIdx] = (posOffset, rotEulerOffset)
    // Built once at Awake
    private Vector3[,] posOffsets;  // [15, BONE_COUNT]
    private Vector3[,] rotOffsets;  // [15, BONE_COUNT] (euler angles)

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        FindBones();
        BuildPoseTable();
    }

    void FindBones()
    {
        bones = new Transform[BONE_COUNT];
        restPos = new Vector3[BONE_COUNT];
        restRot = new Quaternion[BONE_COUNT];

        if (faceMesh == null) return;

        // Build lookup from SMR bones
        var lookup = new Dictionary<string, Transform>();
        foreach (var b in faceMesh.bones)
        {
            if (b != null) lookup[b.name] = b;
        }

        for (int i = 0; i < BONE_COUNT; i++)
        {
            if (lookup.TryGetValue(BoneNames[i], out var t))
            {
                bones[i] = t;
                restPos[i] = t.localPosition;
                restRot[i] = t.localRotation;
            }
            else
            {
                Debug.LogWarning($"[MetaHumanLipSync] Bone not found: {BoneNames[i]}");
            }
        }
    }

    void BuildPoseTable()
    {
        posOffsets = new Vector3[15, BONE_COUNT];
        rotOffsets = new Vector3[15, BONE_COUNT];

        // MetaHuman face rig: jaw bone only influences 66 vertices directly.
        // Lip bones are SIBLINGS of jaw, not children — they must be position-driven
        // independently. Jaw rotation helps with chin/jawline but position offsets on
        // jaw + lip + teeth + mouth bones are what visually open the mouth.
        //
        // Bone indices:
        // 0=Jaw, 1=C_LipLower, 2=C_LipUpper, 3=L_Corner, 4=R_Corner,
        // 5=LowerLipRot, 6=L_LipLower, 7=R_LipLower, 8=L_LipUpper, 9=R_LipUpper,
        // 10=MouthLower, 11=MouthUpper, 12=TeethLower, 13=TeethUpper,
        // 14=Tongue1, 15=Tongue2

        // Helper: jaw position drop + rotation + tongue counter-rotation
        void JawOpen(int v, float posY, float deg)
        {
            SetPos(v, 0, 0, posY, 0);
            SetRot(v, 0, deg, 0, 0);
            SetRot(v, 14, -deg * 1.3f, 0, 0);
            SetRot(v, 15, -deg * 0.5f, 0, 0);
        }

        // 0: sil — rest pose (no offsets)

        // 1: PP — lips pressed together
        SetPos(1, 1, 0, 0.003f, 0);
        SetPos(1, 2, 0, -0.003f, 0);
        SetPos(1, 6, 0, 0.002f, 0);
        SetPos(1, 7, 0, 0.002f, 0);
        SetPos(1, 8, 0, -0.002f, 0);
        SetPos(1, 9, 0, -0.002f, 0);

        // 2: FF — lower lip tucked under upper teeth
        JawOpen(2, -0.003f, 3);
        SetPos(2, 1, 0, 0.004f, -0.002f);
        SetPos(2, 6, 0, 0.003f, -0.002f);
        SetPos(2, 7, 0, 0.003f, -0.002f);
        SetRot(2, 5, 8, 0, 0);

        // 3: TH — tongue between teeth, teeth apart
        JawOpen(3, -0.010f, 6);
        SetPos(3, 1, 0, -0.006f, 0);
        SetPos(3, 6, 0, -0.004f, 0);
        SetPos(3, 7, 0, -0.004f, 0);
        SetPos(3, 10, 0, -0.006f, 0);
        SetPos(3, 12, 0, -0.005f, 0);

        // 4: DD — tongue behind teeth, medium open
        JawOpen(4, -0.010f, 6);
        SetPos(4, 1, 0, -0.006f, 0);
        SetPos(4, 6, 0, -0.004f, 0);
        SetPos(4, 7, 0, -0.004f, 0);
        SetPos(4, 10, 0, -0.006f, 0);
        SetPos(4, 12, 0, -0.005f, 0);

        // 5: kk — back tongue, medium open
        JawOpen(5, -0.008f, 5);
        SetPos(5, 1, 0, -0.005f, 0);
        SetPos(5, 6, 0, -0.003f, 0);
        SetPos(5, 7, 0, -0.003f, 0);
        SetPos(5, 10, 0, -0.005f, 0);

        // 6: CH — "sh/ch", lips forward + slightly open
        JawOpen(6, -0.005f, 3);
        SetPos(6, 1, 0, -0.003f, 0.004f);
        SetPos(6, 2, 0, 0.002f, 0.004f);
        SetPos(6, 3, 0.003f, 0, 0.003f);
        SetPos(6, 4, -0.003f, 0, 0.003f);
        SetPos(6, 6, 0.002f, -0.002f, 0.003f);
        SetPos(6, 7, -0.002f, -0.002f, 0.003f);

        // 7: SS — teeth close, lips spread
        SetPos(7, 1, 0, -0.002f, 0);
        SetPos(7, 3, -0.005f, -0.001f, 0);
        SetPos(7, 4, 0.005f, -0.001f, 0);
        SetPos(7, 6, -0.003f, -0.002f, 0);
        SetPos(7, 7, 0.003f, -0.002f, 0);

        // 8: nn — tongue behind teeth, slightly open
        JawOpen(8, -0.005f, 3);
        SetPos(8, 1, 0, -0.004f, 0);
        SetPos(8, 6, 0, -0.002f, 0);
        SetPos(8, 7, 0, -0.002f, 0);
        SetPos(8, 10, 0, -0.003f, 0);

        // 9: RR — lips slightly rounded and forward
        JawOpen(9, -0.005f, 3);
        SetPos(9, 1, 0, -0.003f, 0.003f);
        SetPos(9, 2, 0, 0.001f, 0.003f);
        SetPos(9, 3, 0.002f, 0, 0.003f);
        SetPos(9, 4, -0.002f, 0, 0.003f);
        SetPos(9, 6, 0.001f, -0.002f, 0.002f);
        SetPos(9, 7, -0.001f, -0.002f, 0.002f);

        // 10: aa — WIDE OPEN mouth (most dramatic)
        JawOpen(10, -0.025f, 15);
        SetPos(10, 1, 0, -0.012f, 0);
        SetPos(10, 3, -0.002f, -0.003f, 0);
        SetPos(10, 4, 0.002f, -0.003f, 0);
        SetPos(10, 6, 0, -0.008f, 0);
        SetPos(10, 7, 0, -0.008f, 0);
        SetPos(10, 10, 0, -0.015f, 0);
        SetPos(10, 12, 0, -0.012f, 0);

        // 11: E — "eh", medium open + spread
        JawOpen(11, -0.015f, 10);
        SetPos(11, 1, 0, -0.008f, 0);
        SetPos(11, 3, -0.004f, -0.002f, 0);
        SetPos(11, 4, 0.004f, -0.002f, 0);
        SetPos(11, 6, -0.002f, -0.006f, 0);
        SetPos(11, 7, 0.002f, -0.006f, 0);
        SetPos(11, 10, 0, -0.010f, 0);
        SetPos(11, 12, 0, -0.008f, 0);

        // 12: ih — "ee", narrow opening, lips spread wide
        JawOpen(12, -0.005f, 4);
        SetPos(12, 1, 0, -0.003f, 0);
        SetPos(12, 3, -0.006f, 0, 0);
        SetPos(12, 4, 0.006f, 0, 0);
        SetPos(12, 6, -0.003f, -0.002f, 0);
        SetPos(12, 7, 0.003f, -0.002f, 0);
        SetPos(12, 10, 0, -0.004f, 0);

        // 13: oh — round "O" shape
        JawOpen(13, -0.015f, 8);
        SetPos(13, 1, 0, -0.008f, 0.003f);
        SetPos(13, 2, 0, 0.002f, 0.003f);
        SetPos(13, 3, 0.004f, 0, 0.002f);
        SetPos(13, 4, -0.004f, 0, 0.002f);
        SetPos(13, 6, 0.002f, -0.005f, 0.002f);
        SetPos(13, 7, -0.002f, -0.005f, 0.002f);
        SetPos(13, 10, 0, -0.010f, 0);
        SetPos(13, 12, 0, -0.008f, 0);

        // 14: ou — "oo" tight round pucker forward
        JawOpen(14, -0.010f, 5);
        SetPos(14, 1, 0, -0.005f, 0.005f);
        SetPos(14, 2, 0, 0.002f, 0.005f);
        SetPos(14, 3, 0.005f, 0, 0.004f);
        SetPos(14, 4, -0.005f, 0, 0.004f);
        SetPos(14, 6, 0.003f, -0.003f, 0.004f);
        SetPos(14, 7, -0.003f, -0.003f, 0.004f);
        SetPos(14, 10, 0, -0.006f, 0);
        SetPos(14, 12, 0, -0.005f, 0);
    }

    void SetPos(int viseme, int bone, float x, float y, float z)
    {
        posOffsets[viseme, bone] = new Vector3(x, y, z);
    }
    void SetRot(int viseme, int bone, float x, float y, float z)
    {
        rotOffsets[viseme, bone] = new Vector3(x, y, z);
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
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

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            ResetTargets();
            ApplyBones();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplyBones();
    }

    void UpdateTargets(float elapsedMs)
    {
        Array.Clear(targetWeights, 0, targetWeights.Length);

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

            if (nextId != curId && timeUntilNext < lookAheadMs && nextId < 15)
            {
                float blend = 1.0f - (timeUntilNext / lookAheadMs);
                if (curId < 15) targetWeights[curId] = 1.0f - blend;
                targetWeights[nextId] = blend;
            }
            else if (curId < 15)
            {
                targetWeights[curId] = 1.0f;
            }
        }
    }

    void ApplyBones()
    {
        // Smooth all weights
        for (int v = 0; v < 15; v++)
        {
            currentWeights[v] = Mathf.SmoothDamp(
                currentWeights[v], targetWeights[v],
                ref velocityWeights[v], smoothTime);
        }

        // For each bone, compute the weighted sum of all viseme offsets
        for (int b = 0; b < BONE_COUNT; b++)
        {
            if (bones[b] == null) continue;

            Vector3 totalPosOffset = Vector3.zero;
            Vector3 totalRotOffset = Vector3.zero;

            for (int v = 0; v < 15; v++)
            {
                float w = currentWeights[v];
                if (w < 0.001f) continue;

                totalPosOffset += posOffsets[v, b] * w;
                totalRotOffset += rotOffsets[v, b] * w;
            }

            bones[b].localPosition = restPos[b] + totalPosOffset;
            bones[b].localRotation = restRot[b] * Quaternion.Euler(totalRotOffset);
        }
    }

    void ResetTargets()
    {
        Array.Clear(targetWeights, 0, targetWeights.Length);
    }

    void OnDisable()
    {
        // Reset bones to rest pose when disabled
        for (int b = 0; b < BONE_COUNT; b++)
        {
            if (bones[b] != null)
            {
                bones[b].localPosition = restPos[b];
                bones[b].localRotation = restRot[b];
            }
        }
    }
}
