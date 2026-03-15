using UnityEngine;
using UnityEditor;
using System.Text;

public static class FindEyebrowUVs
{
    public static string Run()
    {
        // Use Renderer (not SkinnedMeshRenderer) to find all, then cast
        SkinnedMeshRenderer faceSMR = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            var smr = r as SkinnedMeshRenderer;
            if (smr == null) continue;
            if (r.gameObject.name == "SKM_model4_FaceMesh") { faceSMR = smr; break; }
        }
        if (faceSMR == null) return "ERROR: SKM_model4_FaceMesh still not found via Renderer cast";

        Mesh mesh = faceSMR.sharedMesh;
        if (mesh == null) return "ERROR: sharedMesh is null";

        Vector3[] verts = mesh.vertices;
        Vector2[] uvs = mesh.uv;
        if (uvs == null || uvs.Length == 0) return $"ERROR: no UVs, verts={verts.Length}";

        var sb = new StringBuilder();
        sb.AppendLine($"Found! mesh={mesh.name} verts={verts.Length}");

        float yMin = float.MaxValue, yMax = float.MinValue;
        for (int i = 0; i < verts.Length; i++) {
            if (verts[i].y < yMin) yMin = verts[i].y;
            if (verts[i].y > yMax) yMax = verts[i].y;
        }
        float yRange = yMax - yMin;
        sb.AppendLine($"Local Y: {yMin:F4} to {yMax:F4}");

        // Fine-grained slices
        for (int step = 0; step <= 30; step++)
        {
            float frac = step / 30.0f;
            float ty = yMin + frac * yRange;
            float band = yRange * 0.015f;
            float minV = 1f, maxV = 0f; int n = 0;
            for (int i = 0; i < verts.Length; i++)
            {
                if (verts[i].y < ty - band || verts[i].y > ty + band) continue;
                if (uvs[i].y < minV) minV = uvs[i].y;
                if (uvs[i].y > maxV) maxV = uvs[i].y;
                n++;
            }
            if (n > 5)
                sb.AppendLine($"frac={frac:F2} localY={ty:F4}: n={n} UV_V=[{minV:F3},{maxV:F3}]");
        }
        return sb.ToString();
    }
}
