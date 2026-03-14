using UnityEngine;
using UnityEditor;
using System.IO;

public static class BakeEyebrows3
{
    [MenuItem("Aivatar/Bake Eyebrows 3")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Load original face texture (not the baked one)
        string origPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT.PNG";
        var origTex = AssetDatabase.LoadAssetAtPath<Texture2D>(origPath);
        if (origTex == null) return "ERROR: original texture not found";

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

        int w = tex.width, h = tex.height; // 2048x2048
        log.AppendLine($"Texture: {w}x{h}");

        // From mesh analysis:
        // Right brow (viewer's left): UV (0.319-0.360, 0.631-0.748) → pixels (654-737, 1291-1532)
        // Left brow (viewer's right): UV (0.648-0.699, 0.632-0.776) → pixels (1328-1431, 1295-1589)

        // Paint eyebrow arcs - multiple strokes with varying thickness
        Color browColor = new Color(0.22f, 0.16f, 0.12f);

        // Right eyebrow (viewer's left side of face)
        // Arc from inner corner to outer corner
        PaintBrowArc(tex,
            startX: 695, startY: 1450,   // Inner corner (near nose)
            endX: 660, endY: 1320,       // Outer corner
            peakY: 1500,                  // Arc peak height
            thickness: 8f,
            color: browColor,
            strength: 0.65f);

        // Additional strokes for fuller brow
        PaintBrowArc(tex,
            startX: 695, startY: 1440,
            endX: 665, endY: 1330,
            peakY: 1485,
            thickness: 6f,
            color: browColor,
            strength: 0.5f);

        // Left eyebrow (viewer's right side of face)
        PaintBrowArc(tex,
            startX: 1365, startY: 1450,  // Inner corner
            endX: 1400, endY: 1320,      // Outer corner
            peakY: 1500,
            thickness: 8f,
            color: browColor,
            strength: 0.65f);

        PaintBrowArc(tex,
            startX: 1365, startY: 1440,
            endX: 1395, endY: 1330,
            peakY: 1485,
            thickness: 6f,
            color: browColor,
            strength: 0.5f);

        log.AppendLine("Painted eyebrow arcs");

        // Save
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
        var faceMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        var newTex = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        if (faceMat != null && newTex != null)
        {
            faceMat.SetTexture("_BaseMap", newTex);
            EditorUtility.SetDirty(faceMat);
            log.AppendLine("Assigned to face material");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static void PaintBrowArc(Texture2D tex, int startX, int startY, int endX, int endY,
                              int peakY, float thickness, Color color, float strength)
    {
        // Paint a curved arc from start to end with a peak
        int steps = 60;
        for (int i = 0; i <= steps; i++)
        {
            float t = (float)i / steps;

            // Quadratic bezier: start → peak → end
            float midX = (startX + endX) * 0.5f;
            float x = Mathf.Lerp(Mathf.Lerp(startX, midX, t), Mathf.Lerp(midX, endX, t), t);
            float y = Mathf.Lerp(Mathf.Lerp(startY, peakY, t), Mathf.Lerp(peakY, endY, t), t);

            // Thickness varies - thicker in middle, thinner at ends
            float thickMult = 1f - 0.5f * Mathf.Abs(t - 0.4f) / 0.6f;
            float r = thickness * thickMult;

            // Paint a filled circle at this point
            int ir = Mathf.CeilToInt(r);
            for (int dy = -ir; dy <= ir; dy++)
            {
                for (int dx = -ir; dx <= ir; dx++)
                {
                    int px = Mathf.RoundToInt(x) + dx;
                    int py = Mathf.RoundToInt(y) + dy;
                    if (px < 0 || px >= tex.width || py < 0 || py >= tex.height) continue;

                    float dist = Mathf.Sqrt(dx * dx + dy * dy);
                    if (dist > r) continue;

                    float falloff = 1f - (dist / r);
                    falloff = falloff * falloff; // Soft edges
                    float alpha = strength * falloff;

                    Color existing = tex.GetPixel(px, py);
                    Color blended = Color.Lerp(existing, color, alpha);
                    tex.SetPixel(px, py, blended);
                }
            }
        }
    }
}
