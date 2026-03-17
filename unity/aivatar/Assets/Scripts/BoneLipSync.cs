using UnityEngine;
using System;

// Bone-based lip sync for MetaHuman rigs that have no blendshapes.
// Drives FACIAL_C_Jaw (jaw open), FACIAL_C_LowerLipRotation (pucker),
// and FACIAL_L/R_LipCorner (spread) based on Azure viseme events.
[RequireComponent(typeof(AudioSource))]
public class BoneLipSync : LipSyncBase
{
    [Header("Bone References — filled by Aivatar > Wire Model4 (Bones)")]
    public Transform jawBone;           // FACIAL_C_Jaw
    public Transform lowerLipBone;      // FACIAL_C_LowerLipRotation
    public Transform lipCornerL;        // FACIAL_L_LipCorner
    public Transform lipCornerR;        // FACIAL_R_LipCorner

    [Header("Jaw Settings")]
    public Vector3 jawOpenAxis   = new Vector3(1, 0, 0); // local rotation axis
    [Range(5f, 45f)]  public float jawMaxDegrees    = 20f;

    [Header("Lip Settings")]
    [Range(0f, 15f)]  public float lipCornerSpread  = 6f;  // degrees outward per side
    [Range(0f, 15f)]  public float lipPuckerDegrees = 6f;  // lower-lip forward rotation

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime   = 0.08f;
    [Range(50f, 200f)]   public float lookAheadMs  = 150f;

    // Per-viseme targets: [jaw 0-1, corner 0-1, pucker 0-1]
    // Indexed by Azure viseme ID 0-14.
    private static readonly float[,] VISEME_POSE = new float[15, 3]
    {
        //              jaw    corner  pucker
        /* 0  sil */ { 0.00f,  0.00f,  0.00f },
        /* 1  PP  */ { 0.00f,  0.00f,  0.00f },
        /* 2  FF  */ { 0.05f,  0.00f,  0.00f },
        /* 3  TH  */ { 0.15f,  0.00f,  0.00f },
        /* 4  DD  */ { 0.15f,  0.00f,  0.00f },
        /* 5  kk  */ { 0.20f,  0.00f,  0.00f },
        /* 6  CH  */ { 0.20f,  0.30f,  0.00f },
        /* 7  SS  */ { 0.05f,  0.20f,  0.00f },
        /* 8  nn  */ { 0.05f,  0.00f,  0.00f },
        /* 9  RR  */ { 0.30f,  0.00f,  0.30f },
        /* 10 aa  */ { 1.00f,  0.50f,  0.00f },
        /* 11 E   */ { 0.60f,  0.60f,  0.00f },
        /* 12 ih  */ { 0.30f,  0.30f,  0.00f },
        /* 13 oh  */ { 0.70f,  0.00f,  0.40f },
        /* 14 ou  */ { 0.30f,  0.00f,  0.80f },
    };

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private int lastVisemeIndex;
    private bool isPlaying;

    // Smoothed [jaw, corner, pucker]
    private float[] current    = new float[3];
    private float[] target     = new float[3];
    private float[] velocities = new float[3];

    // Rest rotations captured on Start
    private Quaternion jawRest, lowerLipRest, cornerLRest, cornerRRest;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
    }

    void Start()
    {
        if (jawBone)      jawRest      = jawBone.localRotation;
        if (lowerLipBone) lowerLipRest = lowerLipBone.localRotation;
        if (lipCornerL)   cornerLRest  = lipCornerL.localRotation;
        if (lipCornerR)   cornerRRest  = lipCornerR.localRotation;
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline  = timeline;
        lastVisemeIndex = 0;
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        Debug.Log($"[BoneLipSync] Play() called — visemes={timeline?.visemes?.Count ?? 0}  clipLength={clip?.length:F2}s" +
                  $"  jaw={jawBone?.name ?? "NULL"}");
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null) return;

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            Array.Clear(target, 0, 3);
            ApplySmoothing();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplySmoothing();
    }

    private void UpdateTargets(float elapsedMs)
    {
        Array.Clear(target, 0, target.Length);

        while (lastVisemeIndex < activeTimeline.visemes.Count - 1 &&
               activeTimeline.visemes[lastVisemeIndex + 1].timeMs <= elapsedMs)
            lastVisemeIndex++;

        if (lastVisemeIndex < 0 || lastVisemeIndex >= activeTimeline.visemes.Count) return;

        int curId    = activeTimeline.visemes[lastVisemeIndex].visemeId;
        int nextId   = curId;
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

        float blend        = 0f;
        float timeUntilNext = nextMs - elapsedMs;
        if (nextId != curId && timeUntilNext < lookAheadMs)
            blend = 1f - (timeUntilNext / lookAheadMs);

        int a = Mathf.Clamp(curId,  0, 14);
        int b = Mathf.Clamp(nextId, 0, 14);

        for (int i = 0; i < 3; i++)
            target[i] = Mathf.Lerp(VISEME_POSE[a, i], VISEME_POSE[b, i], blend);
    }

    private void ApplySmoothing()
    {
        for (int i = 0; i < 3; i++)
            current[i] = Mathf.SmoothDamp(current[i], target[i], ref velocities[i], smoothTime);

        float jaw    = current[0];
        float corner = current[1];
        float pucker = current[2];

        if (jawBone)
            jawBone.localRotation = jawRest * Quaternion.AngleAxis(jaw * jawMaxDegrees, jawOpenAxis);

        if (lowerLipBone)
            lowerLipBone.localRotation = lowerLipRest * Quaternion.AngleAxis(pucker * lipPuckerDegrees, Vector3.right);

        if (lipCornerL)
            lipCornerL.localRotation = cornerLRest * Quaternion.AngleAxis( corner * lipCornerSpread, Vector3.forward);

        if (lipCornerR)
            lipCornerR.localRotation = cornerRRest * Quaternion.AngleAxis(-corner * lipCornerSpread, Vector3.forward);
    }
}
