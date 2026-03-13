using UnityEngine;
using UnityEditor;

public class DebugMaterials
{
    // Assign a unique bright color to each material slot on the face mesh
    // so we can visually identify which submesh is which
    [MenuItem("Aivatar/Color-Code Face Submeshes")]
    static void ColorCodeFaceSubmeshes()
    {
        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (!path.Contains("SKM_model4_FaceMesh")) continue;

            Color[] colors = new Color[]
            {
                Color.red,       // 0
                Color.green,     // 1
                Color.blue,      // 2
                Color.yellow,    // 3
                Color.cyan,      // 4
                Color.magenta,   // 5
                new Color(1, 0.5f, 0), // 6 orange
                Color.white,     // 7
                new Color(0.5f, 0, 0.5f), // 8 purple
            };

            string[] names = new string[]
            {
                "MI_Teeth_Baked",
                "M_Hide",
                "MI_EyeL_Baked",
                "MI_EyeR_Baked",
                "MI_Face_EyeShell",
                "MI_Face_LacrimalFluid",
                "M_Hide_6",
                "MI_Face_Skin_Baked_LOD1_VT",
                "MI_Face_EyelashesHiLODs",
            };

            var mats = r.sharedMaterials;
            var newMats = new Material[mats.Length];
            for (int i = 0; i < mats.Length; i++)
            {
                newMats[i] = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                newMats[i].color = colors[i % colors.Length];
                newMats[i].SetColor("_BaseColor", colors[i % colors.Length]);
                Debug.Log($"Slot[{i}] = {names[i]} -> {colors[i % colors.Length]} (was: {(mats[i] != null ? mats[i].name : "null")})");
            }
            r.sharedMaterials = newMats;
            Debug.Log("Applied color-coded materials. Undo (Ctrl+Z) to restore.");
            return;
        }
        Debug.LogWarning("Face mesh not found!");
    }

    [MenuItem("Aivatar/Debug Materials on Model4")]
    static void DebugModel4Materials()
    {
        var renderers = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in renderers)
        {
            string path = GetPath(r.transform);
            if (!path.Contains("model4")) continue;

            Debug.Log($"=== SkinnedMeshRenderer: {path} | enabled={r.enabled} ===");
            Debug.Log($"  Mesh: {(r.sharedMesh != null ? r.sharedMesh.name : "null")}");
            if (r.sharedMesh != null)
            {
                Debug.Log($"  SubMesh count: {r.sharedMesh.subMeshCount}");
                Debug.Log($"  Vertex count: {r.sharedMesh.vertexCount}");
                Debug.Log($"  Bounds: {r.sharedMesh.bounds}");
                for (int s = 0; s < r.sharedMesh.subMeshCount; s++)
                {
                    var desc = r.sharedMesh.GetSubMesh(s);
                    Debug.Log($"  SubMesh[{s}]: indexCount={desc.indexCount} topology={desc.topology}");
                }
            }
            LogMaterials(r.sharedMaterials);
        }

        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (!path.Contains("model4")) continue;

            var mf = r.GetComponent<MeshFilter>();
            Debug.Log($"=== MeshRenderer: {path} | enabled={r.enabled} ===");
            if (mf != null && mf.sharedMesh != null)
            {
                var mesh = mf.sharedMesh;
                Debug.Log($"  Mesh: {mesh.name}");
                Debug.Log($"  SubMesh count: {mesh.subMeshCount}");
                Debug.Log($"  Vertex count: {mesh.vertexCount}");
                Debug.Log($"  Bounds: {mesh.bounds}");
                for (int s = 0; s < mesh.subMeshCount; s++)
                {
                    var desc = mesh.GetSubMesh(s);
                    Debug.Log($"  SubMesh[{s}]: indexCount={desc.indexCount} topology={desc.topology}");
                }
            }
            LogMaterials(r.sharedMaterials);
        }
    }

    static void LogMaterials(Material[] mats)
    {
        for (int i = 0; i < mats.Length; i++)
        {
            var mat = mats[i];
            if (mat == null) { Debug.Log($"  Material[{i}]: NULL"); continue; }
            string matPath = AssetDatabase.GetAssetPath(mat);
            Debug.Log($"  Material[{i}]: {mat.name} | path: {matPath} | shader: {mat.shader.name}");
            if (mat.HasProperty("_BaseMap"))
            {
                var tex = mat.GetTexture("_BaseMap");
                Debug.Log($"    _BaseMap: {(tex != null ? tex.name + " | " + AssetDatabase.GetAssetPath(tex) : "null")}");
            }
            if (mat.HasProperty("_BumpMap"))
            {
                var tex = mat.GetTexture("_BumpMap");
                Debug.Log($"    _BumpMap: {(tex != null ? tex.name + " | " + AssetDatabase.GetAssetPath(tex) : "null")}");
            }
        }
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null) { t = t.parent; path = t.name + "/" + path; }
        return path;
    }
}
