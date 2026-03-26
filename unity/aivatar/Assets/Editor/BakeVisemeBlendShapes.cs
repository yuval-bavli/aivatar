#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

// Bakes viseme delta arrays into a mesh asset. Does NOT modify any scene objects.
public static class BakeVisemeBlendShapes
{
    private static readonly (string name, float jaw, float corner, float pucker)[] VISEMES =
    {
        ("sil", 0.00f, 0.00f, 0.00f),
        ("PP",  0.00f, 0.00f, 0.10f),
        ("FF",  0.05f, 0.00f, 0.05f),
        ("TH",  0.15f, 0.00f, 0.00f),
        ("DD",  0.15f, 0.00f, 0.00f),
        ("kk",  0.20f, 0.00f, 0.00f),
        ("CH",  0.20f, 0.30f, 0.00f),
        ("SS",  0.05f, 0.20f, 0.00f),
        ("nn",  0.05f, 0.00f, 0.00f),
        ("RR",  0.30f, 0.00f, 0.30f),
        ("aa",  1.00f, 0.50f, 0.00f),
        ("E",   0.60f, 0.60f, 0.00f),
        ("ih",  0.30f, 0.30f, 0.00f),
        ("oh",  0.70f, 0.00f, 0.40f),
        ("ou",  0.30f, 0.00f, 0.80f),
    };

    [MenuItem("Aivatar/Bake Viseme BlendShapes onto Face")]
    public static void Bake()
    {
        // Find face MeshFilter
        MeshFilter faceMF = null;
        foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mf.name.ToLower().Contains("facemesh"))
            { faceMF = mf; break; }
        }
        if (faceMF == null)
        { Debug.LogError("[BakeViseme] No MeshFilter with 'facemesh' in scene."); return; }

        Mesh srcMesh = faceMF.sharedMesh;
        if (srcMesh == null || !srcMesh.isReadable)
        { Debug.LogError("[BakeViseme] Mesh null or not readable."); return; }

        Transform meshTf = faceMF.transform;
        Vector3[] verts = srcMesh.vertices;
        Vector3[] normals = srcMesh.normals;
        int count = verts.Length;

        // ── Locate mouth from scene bones (transformed to mesh local space) ──
        var lipLGO = GameObject.Find("FACIAL_L_LipCorner");
        var lipRGO = GameObject.Find("FACIAL_R_LipCorner");
        var jawGO  = GameObject.Find("FACIAL_C_Jaw");

        if (lipLGO == null || lipRGO == null)
        { Debug.LogError("[BakeViseme] FACIAL_L/R_LipCorner not found in scene."); return; }

        Vector3 cornerL = meshTf.InverseTransformPoint(lipLGO.transform.position);
        Vector3 cornerR = meshTf.InverseTransformPoint(lipRGO.transform.position);
        Vector3 mouthCenter = (cornerL + cornerR) * 0.5f;
        float mouthWidth = Vector3.Distance(cornerL, cornerR);

        // Local coordinate axes from bone geometry
        Vector3 localRight = (cornerL - cornerR).normalized;  // left-to-right
        // Y axis in mesh local space (up = +Y for this mesh)
        Vector3 localUp = Vector3.up;
        Vector3 localDown = -localUp;
        Vector3 localForward = Vector3.Cross(localRight, localUp).normalized;

        // Ensure forward points toward the front of the face (toward viewer)
        if (jawGO != null)
        {
            Vector3 jawLocal = meshTf.InverseTransformPoint(jawGO.transform.position);
            if (Vector3.Dot(mouthCenter - jawLocal, localForward) < 0)
                localForward = -localForward;
        }

        // Zone sizes — tight around the mouth, based on actual mouth width
        float mouthHalfW = mouthWidth * 0.5f;
        float lipBand = mouthWidth * 0.25f;         // thin vertical band for lip separation
        float jawZoneBelow = mouthWidth * 1.2f;     // how far below mouth the jaw drop extends
        float jawZoneHoriz = mouthWidth * 1.2f;     // horizontal extent of jaw zone
        float lipZoneRadius = mouthWidth * 0.8f;    // radial zone for corner/pucker
        float upperCutoff = mouthWidth * 0.4f;      // don't affect anything this far above mouth

        // Deformation amounts — must be large enough to see on a small mesh
        // The big deform test showed 0.05 units is clearly visible
        float maxJawDrop = 0.05f;        // jaw drops 5cm at full open (viseme "aa")
        float maxUpperPull = 0.012f;     // upper lip lifts slightly
        float maxCornerSpread = 0.015f;  // corners spread outward
        float maxPucker = 0.012f;        // lips push forward

        Debug.Log($"[BakeViseme] Bone-based mouth detection:" +
                  $"\n  cornerL={cornerL}  cornerR={cornerR}" +
                  $"\n  mouthCenter={mouthCenter}  mouthWidth={mouthWidth:F4}" +
                  $"\n  localRight={localRight}  localFwd={localForward}" +
                  $"\n  lipBand={lipBand:F4}  jawZoneBelow={jawZoneBelow:F4}" +
                  $"\n  maxJawDrop={maxJawDrop:F4}  verts={count}");

        // ── Compute per-vertex weights ──
        float[] lowerLipW = new float[count];
        float[] upperLipW = new float[count];
        float[] cornerW = new float[count];
        float[] puckerW = new float[count];

        for (int i = 0; i < count; i++)
        {
            Vector3 v = verts[i];
            Vector3 n = i < normals.Length ? normals[i] : Vector3.up;
            Vector3 toMouth = v - mouthCenter;
            float vertDist = toMouth.y;  // positive = above mouth
            float horizDist = Mathf.Abs(toMouth.x);

            // Skip vertices far from mouth region
            if (vertDist > upperCutoff) continue;           // above nose
            if (vertDist < -jawZoneBelow * 1.2f) continue;  // well below chin
            if (horizDist > jawZoneHoriz * 1.2f) continue;  // far to the sides

            float distXY = new Vector2(toMouth.x, toMouth.y).magnitude;

            // ── LIP SEPARATION (thin band around mouth line) ──
            if (Mathf.Abs(vertDist) < lipBand && horizDist < mouthHalfW * 1.8f)
            {
                float proxToSeam = 1.0f - Mathf.Clamp01(Mathf.Abs(vertDist) / lipBand);
                float horizFade = 1.0f - Mathf.Clamp01(horizDist / (mouthHalfW * 1.8f));
                float lipStrength = proxToSeam * horizFade;

                // Lower lip: normal points down or vertex is below mouth line
                if (n.y < 0.1f || vertDist < -lipBand * 0.15f)
                    lowerLipW[i] = Mathf.Max(lowerLipW[i], lipStrength);
                // Upper lip: vertex near or above mouth line
                if (vertDist > -lipBand * 0.3f)
                    upperLipW[i] = Mathf.Max(upperLipW[i], lipStrength * 0.4f);
            }

            // ── JAW / CHIN (below mouth → drops down) ──
            if (vertDist < 0 && horizDist < jawZoneHoriz)
            {
                float belowAmount = -vertDist;
                float w = Mathf.Clamp01(belowAmount / (mouthWidth * 0.4f));
                w *= Mathf.Clamp01(1.0f - horizDist / jawZoneHoriz);
                // Taper off at the very bottom of the chin
                if (belowAmount > jawZoneBelow * 0.7f)
                    w *= 1.0f - Mathf.Clamp01((belowAmount - jawZoneBelow * 0.7f) / (jawZoneBelow * 0.3f));
                lowerLipW[i] = Mathf.Max(lowerLipW[i], w);
            }

            // ── CORNER SPREAD (lip area moves outward) ──
            if (distXY < lipZoneRadius && Mathf.Abs(vertDist) < lipBand * 1.5f)
            {
                float prox = 1.0f - distXY / lipZoneRadius;
                prox *= prox;
                cornerW[i] = Mathf.Sign(toMouth.x) * prox;
            }

            // ── PUCKER (lip area pushes forward) ──
            if (distXY < lipZoneRadius * 0.5f && vertDist < lipBand && vertDist > -lipBand * 2f)
            {
                float prox = 1.0f - distXY / (lipZoneRadius * 0.5f);
                prox *= prox;
                puckerW[i] = prox;
            }
        }

        int lc = 0, uc = 0, cc = 0, pc = 0;
        float maxLW = 0, maxUW = 0, maxCW = 0, maxPW = 0;
        for (int i = 0; i < count; i++)
        {
            if (lowerLipW[i] > 0.01f) lc++;
            if (upperLipW[i] > 0.01f) uc++;
            if (Mathf.Abs(cornerW[i]) > 0.01f) cc++;
            if (puckerW[i] > 0.01f) pc++;
            maxLW = Mathf.Max(maxLW, lowerLipW[i]);
            maxUW = Mathf.Max(maxUW, upperLipW[i]);
            maxCW = Mathf.Max(maxCW, Mathf.Abs(cornerW[i]));
            maxPW = Mathf.Max(maxPW, puckerW[i]);
        }
        Debug.Log($"[BakeViseme] Weights: lower={lc}(max={maxLW:F2})  upper={uc}(max={maxUW:F2})" +
                  $"  corner={cc}(max={maxCW:F2})  pucker={pc}(max={maxPW:F2}) / {count}");

        if (lc == 0 && uc == 0)
        { Debug.LogError("[BakeViseme] No vertices matched! Aborting."); return; }

        // ── Build blendshapes on a mesh clone ──
        Mesh newMesh = Object.Instantiate(srcMesh);
        newMesh.name = srcMesh.name + "_Visemes";
        newMesh.ClearBlendShapes();

        foreach (var vis in VISEMES)
        {
            Vector3[] deltas = new Vector3[count];
            Vector3[] dn = new Vector3[count];
            Vector3[] dt = new Vector3[count];

            for (int i = 0; i < count; i++)
            {
                Vector3 d = Vector3.zero;
                if (lowerLipW[i] > 0.001f)
                    d += localDown * (lowerLipW[i] * vis.jaw * maxJawDrop);
                if (upperLipW[i] > 0.001f)
                    d += localUp * (upperLipW[i] * vis.jaw * maxUpperPull);
                if (Mathf.Abs(cornerW[i]) > 0.001f)
                    d += localRight * (cornerW[i] * vis.corner * maxCornerSpread);
                if (puckerW[i] > 0.001f)
                    d += localForward * (puckerW[i] * vis.pucker * maxPucker);
                deltas[i] = d;
            }
            newMesh.AddBlendShapeFrame(vis.name, 100f, deltas, dn, dt);
        }

        string meshPath = "Assets/Models/Avatar/SKM_model4_FaceMesh_Visemes.asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
        if (existing != null) AssetDatabase.DeleteAsset(meshPath);
        AssetDatabase.CreateAsset(newMesh, meshPath);
        AssetDatabase.SaveAssets();

        Debug.Log($"[BakeViseme] Saved {newMesh.blendShapeCount} blendshapes to {meshPath}");

        // ── Wire MeshLipSync on Avatar ──
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO != null)
        {
            var oldPro = avatarGO.GetComponent<ProLipSync>();
            if (oldPro != null) Undo.DestroyObjectImmediate(oldPro);
            var oldBone = avatarGO.GetComponent<BoneLipSync>();
            if (oldBone != null) Undo.DestroyObjectImmediate(oldBone);

            var meshLipSync = avatarGO.GetComponent<MeshLipSync>();
            if (meshLipSync == null)
                meshLipSync = Undo.AddComponent<MeshLipSync>(avatarGO);

            Undo.RecordObject(meshLipSync, "Wire MeshLipSync");
            meshLipSync.faceMeshFilter = faceMF;
            meshLipSync.visemeMesh = newMesh;
            EditorUtility.SetDirty(meshLipSync);

            var speech = avatarGO.GetComponent<AzureSpeechManager>();
            if (speech != null)
            {
                Undo.RecordObject(speech, "Wire speech");
                speech.lipSyncController = meshLipSync;
                EditorUtility.SetDirty(speech);
            }

            Debug.Log("[BakeViseme] Wired MeshLipSync. Press Play to test!");
        }
    }
}
#endif
