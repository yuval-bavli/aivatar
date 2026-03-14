using UnityEngine;
using UnityEditor;

public static class DebugEyebrowRed
{
    [MenuItem("Aivatar/Debug Eyebrow Red")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            // Solid red, no texture, no alpha test
            browMat.SetTexture("_BaseMap", null);
            browMat.SetTexture("_BumpMap", null);
            browMat.SetFloat("_AlphaClip", 0f);
            browMat.DisableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Surface", 0f); // Opaque
            browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f));
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.renderQueue = 2500; // High priority
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Set eyebrow to SOLID RED, no alpha");
        }

        // Also check: is there a MeshFilter with actual mesh assigned?
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == "Eyebrows_M_Natural_CardsMesh_Group0_LOD0")
            {
                log.AppendLine($"Eyebrow renderer: {r.GetType().Name}");
                log.AppendLine($"  enabled: {r.enabled}, GO active: {r.gameObject.activeInHierarchy}");
                log.AppendLine($"  bounds: center={r.bounds.center}, size={r.bounds.size}");
                log.AppendLine($"  material: {r.sharedMaterial?.name}");

                var mf = r.GetComponent<MeshFilter>();
                if (mf != null)
                {
                    log.AppendLine($"  meshFilter.mesh: {(mf.sharedMesh != null ? mf.sharedMesh.name : "NULL")}");
                    if (mf.sharedMesh != null)
                    {
                        log.AppendLine($"  mesh verts: {mf.sharedMesh.vertexCount}");
                        log.AppendLine($"  mesh tris: {mf.sharedMesh.triangles.Length / 3}");
                    }
                }
            }
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }
}
