#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

// Applies a huge obvious deformation to the face mesh to verify
// that MeshFilter vertex deformation is actually visible.
public static class TestBigDeform
{
    [MenuItem("Aivatar/Test Big Deform (toggle)")]
    public static string Run()
    {
        MeshFilter faceMF = null;
        foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mf.name.ToLower().Contains("facemesh"))
            { faceMF = mf; break; }
        }
        if (faceMF == null) return "No FaceMesh MeshFilter found";

        Mesh mesh = faceMF.sharedMesh;
        if (mesh == null || !mesh.isReadable) return "Mesh null or not readable";

        Transform meshTf = faceMF.transform;
        var lipLGO = GameObject.Find("FACIAL_L_LipCorner");
        var lipRGO = GameObject.Find("FACIAL_R_LipCorner");
        if (lipLGO == null || lipRGO == null) return "Lip corner bones not found";

        Vector3 mouthLocal = meshTf.InverseTransformPoint(
            (lipLGO.transform.position + lipRGO.transform.position) * 0.5f);

        Vector3[] verts = mesh.vertices;
        int moved = 0;

        // Move every vertex below the mouth line DOWN by 0.05 units (huge, obvious)
        for (int i = 0; i < verts.Length; i++)
        {
            float vertDist = verts[i].y - mouthLocal.y;
            if (vertDist < 0)
            {
                float w = Mathf.Clamp01(-vertDist / 0.04f);
                verts[i].y -= 0.05f * w;  // Move chin down by 5cm
                moved++;
            }
        }

        mesh.vertices = verts;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        return $"Deformed {moved}/{verts.Length} verts below mouth (mouthY={mouthLocal.y:F4}). If you see NO change, the MeshFilter is not what's being rendered!";
    }
}
#endif
