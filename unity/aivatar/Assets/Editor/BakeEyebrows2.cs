using UnityEngine;
using UnityEditor;
using System.IO;
using System.Collections.Generic;

public static class BakeEyebrows2
{
    [MenuItem("Aivatar/Bake Eyebrows 2")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Find face mesh
        MeshFilter faceMF = null;
        Renderer faceRenderer = null;
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == "SKM_model4_FaceMesh" && r is MeshRenderer)
            {
                faceRenderer = r;
                faceMF = r.GetComponent<MeshFilter>();
                break;
            }
        }
        if (faceMF == null) return "ERROR: no face mesh";

        var mesh = faceMF.sharedMesh;
        var verts = mesh.vertices;
        var uvs = mesh.uv;
        var tris = mesh.GetTriangles(0);
        var xform = faceRenderer.transform;

        // Build set of submesh 0 vertex indices
        HashSet<int> sm0 = new HashSet<int>();
        foreach (int i in tris) sm0.Add(i);

        // Narrow eyebrow region: just above eyes, separated left/right
        // Face center X ≈ 0.03
        float browMinY = 1.56f, browMaxY = 1.62f;
        float browMinZ = -8.78f, browMaxZ = -8.70f;

        List<Vector2> leftBrowUVs = new List<Vector2>();
        List<Vector2> rightBrowUVs = new List<Vector2>();
        List<Vector2> centerBrowUVs = new List<Vector2>();

        for (int i = 0; i < verts.Length; i++)
        {
            if (!sm0.Contains(i)) continue;
            Vector3 wp = xform.TransformPoint(verts[i]);
            if (wp.y < browMinY || wp.y > browMaxY) continue;
            if (wp.z < browMinZ || wp.z > browMaxZ) continue;

            if (wp.x < -0.02f)
                rightBrowUVs.Add(uvs[i]); // Right side of face (viewer's left)
            else if (wp.x > 0.08f)
                leftBrowUVs.Add(uvs[i]); // Left side of face (viewer's right)
            else
                centerBrowUVs.Add(uvs[i]);
        }

        log.AppendLine($"Left brow verts: {leftBrowUVs.Count}");
        log.AppendLine($"Right brow verts: {rightBrowUVs.Count}");
        log.AppendLine($"Center brow verts: {centerBrowUVs.Count}");

        LogUVRange("Left brow", leftBrowUVs, log);
        LogUVRange("Right brow", rightBrowUVs, log);
        LogUVRange("Center brow", centerBrowUVs, log);

        // Now bake eyebrows onto face texture
        var faceMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        if (faceMat == null) return "ERROR: no face material";

        var origTex = faceMat.GetTexture("_BaseMap") as Texture2D;
        if (origTex == null) return "ERROR: no face texture";

        // Make readable copy
        var rt = RenderTexture.GetTemporary(origTex.width, origTex.height, 0, RenderTextureFormat.ARGB32);
        Graphics.Blit(origTex, rt);
        var prev = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(origTex.width, origTex.height, TextureFormat.RGBA32, false);
        tex.ReadPixels(new Rect(0, 0, origTex.width, origTex.height), 0, 0);
        tex.Apply();
        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        int w = tex.width, h = tex.height;
        log.AppendLine($"\nTexture: {w}x{h}");

        // Paint eyebrows using collected UV coordinates
        // For each brow region, paint a soft dark stroke
        Color browColor = new Color(0.25f, 0.18f, 0.14f, 1f); // Dark brown

        // Paint strokes at each UV point with a small radius
        int painted = 0;
        float radius = 3f; // pixels

        foreach (var uv in leftBrowUVs)
        {
            painted += PaintDot(tex, uv, browColor, radius, 0.4f);
        }
        foreach (var uv in rightBrowUVs)
        {
            painted += PaintDot(tex, uv, browColor, radius, 0.4f);
        }
        foreach (var uv in centerBrowUVs)
        {
            painted += PaintDot(tex, uv, browColor, radius, 0.2f); // Lighter at center
        }

        log.AppendLine($"Painted {painted} pixels");

        // Save the modified texture
        tex.Apply();
        string outPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png";
        byte[] bytes = tex.EncodeToPNG();
        File.WriteAllBytes(Path.Combine(Application.dataPath, "..", outPath), bytes);
        Object.DestroyImmediate(tex);
        AssetDatabase.Refresh();

        // Set import settings
        var importer = AssetImporter.GetAtPath(outPath) as TextureImporter;
        if (importer != null)
        {
            importer.sRGBTexture = true;
            importer.maxTextureSize = 2048;
            importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        // Assign to face material
        var newTex = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        if (newTex != null)
        {
            faceMat.SetTexture("_BaseMap", newTex);
            EditorUtility.SetDirty(faceMat);
            log.AppendLine($"Assigned baked texture to face material");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static int PaintDot(Texture2D tex, Vector2 uv, Color color, float radius, float strength)
    {
        int px = Mathf.RoundToInt(uv.x * tex.width);
        int py = Mathf.RoundToInt(uv.y * tex.height);
        int r = Mathf.CeilToInt(radius);
        int count = 0;

        for (int dy = -r; dy <= r; dy++)
        {
            for (int dx = -r; dx <= r; dx++)
            {
                int x = px + dx;
                int y = py + dy;
                if (x < 0 || x >= tex.width || y < 0 || y >= tex.height) continue;

                float dist = Mathf.Sqrt(dx * dx + dy * dy);
                if (dist > radius) continue;

                float falloff = 1f - (dist / radius);
                float alpha = strength * falloff;

                Color existing = tex.GetPixel(x, y);
                Color blended = Color.Lerp(existing, color, alpha);
                tex.SetPixel(x, y, blended);
                count++;
            }
        }
        return count;
    }

    static void LogUVRange(string name, List<Vector2> uvs, System.Text.StringBuilder log)
    {
        if (uvs.Count == 0) { log.AppendLine($"  {name}: empty"); return; }
        Vector2 min = uvs[0], max = uvs[0];
        foreach (var uv in uvs) { min = Vector2.Min(min, uv); max = Vector2.Max(max, uv); }
        log.AppendLine($"  {name}: UV range ({min.x:F3},{min.y:F3})-({max.x:F3},{max.y:F3})");
        // In pixels (2048x2048)
        log.AppendLine($"    Pixels: ({min.x * 2048:F0},{min.y * 2048:F0})-({max.x * 2048:F0},{max.y * 2048:F0})");
    }
}
