#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class DiagnoseMouth
{
    [MenuItem("Aivatar/Diagnose Mouth Region")]
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Find face MeshFilter
        MeshFilter faceMF = null;
        foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mf.name.ToLower().Contains("facemesh"))
            { faceMF = mf; break; }
        }
        if (faceMF == null) return "No MeshFilter with 'facemesh'";

        Transform meshTf = faceMF.transform;
        Mesh mesh = faceMF.sharedMesh;
        Vector3[] verts = mesh.vertices;
        Bounds bounds = mesh.bounds;

        sb.AppendLine($"MeshFilter: '{faceMF.name}'  transform pos={meshTf.position}  rot={meshTf.eulerAngles}  scale={meshTf.lossyScale}");
        sb.AppendLine($"Mesh bounds: center={bounds.center}  size={bounds.size}");
        sb.AppendLine($"Verts: {verts.Length}");

        // Find lip corner bones in scene
        var lipL = GameObject.Find("FACIAL_L_LipCorner");
        var lipR = GameObject.Find("FACIAL_R_LipCorner");
        var jaw = GameObject.Find("FACIAL_C_Jaw");

        if (lipL != null) sb.AppendLine($"FACIAL_L_LipCorner world={lipL.transform.position}");
        if (lipR != null) sb.AppendLine($"FACIAL_R_LipCorner world={lipR.transform.position}");
        if (jaw != null) sb.AppendLine($"FACIAL_C_Jaw world={jaw.transform.position}");

        // Transform bone world positions to mesh local space
        if (lipL != null)
        {
            Vector3 localL = meshTf.InverseTransformPoint(lipL.transform.position);
            sb.AppendLine($"LipCornerL in mesh-local: {localL}");
        }
        if (lipR != null)
        {
            Vector3 localR = meshTf.InverseTransformPoint(lipR.transform.position);
            sb.AppendLine($"LipCornerR in mesh-local: {localR}");
        }

        // Transform a few vertices to world space and find closest to lip bones
        if (lipL != null && lipR != null)
        {
            Vector3 mouthWorld = (lipL.transform.position + lipR.transform.position) * 0.5f;
            sb.AppendLine($"Mouth center (world): {mouthWorld}");

            // Find closest vertex in WORLD space
            float minDist = float.MaxValue;
            int minIdx = -1;
            for (int i = 0; i < verts.Length; i++)
            {
                Vector3 worldV = meshTf.TransformPoint(verts[i]);
                float d = Vector3.Distance(worldV, mouthWorld);
                if (d < minDist) { minDist = d; minIdx = i; }
            }

            if (minIdx >= 0)
            {
                Vector3 closestLocal = verts[minIdx];
                Vector3 closestWorld = meshTf.TransformPoint(closestLocal);
                sb.AppendLine($"Closest vertex to mouth (world): idx={minIdx}  local={closestLocal}  world={closestWorld}  dist={minDist:F4}");
            }

            // Also find closest vertex in LOCAL space (to see if local transform is offset)
            Vector3 mouthLocal = meshTf.InverseTransformPoint(mouthWorld);
            float minDistLocal = float.MaxValue;
            int minIdxLocal = -1;
            for (int i = 0; i < verts.Length; i++)
            {
                float d = Vector3.Distance(verts[i], mouthLocal);
                if (d < minDistLocal) { minDistLocal = d; minIdxLocal = i; }
            }
            sb.AppendLine($"Mouth in local space: {mouthLocal}");
            sb.AppendLine($"Closest vert (local search): idx={minIdxLocal}  pos={verts[minIdxLocal]}  dist={minDistLocal:F4}");

            // Show some vertex stats around the world-space mouth
            int nearCount = 0;
            for (int i = 0; i < verts.Length; i++)
            {
                Vector3 worldV = meshTf.TransformPoint(verts[i]);
                if (Vector3.Distance(worldV, mouthWorld) < 0.05f) nearCount++;
            }
            sb.AppendLine($"Vertices within 0.05 of mouth (world): {nearCount}");

            // Sample: what do the first 5 vertices look like in local vs world?
            sb.AppendLine("Sample vertex transforms (local -> world):");
            for (int i = 0; i < Mathf.Min(5, verts.Length); i++)
            {
                Vector3 w = meshTf.TransformPoint(verts[i]);
                sb.AppendLine($"  v[{i}] local={verts[i]}  world={w}");
            }
        }

        string result = sb.ToString();
        Debug.Log("[DiagnoseMouth]\n" + result);
        return result;
    }
}
#endif
