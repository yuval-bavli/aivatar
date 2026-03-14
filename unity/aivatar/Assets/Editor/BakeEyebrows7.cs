using UnityEngine;
using UnityEditor;
using System.IO;

/// BakeEyebrows7 — even lighter/thinner per qwen3-vl:8b audit:
///   - colour:    (0.42, 0.32, 0.22)  was (0.35, 0.25, 0.17)
///   - strength:  0.16                 was 0.28
///   - thickness: 4px                  was 6px
///   - passes:    1                    was 2
public static class BakeEyebrows7
{
    [MenuItem("Aivatar/Bake Eyebrows 7 (ultra-light)")]
    public static string Run()
    {
        string origPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT.PNG";
        var origTex = AssetDatabase.LoadAssetAtPath<Texture2D>(origPath);
        if (origTex == null) return "ERROR: texture not found";

        var rt = RenderTexture.GetTemporary(origTex.width, origTex.height, 0, RenderTextureFormat.ARGB32);
        Graphics.Blit(origTex, rt);
        var prev = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(origTex.width, origTex.height, TextureFormat.RGBA32, false);
        tex.ReadPixels(new Rect(0, 0, origTex.width, origTex.height), 0, 0);
        tex.Apply();
        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        Color browColor = new Color(0.42f, 0.32f, 0.22f);

        PaintBrowArc(tex, 698, 1455, 658, 1310, 1510, 4f, browColor, 0.16f);
        PaintBrowArc(tex, 1362, 1455, 1402, 1310, 1510, 4f, browColor, 0.16f);

        // Very minimal hair strokes
        var rng = new System.Random(42);
        Color hairColor = new Color(0.38f, 0.28f, 0.20f);
        for (int i = 0; i < 12; i++)
        {
            float t  = (float)rng.NextDouble();
            float rx = Mathf.Lerp(698, 658, t) + (float)(rng.NextDouble() - 0.5) * 6;
            float ry = Mathf.Lerp(1455, 1310, t);
            float peak = t < 0.5f ? Mathf.Lerp(1455, 1510, t * 2f) : Mathf.Lerp(1510, 1310, (t - 0.5f) * 2f);
            ry = ry + (peak - ry) * 0.3f + (float)(rng.NextDouble() - 0.5) * 8;
            PaintStroke(tex, (int)rx, (int)ry, 2 + rng.Next(3), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.14f);
            float lx = Mathf.Lerp(1362, 1402, t) + (float)(rng.NextDouble() - 0.5) * 6;
            PaintStroke(tex, (int)lx, (int)ry, 2 + rng.Next(3), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.14f);
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

        return "BakeEyebrows7: ultra-light arcs painted";
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
