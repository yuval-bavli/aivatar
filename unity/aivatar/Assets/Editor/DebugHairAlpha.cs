#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;

/// <summary>
/// Menu: Aivatar > Debug Hair Alpha
/// Samples the hair card texture to check if the alpha channel is valid.
/// </summary>
public static class DebugHairAlpha
{
    [MenuItem("Aivatar/Debug Hair Alpha")]
    private static void Run()
    {
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        if (tex == null) { Debug.LogError("HairCard0_Color_1K.png not found"); return; }

        if (!tex.isReadable)
        {
            Debug.LogError("Texture is not readable! Enable Read/Write in import settings.");
            return;
        }

        int w = tex.width, h = tex.height;
        Debug.Log($"[HairAlpha] Texture: {w}x{h}, format={tex.format}, hasAlpha={tex.format.ToString().Contains("Alpha") || tex.format == TextureFormat.RGBA32 || tex.format == TextureFormat.ARGB32 || tex.format == TextureFormat.DXT5 || tex.format == TextureFormat.RGBA4444}");

        // Sample pixels across the texture
        int transparent = 0, opaque = 0, semiTransparent = 0;
        int total = 0;

        for (int y = 0; y < h; y += 4)
        {
            for (int x = 0; x < w; x += 4)
            {
                Color c = tex.GetPixel(x, y);
                total++;
                if (c.a < 0.01f) transparent++;
                else if (c.a > 0.99f) opaque++;
                else semiTransparent++;
            }
        }

        Debug.Log($"[HairAlpha] Sampled {total} pixels (every 4th): " +
                  $"transparent(a<0.01)={transparent} ({100f*transparent/total:F1}%), " +
                  $"opaque(a>0.99)={opaque} ({100f*opaque/total:F1}%), " +
                  $"semi(between)={semiTransparent} ({100f*semiTransparent/total:F1}%)");

        // Sample some specific areas
        // Center of texture
        SampleArea(tex, "center", w/2, h/2);
        // Top-left corner (likely background)
        SampleArea(tex, "top-left(0,0)", 5, 5);
        // Various points
        SampleArea(tex, "quarter", w/4, h/4);
        SampleArea(tex, "3quarter", 3*w/4, 3*h/4);

        // Check if ALL pixels have alpha=1 (meaning no alpha channel data)
        if (transparent == 0 && semiTransparent == 0)
        {
            Debug.LogWarning("[HairAlpha] ALL pixels are fully opaque! The PNG has no meaningful alpha channel. " +
                             "This means alpha cutout won't work - you need to generate alpha from the color data.");
        }

        // Also check the actual pixel format
        var pixels = tex.GetPixels(0, 0, Mathf.Min(10, w), Mathf.Min(10, h));
        Debug.Log($"[HairAlpha] First 10x10 corner alpha values: " +
                  $"min={MinAlpha(pixels):F3}, max={MaxAlpha(pixels):F3}, avg={AvgAlpha(pixels):F3}");
    }

    private static void SampleArea(Texture2D tex, string label, int cx, int cy)
    {
        Color c = tex.GetPixel(cx, cy);
        Debug.Log($"[HairAlpha] {label} ({cx},{cy}): RGBA=({c.r:F3}, {c.g:F3}, {c.b:F3}, {c.a:F3})");
    }

    private static float MinAlpha(Color[] pixels)
    {
        float min = 1f;
        foreach (var c in pixels) if (c.a < min) min = c.a;
        return min;
    }

    private static float MaxAlpha(Color[] pixels)
    {
        float max = 0f;
        foreach (var c in pixels) if (c.a > max) max = c.a;
        return max;
    }

    private static float AvgAlpha(Color[] pixels)
    {
        float sum = 0f;
        foreach (var c in pixels) sum += c.a;
        return sum / pixels.Length;
    }
}
#endif
