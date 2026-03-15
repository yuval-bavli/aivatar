using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.IO;

/// FixAllMaterials — applies eyelash thin texture, fixes hair color, adjusts eyebrow bake
public static class FixAllMaterials
{
    [MenuItem("Aivatar/Fix All Materials: Eyelashes + Hair + Eyebrows")]
    public static string Run()
    {
        string log = "";

        // 1. Fix eyelash material — use thin eyelash texture
        var lashTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/EyelashThin.png");
        if (lashTex == null)
        {
            // Trigger import first
            AssetDatabase.ImportAsset("Assets/Models/Avatar/Textures/EyelashThin.png");
            AssetDatabase.Refresh();
            lashTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/EyelashThin.png");
        }

        if (lashTex != null)
        {
            // Fix importer settings for alpha
            var lashImporter = AssetImporter.GetAtPath("Assets/Models/Avatar/Textures/EyelashThin.png") as TextureImporter;
            if (lashImporter != null)
            {
                lashImporter.sRGBTexture = true;
                lashImporter.alphaSource = TextureImporterAlphaSource.FromInput;
                lashImporter.alphaIsTransparency = true;
                lashImporter.maxTextureSize = 1024;
                lashImporter.textureCompression = TextureImporterCompression.Compressed;
                lashImporter.SaveAndReimport();
                lashTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/EyelashThin.png");
            }
        }

        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        if (lashMat != null && lashTex != null)
        {
            lashMat.SetTexture("_BaseMap", lashTex);
            lashMat.SetTexture("_MainTex", lashTex);
            lashMat.SetFloat("_Cutoff", 0.35f);  // lower cutoff to show the thin strands
            EditorUtility.SetDirty(lashMat);
            log += "Eyelash mat updated. ";
        }
        else log += $"WARNING: lashMat={lashMat != null}, lashTex={lashTex != null}. ";

        // 2. Fix hair color — dark brown (not pure black)
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            var brownColor = new Color(0.28f, 0.20f, 0.14f, 1f);
            hairMat.SetColor("_BaseColor", brownColor);
            hairMat.SetColor("_Color", brownColor);
            EditorUtility.SetDirty(hairMat);
            log += "Hair color set to dark brown. ";
        }

        // 3. Bake lighter eyebrows — reduce strength from 0.50 to 0.22
        log += BakeEyebrowsLight();

        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveOpenScenes();
        return log;
    }

    static string BakeEyebrowsLight()
    {
        string origPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT.PNG";
        var origTex = AssetDatabase.LoadAssetAtPath<Texture2D>(origPath);
        if (origTex == null) return "ERROR: head texture not found.";

        int w = origTex.width, h = origTex.height;
        float scale = (float)w / 8192f;

        var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
        Graphics.Blit(origTex, rt);
        var prev = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply();
        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        int rSX = Mathf.RoundToInt(698 * scale),  rSY = Mathf.RoundToInt(1455 * scale);
        int rEX = Mathf.RoundToInt(658 * scale),  rEY = Mathf.RoundToInt(1310 * scale);
        int rPY = Mathf.RoundToInt(1510 * scale);
        int lSX = Mathf.RoundToInt(1362 * scale), lSY = Mathf.RoundToInt(1455 * scale);
        int lEX = Mathf.RoundToInt(1402 * scale), lEY = Mathf.RoundToInt(1310 * scale);
        int lPY = Mathf.RoundToInt(1510 * scale);

        Color browColor = new Color(0.38f, 0.28f, 0.18f);
        float strength = 0.22f;  // lighter than before (was 0.50)
        float thickness = 4.0f;

        PaintBrowArc(tex, rSX, rSY, rEX, rEY, rPY, thickness, browColor, strength);
        PaintBrowArc(tex, lSX, lSY, lEX, lEY, lPY, thickness, browColor, strength);

        // Hair strokes
        var rng = new System.Random(42);
        Color hairColor = new Color(0.35f, 0.25f, 0.16f);
        for (int i = 0; i < 16; i++)
        {
            float t = (float)rng.NextDouble();
            int rx = (int)(Mathf.Lerp(rSX, rEX, t) + (rng.NextDouble() - 0.5) * 6 * scale);
            int ry = (int)(Mathf.Lerp(rSY, rEY, t) + (rng.NextDouble() - 0.5) * 4 * scale);
            PaintStroke(tex, rx, ry, Mathf.Max(1, (int)(3 * scale)), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.18f);
            int lx = (int)(Mathf.Lerp(lSX, lEX, t) + (rng.NextDouble() - 0.5) * 6 * scale);
            PaintStroke(tex, lx, ry, Mathf.Max(1, (int)(3 * scale)), (float)(rng.NextDouble() * 0.3 + 0.1), hairColor, 0.18f);
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

        return $"Eyebrows baked at strength=0.22 ({w}x{h}).";
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
