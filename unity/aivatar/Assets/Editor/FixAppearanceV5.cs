using UnityEngine;
using UnityEditor;
using System.IO;

public static class FixAppearanceV5
{
    [MenuItem("Aivatar/Fix Appearance V5")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // ============================================================
        // 1. Debug: Sample hair card texture in eyebrow UV range (0,0.5)-(0.75,1.0)
        // ============================================================
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        if (hairTex != null)
        {
            var rt = RenderTexture.GetTemporary(hairTex.width, hairTex.height, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(hairTex, rt);
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var readable = new Texture2D(hairTex.width, hairTex.height, TextureFormat.RGBA32, false);
            readable.ReadPixels(new Rect(0, 0, hairTex.width, hairTex.height), 0, 0);
            readable.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);

            // Eyebrow UV range: x=0..0.75, y=0.5..1.0
            // In pixel space (1024): x=0..768, y=512..1024
            log.AppendLine("=== Hair texture in eyebrow UV range (y=512..1024) ===");
            int alphaZero = 0, alphaPartial = 0, alphaFull = 0;
            for (int y = 512; y < 1024; y += 8)
            {
                for (int x = 0; x < 768; x += 8)
                {
                    var c = readable.GetPixel(x, y);
                    if (c.a < 0.01f) alphaZero++;
                    else if (c.a > 0.99f) alphaFull++;
                    else alphaPartial++;
                }
            }
            log.AppendLine($"Alpha distribution: zero={alphaZero}, partial={alphaPartial}, full={alphaFull}");
            int total = alphaZero + alphaPartial + alphaFull;
            log.AppendLine($"Coverage: {(alphaPartial + alphaFull) * 100f / total:F1}% has some alpha");

            // Sample some rows
            log.AppendLine("Sampling specific pixels in eyebrow UV region:");
            for (int y = 512; y <= 1024; y += 64)
            {
                int nonzero = 0;
                for (int x = 0; x < 768; x += 4)
                {
                    if (readable.GetPixel(x, y).a > 0.03f) nonzero++;
                }
                log.AppendLine($"  Row y={y}: {nonzero}/{768/4} pixels with alpha > 0.03");
            }

            Object.DestroyImmediate(readable);
        }

        // ============================================================
        // 2. Try rendering eyebrows WITHOUT alpha clipping to see full shape
        // ============================================================
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        if (browMat != null)
        {
            // TEMPORARILY: Render fully opaque to see the geometry shape
            browMat.SetFloat("_AlphaClip", 0f);
            browMat.DisableKeyword("_ALPHATEST_ON");
            browMat.SetFloat("_Surface", 0f); // Opaque
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.renderQueue = 2001; // Just after face skin to render on top
            browMat.SetFloat("_Cull", 0f); // Double-sided
            EditorUtility.SetDirty(browMat);
            log.AppendLine("DEBUG: Eyebrows set to fully opaque (no alpha test) for shape debugging");
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
        string path = Path.Combine(Application.dataPath, "..", "fixv5_result.txt");
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
