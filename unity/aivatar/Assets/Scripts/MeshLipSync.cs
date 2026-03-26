using UnityEngine;
using System;

// Runtime lip sync that applies baked viseme blendshape deltas to a MeshFilter.
// Works with MetaHuman faces that have MeshRenderer (not SkinnedMeshRenderer).
// Pair with BakeVisemeBlendShapes editor script to create the visemeMesh asset.
[RequireComponent(typeof(AudioSource))]
public class MeshLipSync : LipSyncBase
{
    [Header("References — filled by Aivatar > Bake Viseme BlendShapes")]
    public MeshFilter faceMeshFilter;
    public Mesh visemeMesh; // Asset with 15 blendshape frames baked in

    [Header("Smoothing")]
    [Range(0.01f, 0.2f)] public float smoothTime = 0.08f;
    [Range(50f, 200f)] public float lookAheadMs = 150f;

    private AudioSource audioSource;
    private VisemeTimeline activeTimeline;
    private int lastVisemeIndex;
    private bool isPlaying;

    // Blendshape delta arrays extracted from visemeMesh (one per viseme)
    private Vector3[][] visemeDeltas;
    private int visemeCount;

    // Runtime deformation
    private Mesh deformMesh;
    private Vector3[] restVertices;
    private Vector3[] deformedVertices;

    // Per-viseme weights (smoothed)
    private float[] currentWeights;
    private float[] targetWeights;
    private float[] velocityWeights;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
    }

    void Start()
    {
        if (faceMeshFilter == null)
        { Debug.LogError("[MeshLipSync] faceMeshFilter not assigned."); return; }
        if (visemeMesh == null)
        { Debug.LogError("[MeshLipSync] visemeMesh not assigned. Run Aivatar > Bake Viseme BlendShapes."); return; }

        visemeCount = visemeMesh.blendShapeCount;
        if (visemeCount == 0)
        { Debug.LogError("[MeshLipSync] visemeMesh has no blendshapes."); return; }

        // Extract delta arrays from the baked mesh asset
        int vertCount = visemeMesh.vertexCount;
        visemeDeltas = new Vector3[visemeCount][];
        for (int i = 0; i < visemeCount; i++)
        {
            visemeDeltas[i] = new Vector3[vertCount];
            var dn = new Vector3[vertCount];
            var dt = new Vector3[vertCount];
            visemeMesh.GetBlendShapeFrameVertices(i, 0, visemeDeltas[i], dn, dt);
        }

        // Clone the face mesh for runtime deformation
        deformMesh = Instantiate(faceMeshFilter.sharedMesh);
        faceMeshFilter.mesh = deformMesh;
        restVertices = deformMesh.vertices;
        deformedVertices = new Vector3[restVertices.Length];
        Array.Copy(restVertices, deformedVertices, restVertices.Length);

        currentWeights = new float[visemeCount];
        targetWeights = new float[visemeCount];
        velocityWeights = new float[visemeCount];

        // Verify delta integrity
        int totalNonZero = 0;
        float globalMax = 0;
        for (int v = 0; v < visemeCount; v++)
        {
            int nz = 0;
            float mx = 0;
            for (int j = 0; j < vertCount; j++)
            {
                float m = visemeDeltas[v][j].magnitude;
                if (m > 0.0001f) nz++;
                if (m > mx) mx = m;
            }
            totalNonZero += nz;
            if (mx > globalMax) globalMax = mx;
        }

        Debug.Log($"[MeshLipSync] Ready: {visemeCount} visemes, {vertCount} verts" +
                  $"\n  faceMesh verts={restVertices.Length}  visemeMesh verts={vertCount}" +
                  $"\n  totalNonZeroDeltas={totalNonZero}  globalMaxDelta={globalMax:F6}");
    }

    private int logCountdown = 0;

    public override void Play(VisemeTimeline timeline, AudioClip clip)
    {
        activeTimeline = timeline;
        lastVisemeIndex = 0;
        audioSource.clip = clip;
        audioSource.Play();
        isPlaying = true;
        logCountdown = 10; // Log first 10 frames
        Debug.Log($"[MeshLipSync] Play() — visemes={timeline?.visemes?.Count ?? 0}  clip={clip?.length:F2}s");
    }

    void Update()
    {
        if (!isPlaying || activeTimeline == null) return;

        float elapsedMs = audioSource.time * 1000f;

        if (!audioSource.isPlaying && elapsedMs == 0f)
        {
            isPlaying = false;
            Array.Clear(targetWeights, 0, targetWeights.Length);
            ApplyDeformation();
            return;
        }

        UpdateTargets(elapsedMs);
        ApplyDeformation();

        if (logCountdown > 0)
        {
            logCountdown--;
            float maxW = 0;
            int activeIdx = -1;
            for (int i = 0; i < visemeCount; i++)
            {
                if (currentWeights[i] > maxW) { maxW = currentWeights[i]; activeIdx = i; }
            }
            float maxVertMove = 0;
            for (int i = 0; i < restVertices.Length; i++)
            {
                float d = (deformedVertices[i] - restVertices[i]).magnitude;
                if (d > maxVertMove) maxVertMove = d;
            }
            Debug.Log($"[MeshLipSync] Frame: elapsed={elapsedMs:F1}ms  activeViseme={activeIdx}  weight={maxW:F3}  maxVertexMove={maxVertMove:F6}");
        }
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

        if (nextId != curId && timeUntilNext < lookAheadMs && nextId < visemeCount)
        {
            float blend = 1f - (timeUntilNext / lookAheadMs);
            if (curId < visemeCount) targetWeights[curId] = 1f - blend;
            if (nextId < visemeCount) targetWeights[nextId] = blend;
        }
        else if (curId < visemeCount)
        {
            targetWeights[curId] = 1f;
        }
    }

    private void ApplyDeformation()
    {
        if (deformMesh == null || restVertices == null || visemeDeltas == null) return;

        // Smooth weights
        for (int i = 0; i < visemeCount; i++)
            currentWeights[i] = Mathf.SmoothDamp(currentWeights[i], targetWeights[i], ref velocityWeights[i], smoothTime);

        // Apply weighted sum of viseme deltas
        int vertCount = restVertices.Length;
        Array.Copy(restVertices, deformedVertices, vertCount);

        for (int v = 0; v < visemeCount; v++)
        {
            float w = currentWeights[v];
            if (w < 0.001f) continue;

            var deltas = visemeDeltas[v];
            for (int i = 0; i < vertCount; i++)
                deformedVertices[i] += deltas[i] * w;
        }

        deformMesh.vertices = deformedVertices;
        deformMesh.RecalculateNormals();
        deformMesh.RecalculateBounds();
    }
}
