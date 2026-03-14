using UnityEngine;
using UnityEditor;
using System.IO;

/// BakeEyebrows5 — lighter, thinner eyebrows per vision-model audit feedback:
///   - colour lightened: (0.28, 0.20, 0.14)  was (0.20, 0.14, 0.10)
///   - max strength:  0.45   was 0.70
///   - thickness:     8px    was 12px
///   - passes:        3      was 5
public static class BakeEyebrows5
{
    [MenuItem("Aivatar/Bake Eyebrows 5 (lighter+thinner)")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

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

        Color browColor = new Color(0.28f, 0.20f, 0.14f);  // lighter than v4

        // Right eyebrow (viewer's left)
        for (int pass = 0; pass < 3; pass++)
        {
            float yOff = pass * 3f - 3f;
            float str  = 0.45f - pass * 0.07f;
            PaintBrowArc(tex,
                startX: 698, startY: (int)(1455 + yOff),
                endX:   658, endY:   (int)(1310 + yOff),
                peakY:  (int)(1510 + yOff),
                thickness: 8f,
                color: browColor,
                strength: str);
        }

        // Left eyebrow (viewer's right)
        for (int pass = 0; pass < 3; pass++)
        {
            float yOff = pass * 3f - 3f;
            float str  = 0.45f - pass * 0.07f;
            PaintBrowArc(tex,
                startX: 1362, startY: (int)(1455 + yOff),
                endX:   1402, endY:   (int)(1310 + yOff),
                peakY:  (int)(1510 + yOff),
                thickness: 8f,
                color: browColor,
                strength: str);
        }

        // Light individual hair-like strokes
        var rng = new System.Random(42);
        Color hairColor = new Color(0.25f, 0.18f, 0.12f);
        for (int i = 0; i < 30; i++)
        {
            float t = (float)rng.NextDouble();
            float rx = Mathf.Lerp(698, 658, t) + (float)(rng.NextDouble() - 0.5) * 10;
            float ry = Mathf.Lerp(1455, 1310, t);
            float peak = Mathf.Lerp(1455, 1510, Mathf.Clamp01(t * 2f));
            if (t > 0.5f) peak = Mathf.Lerp(1510, 1310, (t - 0.5f) * 2f);
            ry = ry + (peak - ry) * 0.3f + (float)(rng.NextDouble() - 0.5) * 12;
            PaintStroke(tex, (int)rx, (int)ry, 4 + rng.Next(5), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.35f);

            float lx = Mathf.Lerp(1362, 1402, t) + (float)(rng.NextDouble() - 0.5) * 10;
            PaintStroke(tex, (int)lx, (int)ry, 4 + rng.Next(5), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.35f);
        }

        log.AppendLine("Painted lighter/thinner eyebrow arcs (v5)");

        tex.Apply();
        string outPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png";
        byte[] bytes = tex.EncodeToPNG();
        File.WriteAllBytes(Path.Combine(Application.dataPath, "..", outPath), bytes);
        Object.DestroyImmediate(tex);
        AssetDatabase.Refresh();

        var importer = AssetImporter.GetAtPath(outPath) as TextureImporter;
        if (importer != null)
        {
            importer.sRGBTexture = true;
            importer.maxTextureSize = 2048;
            importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        var faceMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        var newTex = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        if (faceMat != null && newTex != null)
        {
            faceMat.SetTexture("_BaseMap", newTex);
            EditorUtility.SetDirty(faceMat);
        }

        AssetDatabase.SaveAssets();
        return log.ToString();
    }

    static void PaintBrowArc(Texture2D tex, int startX, int startY, int endX, int endY,
                              int peakY, float thickness, Color color, float strength)
    {
        int steps = 80;
        for (int i = 0; i <= steps; i++)
        {
            float t  = (float)i / steps;
            float midX = (startX + endX) * 0.5f;
            float x  = Mathf.Lerp(Mathf.Lerp(startX, midX, t), Mathf.Lerp(midX, endX, t), t);
            float y  = Mathf.Lerp(Mathf.Lerp(startY, peakY, t), Mathf.Lerp(peakY, endY, t), t);

            float thickMult = 1f - 0.4f * Mathf.Abs(t - 0.35f) / 0.65f;
            float r = thickness * Mathf.Max(thickMult, 0.3f);

            int ir = Mathf.CeilToInt(r);
            for (int dy = -ir; dy <= ir; dy++)
            for (int dx = -ir; dx <= ir; dx++)
            {
                int px = Mathf.RoundToInt(x) + dx;
                int py = Mathf.RoundToInt(y) + dy;
                if (px < 0 || px >= tex.width || py < 0 || py >= tex.height) continue;
                float dist = Mathf.Sqrt(dx * dx + dy * dy);
                if (dist > r) continue;
                float falloff = 1f - (dist / r);
                falloff *= falloff;
                Color existing = tex.GetPixel(px, py);
                tex.SetPixel(px, py, Color.Lerp(existing, color, strength * falloff));
            }
        }
    }

    static void PaintStroke(Texture2D tex, int cx, int cy, int length, float angle, Color color, float strength)
    {
        float dx = Mathf.Cos(angle);
        float dy = Mathf.Sin(angle);
        for (int i = -length; i <= length; i++)
        {
            int px = cx + Mathf.RoundToInt(dx * i);
            int py = cy + Mathf.RoundToInt(dy * i);
            if (px < 0 || px >= tex.width || py < 0 || py >= tex.height) continue;
            Color existing = tex.GetPixel(px, py);
            tex.SetPixel(px, py, Color.Lerp(existing, color, strength * 0.7f));
        }
    }
}
