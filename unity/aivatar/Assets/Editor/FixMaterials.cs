using UnityEngine;
using UnityEditor;
using System.Text;
using System.Collections.Generic;

public class FixMaterials
{
    // Identify each submesh by rendering only it and checking bounds/position
    public static string IdentifySubmeshes()
    {
        var sb = new StringBuilder();

        SkinnedMeshRenderer smr = FindFaceMesh3SMR();
        if (smr == null) return "ERROR: FaceMesh3 SMR not found";

        var mesh = smr.sharedMesh;
        sb.AppendLine($"Mesh: {mesh.name}, submeshes: {mesh.subMeshCount}");

        // For each submesh, compute its bounding box from the triangles
        var verts = mesh.vertices;
        for (int s = 0; s < mesh.subMeshCount; s++)
        {
            var tris = mesh.GetTriangles(s);
            if (tris.Length == 0) { sb.AppendLine($"  [{s}] empty"); continue; }

            Vector3 min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
            Vector3 max = new Vector3(float.MinValue, float.MinValue, float.MinValue);
            HashSet<int> uniqueVerts = new HashSet<int>();

            foreach (int idx in tris)
            {
                uniqueVerts.Add(idx);
                Vector3 v = verts[idx];
                min = Vector3.Min(min, v);
                max = Vector3.Max(max, v);
            }

            Vector3 center = (min + max) * 0.5f;
            Vector3 size = max - min;
            var matName = s < smr.sharedMaterials.Length && smr.sharedMaterials[s] != null
                ? smr.sharedMaterials[s].name : "null";

            sb.AppendLine($"  [{s}] tris={tris.Length/3} verts={uniqueVerts.Count} center=({center.x:F4},{center.y:F4},{center.z:F4}) size=({size.x:F4},{size.y:F4},{size.z:F4}) mat={matName}");
        }

        return sb.ToString();
    }

    // Apply geometry-analyzed material order
    public static string ApplyCorrect()
    {
        SkinnedMeshRenderer smr = FindFaceMesh3SMR();
        if (smr == null) return "ERROR: FaceMesh3 SMR not found";

        var matFolder = "Assets/Models/Avatar/Materials/";
        var allMats = new Dictionary<string, Material>();
        foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { matFolder }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null) allMats[mat.name] = mat;
        }

        // Based on submesh geometry analysis:
        // [0] 12227 verts, face skin
        // [1] 3357 verts, mouth interior (teeth/gums)
        // [2] 424 verts, centered eye overlay (eye shell)
        // [3] 386 verts, x=-0.032 (LEFT eye)
        // [4] 386 verts, x=+0.032 (RIGHT eye)
        // [5] 330 verts, thin near inner eye corners (lacrimal)
        // [6] 1560 verts, thin strips near eyes (eyelashes)
        // [7] 276 verts, tiny (hidden geometry)
        // [8] 338 verts, thin (hidden geometry)
        string[] order = {
            "MI_Face_Skin_Baked_LOD1_VT", // 0
            "MI_Teeth_Baked",              // 1
            "MI_Face_EyeShell",            // 2
            "MI_EyeL_Baked",              // 3
            "MI_EyeR_Baked",              // 4
            "MI_Face_LacrimalFluid",       // 5
            "MI_Face_EyelashesHiLODs",     // 6
            "M_Hide",                       // 7
            "M_Hide_6",                     // 8
        };

        var mats = new Material[order.Length];
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < order.Length; i++)
        {
            mats[i] = allMats.ContainsKey(order[i]) ? allMats[order[i]] : null;
            sb.AppendLine($"  [{i}] {order[i]}: {(mats[i] != null ? "OK" : "MISSING")}");
        }

        smr.sharedMaterials = mats;
        EditorUtility.SetDirty(smr);
        sb.AppendLine("Applied geometry-based material order");
        return sb.ToString();
    }

    // Auto-fix materials by identifying submeshes from their geometry
    public static string AutoFix()
    {
        var sb = new StringBuilder();

        SkinnedMeshRenderer smr = FindFaceMesh3SMR();
        if (smr == null) return "ERROR: FaceMesh3 SMR not found";

        var mesh = smr.sharedMesh;
        var verts = mesh.vertices;

        // Load all available materials
        var matFolder = "Assets/Models/Avatar/Materials/";
        var allMats = new Dictionary<string, Material>();
        var guids = AssetDatabase.FindAssets("t:Material", new[] { matFolder });
        foreach (var guid in guids)
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat != null) allMats[mat.name] = mat;
        }

        // Analyze each submesh
        var newMats = new Material[mesh.subMeshCount];
        for (int s = 0; s < mesh.subMeshCount; s++)
        {
            var tris = mesh.GetTriangles(s);
            if (tris.Length == 0) continue;

            Vector3 min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
            Vector3 max = new Vector3(float.MinValue, float.MinValue, float.MinValue);
            HashSet<int> uniqueVerts = new HashSet<int>();
            foreach (int idx in tris)
            {
                uniqueVerts.Add(idx);
                min = Vector3.Min(min, verts[idx]);
                max = Vector3.Max(max, verts[idx]);
            }

            Vector3 center = (min + max) * 0.5f;
            Vector3 size = max - min;
            int vertCount = uniqueVerts.Count;
            int triCount = tris.Length / 3;

            // Heuristic identification based on geometry
            string matName = IdentifySubmesh(center, size, vertCount, triCount);
            sb.AppendLine($"  [{s}] {vertCount} verts, {triCount} tris -> {matName}");

            if (allMats.ContainsKey(matName))
                newMats[s] = allMats[matName];
        }

        smr.sharedMaterials = newMats;
        EditorUtility.SetDirty(smr);
        sb.AppendLine("Applied auto-detected materials");

        return sb.ToString();
    }

    static string IdentifySubmesh(Vector3 center, Vector3 size, int verts, int tris)
    {
        // The face mesh is in local space. Identify parts by geometry characteristics:
        // - Face skin: largest submesh by far (most vertices)
        // - Teeth: inside mouth, smaller, typically below/behind face surface
        // - Eyes (L/R): small, roughly spherical, positioned symmetrically
        // - Eye shell: transparent overlay on eyes
        // - Lacrimal fluid: tiny, near inner eye corners
        // - Eyelashes: thin strips near eyes
        // - M_Hide: typically small hidden geometry

        // By vertex count (descending): skin >> eyelashes > teeth > eyes > hide > lacrimal
        if (verts > 5000) return "MI_Face_Skin_Baked_LOD1_VT";  // Largest = skin
        if (verts > 1000 && size.y < 0.02f) return "MI_Face_EyelashesHiLODs"; // Flat + many verts = eyelashes
        if (verts > 1000) return "MI_Teeth_Baked"; // Medium-large = teeth

        // Small submeshes: eyes, eye shell, lacrimal, hide
        // Eyes are roughly spherical and offset left/right from center
        if (verts > 200 && verts < 600)
        {
            if (center.x < -0.005f) return "MI_EyeL_Baked";  // Left of center
            if (center.x > 0.005f) return "MI_EyeR_Baked";   // Right of center
            return "MI_Face_EyeShell";  // Centered = shell overlay
        }

        // Very small
        if (verts < 100) return "MI_Face_LacrimalFluid";

        // Fallback for hide materials
        if (size.x < 0.01f && size.y < 0.01f) return "M_Hide";
        return "M_Hide_6";
    }

    static SkinnedMeshRenderer FindFaceMesh3SMR()
    {
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
        {
            if (go.name == "SKM_model4_FaceMesh3")
            {
                foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    if (smr.bones.Length > 800) return smr;
                }
            }
        }
        return null;
    }
}
