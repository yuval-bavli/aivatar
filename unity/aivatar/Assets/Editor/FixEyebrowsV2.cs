using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.IO;

/// FixEyebrowsV2 — disables eyebrow mesh (saves scene) + bakes at correct 2048 pixel sizes
public static class FixEyebrowsV2
{
    [MenuItem("Aivatar/Fix Eyebrows V2: Disable Mesh + Correct Bake")]
    public static string Run()
    {
        // 1. Disable the eyebrow mesh renderer and save scene
        int disabled = 0;
        foreach (var r in GameObject.FindObjectsOfType<MeshRenderer>(true))
        {
            if (r.gameObject.name.Contains("Eyebrows_M_Natural"))
            {
                r.enabled = false;
                EditorUtility.SetDirty(r);
                disabled++;
            }
        }
        foreach (var r in GameObject.FindObjectsOfType<SkinnedMeshRenderer>(true))
        {
            if (r.gameObject.name.Contains("Eyebrows_M_Natural"))
            {
                r.enabled = false;
                EditorUtility.SetDirty(r);
                disabled++;
            }
        }
        EditorSceneManager.SaveOpenScenes();

        // 2. Bake eyebrow arcs with absolute pixel sizes suitable for 2048 texture
        string origPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT.PNG";
        var origTex = AssetDatabase.LoadAssetAtPath<Texture2D>(origPath);
        if (origTex == null) return $"ERROR: texture not found (disabled {disabled} renderers, scene saved)";

        int w = origTex.width, h = origTex.height;
        float scale = (float)w / 8192f;  // e.g. 0.25 for 2048

        var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
        Graphics.Blit(origTex, rt);
        var prev = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        // Coordinates scaled to actual texture resolution
        int rSX = Mathf.RoundToInt(698  * scale), rSY = Mathf.RoundToInt(1455 * scale);
        int rEX = Mathf.RoundToInt(658  * scale), rEY = Mathf.RoundToInt(1310 * scale);
        int rPY = Mathf.RoundToInt(1510 * scale);
        int lSX = Mathf.RoundToInt(1362 * scale), lSY = Mathf.RoundToInt(1455 * scale);
        int lEX = Mathf.RoundToInt(1402 * scale), lEY = Mathf.RoundToInt(1310 * scale);
        int lPY = Mathf.RoundToInt(1510 * scale);

        Color browColor = new Color(0.40f, 0.30f, 0.20f);
        // Use absolute pixel thickness appropriate for the actual resolution
        // At 2048: eyebrow width should be ~6px, at 8192 that would be 24px
        float thickness = Mathf.Max(4f, 4f * scale * 4f);  // ~4px at any resolution
        float strength = 0.50f;

        PaintBrowArc(tex, rSX, rSY, rEX, rEY, rPY, thickness, browColor, strength);
        PaintBrowArc(tex, lSX, lSY, lEX, lEY, lPY, thickness, browColor, strength);

        // Hair strokes
        var rng = new System.Random(42);
        Color hairColor = new Color(0.35f, 0.25f, 0.18f);
        for (int i = 0; i < 16; i++)
        {
            float t = (float)rng.NextDouble();
            int rx = (int)(Mathf.Lerp(rSX, rEX, t) + (rng.NextDouble() - 0.5) * 6 * scale);
            int ry = (int)(Mathf.Lerp(rSY, rEY, t) + (rng.NextDouble() - 0.5) * 4 * scale);
            PaintStroke(tex, rx, ry, Mathf.Max(1, (int)(3 * scale)), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.30f);
            int lx = (int)(Mathf.Lerp(lSX, lEX, t) + (rng.NextDouble() - 0.5) * 6 * scale);
            PaintStroke(tex, lx, ry, Mathf.Max(1, (int)(3 * scale)), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.30f);
        }

        tex.Apply();
        string outPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png";
        File.WriteAllBytes(Path.Combine(Application.dataPath, "..", outPath), tex.EncodeToPNG());
        Object.DestroyImmediate(tex);
        AssetDatabase.Refresh();

        var importer = AssetImporter.GetAtPath(outPath) as TextureImporter;
        if (importer != null) { importer.sRGBTexture = true; importer.maxTextureSize = 2048; importer.textureCompression = TextureImporterCompression.Compressed; importer.SaveAndReimport(); }

        var faceMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        var newTex  = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        if (faceMat != null && newTex != null) { faceMat.SetTexture("_BaseMap", newTex); EditorUtility.SetDirty(faceMat); }
        AssetDatabase.SaveAssets();

        return $"FixEyebrowsV2: disabled {disabled} renderers, scene saved, baked at {w}x{h} thickness={thickness:F1}px";
    }

    static void PaintBrowArc(Texture2D tex, int startX, int startY, int endX, int endY, int peakY, float thickness, Color color, float strength)
    {
        for (int i = 0; i <= 80; i++)
        {
            float t = (float)i / 80;
            float midX = (startX + endX) * 0.5f;
            float x = Mathf.Lerp(Mathf.Lerp(startX, midX, t), Mathf.Lerp(midX, endX, t), t);
            float y = Mathf.Lerp(Mathf.Lerp(startY, peakY, t), Mathf.Lerp(peakY, endY, t), t);
            float r = thickness * Mathf.Max(1f - 0.4f * Mathf.Abs(t - 0.35f) / 0.65f, 0.3f);
            int ir = Mathf.CeilToInt(r);
            for (int dy = -ir; dy <= ir; dy++)
            for (int dx = -ir; dx <= ir; dx++)
            {
                int px = Mathf.RoundToInt(x) + dx, py = Mathf.RoundToInt(y) + dy;
                if (px < 0 || px >= tex.width || py < 0 || py >= tex.height) continue;
                float dist = Mathf.Sqrt(dx * dx + dy * dy);
                if (dist > r) continue;
                float falloff = (1f - dist / r); falloff *= falloff;
                tex.SetPixel(px, py, Color.Lerp(tex.GetPixel(px, py), color, strength * falloff));
            }
        }
    }

    static void PaintStroke(Texture2D tex, int cx, int cy, int length, float angle, Color color, float strength)
    {
        for (int i = -length; i <= length; i++)
        {
            int px = cx + Mathf.RoundToInt(Mathf.Cos(angle) * i);
            int py = cy + Mathf.RoundToInt(Mathf.Sin(angle) * i);
            if (px < 0 || px >= tex.width || py < 0 || py >= tex.height) continue;
            tex.SetPixel(px, py, Color.Lerp(tex.GetPixel(px, py), color, strength * 0.7f));
        }
    }
}
