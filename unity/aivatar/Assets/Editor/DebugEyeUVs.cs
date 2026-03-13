using UnityEngine;
using UnityEditor;

public class DebugEyeUVs
{
    [MenuItem("Aivatar/Debug Eye UVs")]
    static void DebugUVs()
    {
        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (!path.Contains("SKM_model4_FaceMesh")) continue;

            var mf = r.GetComponent<MeshFilter>();
            if (mf == null || mf.sharedMesh == null) continue;

            var mesh = mf.sharedMesh;
            var uvs = mesh.uv;
            var vertices = mesh.vertices;
            var mats = r.sharedMaterials;

            Debug.Log($"Mesh: {mesh.name}, submeshes: {mesh.subMeshCount}, materials: {mats.Length}");

            for (int si = 0; si < mesh.subMeshCount; si++)
            {
                var indices = mesh.GetIndices(si);
                var uniqueVerts = new System.Collections.Generic.HashSet<int>();
                foreach (int idx in indices) uniqueVerts.Add(idx);

                // Compute center position
                Vector3 center = Vector3.zero;
                foreach (int idx in uniqueVerts) center += vertices[idx];
                center /= uniqueVerts.Count;

                // Compute bounding box
                Vector3 min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
                Vector3 max = new Vector3(float.MinValue, float.MinValue, float.MinValue);
                foreach (int idx in uniqueVerts)
                {
                    min = Vector3.Min(min, vertices[idx]);
                    max = Vector3.Max(max, vertices[idx]);
                }
                Vector3 size = max - min;

                string matName = (si < mats.Length && mats[si] != null) ? mats[si].name : "none";

                // Compute tangent aspect for submeshes with eye-like UVs
                float uvMinU = float.MaxValue, uvMaxU = float.MinValue;
                float uvMinV = float.MaxValue, uvMaxV = float.MinValue;
                foreach (int idx in uniqueVerts)
                {
                    if (idx < uvs.Length)
                    {
                        uvMinU = Mathf.Min(uvMinU, uvs[idx].x);
                        uvMaxU = Mathf.Max(uvMaxU, uvs[idx].x);
                        uvMinV = Mathf.Min(uvMinV, uvs[idx].y);
                        uvMaxV = Mathf.Max(uvMaxV, uvs[idx].y);
                    }
                }

                float tangentAspect = 0;
                int triCount = 0;
                float totalU = 0, totalV = 0;
                for (int t = 0; t < indices.Length; t += 3)
                {
                    int i0 = indices[t], i1 = indices[t+1], i2 = indices[t+2];
                    if (i0 >= uvs.Length || i1 >= uvs.Length || i2 >= uvs.Length) continue;
                    Vector2 uv0 = uvs[i0], uv1 = uvs[i1], uv2 = uvs[i2];
                    Vector2 uvC = (uv0 + uv1 + uv2) / 3f;
                    if (Vector2.Distance(uvC, new Vector2(0.5f, 0.5f)) > 0.15f) continue;
                    Vector2 duv1 = uv1 - uv0, duv2 = uv2 - uv0;
                    Vector3 dp1 = vertices[i1] - vertices[i0], dp2 = vertices[i2] - vertices[i0];
                    float det = duv1.x * duv2.y - duv1.y * duv2.x;
                    if (Mathf.Abs(det) < 1e-8f) continue;
                    float inv = 1f / det;
                    Vector3 dpdu = (dp1 * duv2.y - dp2 * duv1.y) * inv;
                    Vector3 dpdv = (dp2 * duv1.x - dp1 * duv2.x) * inv;
                    totalU += dpdu.magnitude;
                    totalV += dpdv.magnitude;
                    triCount++;
                }
                if (triCount > 0) tangentAspect = (totalU / triCount) / (totalV / triCount);

                Debug.Log($"  [{si}] mat={matName}, verts={uniqueVerts.Count}, tris={indices.Length/3}, " +
                    $"center=({center.x:F4},{center.y:F4},{center.z:F4}), " +
                    $"size=({size.x:F4},{size.y:F4},{size.z:F4}), " +
                    $"UV=[{uvMinU:F2}..{uvMaxU:F2}, {uvMinV:F2}..{uvMaxV:F2}], " +
                    $"tangentAspect={tangentAspect:F3}");
            }
            return;
        }
        Debug.LogWarning("Face mesh not found!");
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null) { t = t.parent; path = t.name + "/" + path; }
        return path;
    }
}
