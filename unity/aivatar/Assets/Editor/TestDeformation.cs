#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class TestDeformation
{
    [MenuItem("Aivatar/Test Deformation (Static)")]
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Load the baked viseme mesh
        string meshPath = "Assets/Models/Avatar/SKM_model4_FaceMesh_Visemes.asset";
        var visemeMesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
        if (visemeMesh == null) return $"Viseme mesh not found at {meshPath}";

        sb.AppendLine($"Viseme mesh: {visemeMesh.name}  bs={visemeMesh.blendShapeCount}  verts={visemeMesh.vertexCount}");

        // Check each blendshape for non-zero deltas
        int vertCount = visemeMesh.vertexCount;
        for (int bs = 0; bs < visemeMesh.blendShapeCount; bs++)
        {
            string name = visemeMesh.GetBlendShapeName(bs);
            Vector3[] deltas = new Vector3[vertCount];
            Vector3[] dn = new Vector3[vertCount];
            Vector3[] dt = new Vector3[vertCount];
            visemeMesh.GetBlendShapeFrameVertices(bs, 0, deltas, dn, dt);

            int nonZero = 0;
            float maxMag = 0;
            for (int i = 0; i < vertCount; i++)
            {
                float mag = deltas[i].magnitude;
                if (mag > 0.0001f) nonZero++;
                if (mag > maxMag) maxMag = mag;
            }
            sb.AppendLine($"  [{bs}] '{name}': nonZero={nonZero}  maxDelta={maxMag:F6}");
        }

        // Also find the face MeshFilter and check what mesh it's using
        MeshFilter faceMF = null;
        foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mf.name.ToLower().Contains("facemesh"))
            { faceMF = mf; break; }
        }
        if (faceMF != null)
        {
            sb.AppendLine($"\nFace MeshFilter: '{faceMF.name}'  mesh='{faceMF.sharedMesh?.name}'  verts={faceMF.sharedMesh?.vertexCount}");
            sb.AppendLine($"  Transform: pos={faceMF.transform.position}  rot={faceMF.transform.eulerAngles}");

            // Check if vertexCount matches
            if (faceMF.sharedMesh != null && faceMF.sharedMesh.vertexCount != visemeMesh.vertexCount)
                sb.AppendLine($"  WARNING: vertex count mismatch! face={faceMF.sharedMesh.vertexCount} vs viseme={visemeMesh.vertexCount}");
        }

        string result = sb.ToString();
        Debug.Log("[TestDeformation]\n" + result);
        return result;
    }
}
#endif
