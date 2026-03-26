using UnityEngine;
using System;

// Vertex-deformation lip sync for MetaHuman faces exported without skin weights.
// Translates lower jaw/chin vertices downward to open the mouth,
// spreads lip corners, and pushes lower lip forward for pucker.
[RequireComponent(typeof(AudioSource))]
public class BoneLipSync : LipSyncBase
{
    [Header("Bone References — filled by Aivatar > Wire Model4 (Bones)")]
    public Transform jawBone;           // FACIAL_C_Jaw
    public Transform lowerLipBone;      // FACIAL_C_LowerLipRotation
    public Transform lipCornerL;        // FACIAL_L_LipCorner
    public Transform lipCornerR;        // FACIAL_R_LipCorner

    [Header("Face Mesh")]
    public MeshFilter faceMeshFilter;

    [Header("Jaw Settings")]
    [Tooltip("How far the chin drops at full open, as a fraction of mouth width")]
    [Range(0.1f, 2f)] public float jawOpenScale = 1.0f;

    [Header("Lip Settings")]
    [Range(0f, 1f)] public float lipCornerSpreadScale = 0.15f;
    [Range(0f, 1f)] public float lipPuckerForwardScale = 0.12f;

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime  = 0.08f;
    [Range(50f, 200f)]   public float lookAheadMs = 150f;

    // Per-viseme targets: [jaw 0-1, corner 0-1, pucker 0-1]
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

    private float[] current    = new float[3];
    private float[] target     = new float[3];
    private float[] velocities = new float[3];

    private Mesh deformMesh;
    private Vector3[] restVertices;
    private Vector3[] deformedVertices;

    // Per-vertex weights
    private float[] jawWeights;      // 0-1: moves vertex downward when jaw opens
    private float[] cornerWeights;   // -1 to 1: moves vertex left/right for lip spread
    private float[] puckerWeights;   // 0-1: moves vertex forward for pucker
    private float[] upperLipWeights; // 0-1: moves vertex slightly UP when jaw opens (lip separation)

    private Vector3 mouthCenterLocal;
    private float mouthWidth;
    private Vector3 localRight;
    private Vector3 localForward;
    private Vector3 localDown;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
    }

    void Start()
    {
        if (faceMeshFilter == null || lipCornerL == null || lipCornerR == null)
        {
            Debug.LogError("[BoneLipSync] faceMeshFilter or lip corner bones not assigned.");
            return;
        }

        deformMesh = Instantiate(faceMeshFilter.sharedMesh);
        faceMeshFilter.mesh = deformMesh;

        restVertices = deformMesh.vertices;
        deformedVertices = new Vector3[restVertices.Length];
        Array.Copy(restVertices, deformedVertices, restVertices.Length);

        ComputeVertexWeights();
    }

    private void ComputeVertexWeights()
    {
        Transform meshTf = faceMeshFilter.transform;

        Vector3 cornerLLocal = meshTf.InverseTransformPoint(lipCornerL.position);
        Vector3 cornerRLocal = meshTf.InverseTransformPoint(lipCornerR.position);
        mouthCenterLocal = (cornerLLocal + cornerRLocal) * 0.5f;
        mouthWidth = Vector3.Distance(cornerLLocal, cornerRLocal);

        // Local axes from bone geometry
        localRight = (cornerLLocal - cornerRLocal).normalized;
        localDown = -Vector3.up; // Y down in local space
        localForward = Vector3.Cross(localRight, Vector3.up).normalized;

        // Ensure forward points toward the viewer (away from the back of the head)
        Vector3 jawLocal = jawBone != null ? meshTf.InverseTransformPoint(jawBone.position) : mouthCenterLocal;
        if (Vector3.Dot(mouthCenterLocal - jawLocal, localForward) < 0)
            localForward = -localForward;

        // Define zones relative to mouth width
        float mouthHalfWidth = mouthWidth * 0.5f;
        float lipZoneRadius = mouthWidth * 0.7f;   // region for corner/pucker effects
        float jawZoneRadius = mouthWidth * 1.8f;    // wider zone for jaw drop
        float upperLipBand  = mouthWidth * 0.15f;   // thin band above mouth line for upper lip

        Debug.Log($"[BoneLipSync] Diagnostics:" +
                  $"\n  mouthCenter={mouthCenterLocal}  mouthWidth={mouthWidth:F4}" +
                  $"\n  cornerL={cornerLLocal}  cornerR={cornerRLocal}" +
                  $"\n  localRight={localRight}  localFwd={localForward}" +
                  $"\n  lipZone={lipZoneRadius:F4}  jawZone={jawZoneRadius:F4}");

        int count = restVertices.Length;
        jawWeights = new float[count];
        cornerWeights = new float[count];
        puckerWeights = new float[count];
        upperLipWeights = new float[count];

        float mouthY = mouthCenterLocal.y;

        for (int i = 0; i < count; i++)
        {
            Vector3 v = restVertices[i];
            Vector3 toMouth = v - mouthCenterLocal;

            float vertFromMouth = v.y - mouthY; // positive = above mouth
            float horizDist = Mathf.Abs(Vector3.Dot(toMouth, localRight)); // left-right only
            float dist3D = toMouth.magnitude;

            // ---- JAW (lower jaw drops down) ----
            // Use only left-right distance for cutoff (not 3D — chin is far in depth too)
            if (vertFromMouth < upperLipBand && horizDist < jawZoneRadius)
            {
                float belowAmount = -vertFromMouth; // positive = below mouth
                float w;

                if (belowAmount > mouthHalfWidth)
                    w = 1.0f;
                else if (belowAmount > 0)
                    w = belowAmount / mouthHalfWidth;
                else
                    w = 0f;

                // Horizontal falloff only (left-right)
                w *= Mathf.Clamp01(1.0f - (horizDist / jawZoneRadius));
                jawWeights[i] = w;
            }

            // ---- UPPER LIP (slight upward pull to help open the mouth gap) ----
            if (vertFromMouth >= -mouthWidth * 0.1f && vertFromMouth < upperLipBand &&
                horizDist < mouthHalfWidth * 1.3f)
            {
                float t = 1.0f - Mathf.Clamp01(Mathf.Abs(vertFromMouth) / upperLipBand);
                float hFalloff = 1.0f - (horizDist / (mouthHalfWidth * 1.3f));
                upperLipWeights[i] = Mathf.Clamp01(t * hFalloff) * 0.4f;
            }

            // ---- CORNER (lip spread outward) ----
            if (dist3D < lipZoneRadius)
            {
                float proximity = 1.0f - (dist3D / lipZoneRadius);
                proximity *= proximity;
                float side = Vector3.Dot(toMouth, localRight);
                cornerWeights[i] = Mathf.Sign(side) * proximity;
            }

            // ---- PUCKER (lips push forward) ----
            if (dist3D < lipZoneRadius * 0.6f)
            {
                float proximity = 1.0f - (dist3D / (lipZoneRadius * 0.6f));
                proximity *= proximity;
                if (vertFromMouth > mouthWidth * 0.15f) proximity = 0f;
                puckerWeights[i] = proximity;
            }
        }

        int jawC = 0, cornerC = 0, puckerC = 0, upperC = 0;
        float maxJawW = 0, maxCornerW = 0, maxPuckerW = 0, maxUpperW = 0;
        for (int i = 0; i < count; i++)
        {
            if (jawWeights[i] > 0.01f) jawC++;
            if (Mathf.Abs(cornerWeights[i]) > 0.01f) cornerC++;
            if (puckerWeights[i] > 0.01f) puckerC++;
            if (upperLipWeights[i] > 0.01f) upperC++;
            maxJawW = Mathf.Max(maxJawW, jawWeights[i]);
            maxCornerW = Mathf.Max(maxCornerW, Mathf.Abs(cornerWeights[i]));
            maxPuckerW = Mathf.Max(maxPuckerW, puckerWeights[i]);
            maxUpperW = Mathf.Max(maxUpperW, upperLipWeights[i]);
        }
        float maxJawDrop = jawOpenScale * mouthWidth;
        Debug.Log($"[BoneLipSync] Weights: jaw={jawC}(max={maxJawW:F2})  upper={upperC}(max={maxUpperW:F2})" +
                  $"  corner={cornerC}(max={maxCornerW:F2})  pucker={puckerC}(max={maxPuckerW:F2}) / {count}" +
                  $"\n  jawMaxDrop={maxJawDrop:F4} units ({maxJawDrop/deformMesh.bounds.size.y*100:F1}% of face height)");
    }

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline  = timeline;
        lastVisemeIndex = 0;
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        Debug.Log($"[BoneLipSync] Play() — visemes={timeline?.visemes?.Count ?? 0}  clip={clip?.length:F2}s");
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null) return;

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            Array.Clear(target, 0, 3);
            ApplyDeformation();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplyDeformation();
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

        float blend = 0f;
        float timeUntilNext = nextMs - elapsedMs;
        if (nextId != curId && timeUntilNext < lookAheadMs)
            blend = 1f - (timeUntilNext / lookAheadMs);

        int a = Mathf.Clamp(curId,  0, 14);
        int b = Mathf.Clamp(nextId, 0, 14);

        for (int i = 0; i < 3; i++)
            target[i] = Mathf.Lerp(VISEME_POSE[a, i], VISEME_POSE[b, i], blend);
    }

    private void ApplyDeformation()
    {
        for (int i = 0; i < 3; i++)
            current[i] = Mathf.SmoothDamp(current[i], target[i], ref velocities[i], smoothTime);

        if (deformMesh == null || restVertices == null) return;

        float jaw    = current[0];
        float corner = current[1];
        float pucker = current[2];

        // Jaw open distance: fraction of mouth width
        float jawDrop = jaw * jawOpenScale * mouthWidth;
        float upperPull = jaw * 0.3f * jawOpenScale * mouthWidth; // upper lip pulls up slightly
        float cornerAmount = corner * lipCornerSpreadScale * mouthWidth;
        float puckerAmount = pucker * lipPuckerForwardScale * mouthWidth;

        for (int i = 0; i < restVertices.Length; i++)
        {
            Vector3 v = restVertices[i];
            Vector3 offset = Vector3.zero;

            // Jaw: translate lower face downward
            if (jawWeights[i] > 0.001f)
                offset += localDown * (jawWeights[i] * jawDrop);

            // Upper lip: pull slightly upward to widen the mouth gap
            if (upperLipWeights[i] > 0.001f)
                offset -= localDown * (upperLipWeights[i] * upperPull);

            // Corner spread
            if (Mathf.Abs(cornerWeights[i]) > 0.001f)
                offset += localRight * (cornerWeights[i] * cornerAmount);

            // Pucker forward
            if (puckerWeights[i] > 0.001f)
                offset += localForward * (puckerWeights[i] * puckerAmount);

            deformedVertices[i] = v + offset;
        }

        deformMesh.vertices = deformedVertices;
        deformMesh.RecalculateNormals();
        deformMesh.RecalculateBounds();
    }
}
