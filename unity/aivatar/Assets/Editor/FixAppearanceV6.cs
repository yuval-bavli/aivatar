using UnityEngine;
using UnityEditor;
using System.IO;

public static class FixAppearanceV6
{
    [MenuItem("Aivatar/Fix Appearance V6")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. EYEBROWS: Fix z-fighting by using depth offset and pushing geometry out
        // ============================================================
        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO != null)
        {
            var browRenderer = browGO.GetComponent<MeshRenderer>();
            var mf = browGO.GetComponent<MeshFilter>();

            // Log parent chain to understand positioning
            var t = browGO.transform;
            log.AppendLine("Eyebrow transform chain:");
            while (t != null)
            {
                log.AppendLine($"  {t.name}: pos={t.localPosition}, rot={t.localEulerAngles}, scale={t.localScale}");
                t = t.parent;
            }

            // Move the eyebrow mesh slightly forward (towards camera) to avoid z-fighting
            // Face is roughly on -Z axis, so pushing eyebrows in -Z direction (toward camera)
            // or more precisely, in the face normal direction
            // World bounds center: (-0.01, 2.35, -8.75)
            // A tiny offset should fix z-fighting
            var pos = browGO.transform.localPosition;
            log.AppendLine($"Eyebrow local pos before: {pos}");

            // Check the mesh normals to determine face-outward direction
            if (mf != null && mf.sharedMesh != null)
            {
                var normals = mf.sharedMesh.normals;
                if (normals.Length > 0)
                {
                    Vector3 avgNormal = Vector3.zero;
                    for (int i = 0; i < normals.Length; i++)
                        avgNormal += normals[i];
                    avgNormal /= normals.Length;
                    avgNormal = browGO.transform.TransformDirection(avgNormal.normalized);
                    log.AppendLine($"Avg world normal: {avgNormal}");
                }
            }
        }

        // ============================================================
        // 2. EYEBROWS: Try material-level depth bias approach
        // ============================================================
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            // Re-enable alpha clipping but with proper depth settings
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Cutoff", 0.03f);
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.SetFloat("_Smoothness", 0.1f);
            browMat.SetFloat("_Cull", 0f); // Double-sided

            // Use high render queue to render after face
            browMat.renderQueue = 2452;

            // Try adding depth bias via shader global offset
            // URP Lit doesn't have built-in offset, but we can use _ZTest
            // Set ZTest to LessEqual (default) - should be fine
            browMat.SetFloat("_ZWrite", 1f);

            EditorUtility.SetDirty(browMat);
            log.AppendLine("Eyebrow material updated with alpha clip re-enabled");
        }

        // ============================================================
        // 3. Physically offset eyebrow mesh forward
        // ============================================================
        if (browGO != null)
        {
            // Push eyebrows slightly outward from face
            // The face normal at the brow area is roughly (0, 0.3, -0.95) in world space
            // A small offset in -Z (towards camera) should work
            var pos = browGO.transform.localPosition;
            // Add a tiny forward offset - the mesh is in local space of the face hierarchy
            // Try adding offset in the mesh's local Z (face-outward direction)
            browGO.transform.localPosition = new Vector3(pos.x, pos.y, pos.z + 0.3f);
            EditorUtility.SetDirty(browGO);
            log.AppendLine($"Eyebrow local pos after: {browGO.transform.localPosition}");
            log.AppendLine($"Eyebrow world pos after: {browGO.transform.position}");
            log.AppendLine($"Eyebrow world bounds after: center={browGO.GetComponent<Renderer>().bounds.center}, size={browGO.GetComponent<Renderer>().bounds.size}");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        string path = Path.Combine(Application.dataPath, "..", "fixv6_result.txt");
        File.WriteAllText(path, result);
        Debug.Log(result);
        return result;
    }

    static GameObject FindByName(string name)
    {
        foreach (var go in Object.FindObjectsOfType<GameObject>())
        {
            if (go.name == name) return go;
        }
        return null;
    }
}
