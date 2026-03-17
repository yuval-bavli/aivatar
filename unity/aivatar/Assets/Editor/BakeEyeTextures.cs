using UnityEngine;
using UnityEditor;
using System.IO;

public class BakeEyeTextures
{
    static readonly string TexturePath = "Assets/Models/Avatar/Textures/";
    static readonly string MaterialPath = "Assets/Models/Avatar/Materials/";
    static readonly string OutputPath = "Assets/Models/Avatar/Textures/";

    // Gentle brightness boost — original UE texture is dark but has good detail
    static readonly float IrisBrightness = 1.8f;
    // Subtle gray-blue-green tint matching MetaHuman reference
    static readonly Color IrisTint = new Color(0.55f, 0.62f, 0.72f, 1f);
    // Threshold: how different a pixel must be from the background to count as "iris"
    static readonly float MaskThreshold = 0.03f;
    // How many edge pixels to sample for background detection
    static readonly int EdgeSamples = 20;
    // Pixels darker than this are treated as pupil
    static readonly float PupilThreshold = 0.04f;
    // How much to shrink the pupil (in UV space, 0.5 = center)
    // Pupil pixels within this distance of the iris boundary get replaced with iris color
    static readonly float PupilShrinkRadius = 0.06f;

    [MenuItem("Aivatar/Bake Eye Textures")]
    public static string Bake()
    {
        BakeEye(
            "T_EyeScleraR_BC", "T_EyeIrisR_BC",
            "T_EyeScleraR_N", "T_EyeIrisR_N",
            "MI_EyeR_Baked",
            "BakedEyeR_BC", "BakedEyeR_N"
        );
        BakeEye(
            "T_EyeScleraL_BC", "T_EyeIrisL_BC",
            "T_EyeScleraL_N", "T_EyeIrisL_N",
            "MI_EyeL_Baked",
            "BakedEyeL_BC", "BakedEyeL_N"
        );

        SetupEyeShell();

        AssetDatabase.Refresh();
        string msg = "Eye textures baked and materials assigned!";
        Debug.Log(msg);
        return msg;
    }

    static void BakeEye(
        string scleraName, string irisName,
        string scleraNormalName, string irisNormalName,
        string materialName,
        string outputColorName, string outputNormalName)
    {
        var sclera = LoadReadable(TexturePath + scleraName + ".PNG");
        var iris = LoadReadable(TexturePath + irisName + ".PNG");
        var scleraN = LoadReadable(TexturePath + scleraNormalName + ".PNG");
        var irisN = LoadReadable(TexturePath + irisNormalName + ".PNG");

        if (sclera == null || iris == null)
        {
            Debug.LogError($"Failed to load textures for {materialName}");
            return;
        }

        float[] mask = BuildContentMask(iris);
        iris = ShrinkPupil(iris);

        var bakedColor = CompositeWithMask(sclera, iris, mask, true);
        SaveTexture(bakedColor, OutputPath + outputColorName + ".png");

        if (scleraN != null && irisN != null)
        {
            float[] maskN = BuildContentMask(irisN);
            var bakedNormal = CompositeWithMask(scleraN, irisN, maskN, false);
            SaveTexture(bakedNormal, OutputPath + outputNormalName + ".png");
        }

        AssetDatabase.Refresh();

        var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath + materialName + ".mat");
        if (mat == null)
        {
            Debug.LogError($"Material not found: {materialName}");
            return;
        }

        var colorTex = AssetDatabase.LoadAssetAtPath<Texture2D>(OutputPath + outputColorName + ".png");
        if (colorTex != null)
        {
            mat.SetTexture("_BaseMap", colorTex);
            mat.SetTexture("_MainTex", colorTex);
        }

        var normalTex = AssetDatabase.LoadAssetAtPath<Texture2D>(OutputPath + outputNormalName + ".png");
        if (normalTex != null)
        {
            string normalPath = OutputPath + outputNormalName + ".png";
            var importer = AssetImporter.GetAtPath(normalPath) as TextureImporter;
            if (importer != null && importer.textureType != TextureImporterType.NormalMap)
            {
                importer.textureType = TextureImporterType.NormalMap;
                importer.SaveAndReimport();
                normalTex = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
            }
            mat.SetTexture("_BumpMap", normalTex);
            mat.EnableKeyword("_NORMALMAP");
        }

        mat.SetFloat("_Smoothness", 0.85f);
        mat.SetFloat("_Metallic", 0f);
        mat.SetFloat("_SpecularHighlights", 1f);
        mat.SetFloat("_EnvironmentReflections", 1f);
        mat.EnableKeyword("_SPECULARHIGHLIGHTS_ON");
        mat.EnableKeyword("_ENVIRONMENTREFLECTIONS_ON");

        EditorUtility.SetDirty(mat);
        Debug.Log($"Baked and assigned textures for {materialName}");
    }

    static float[] BuildContentMask(Texture2D tex)
    {
        int w = tex.width;
        int h = tex.height;
        Color[] pixels = tex.GetPixels();
        float[] mask = new float[pixels.Length];

        Color bgSum = Color.black;
        int count = 0;
        for (int i = 0; i < EdgeSamples; i++)
        {
            bgSum += pixels[i * (w / EdgeSamples)];
            bgSum += pixels[(h - 1) * w + i * (w / EdgeSamples)];
            bgSum += pixels[i * (h / EdgeSamples) * w];
            bgSum += pixels[i * (h / EdgeSamples) * w + (w - 1)];
            count += 4;
        }
        Color bgColor = bgSum / count;
        Debug.Log($"Detected iris background color: R={bgColor.r:F3} G={bgColor.g:F3} B={bgColor.b:F3}");

        for (int i = 0; i < pixels.Length; i++)
        {
            float dr = pixels[i].r - bgColor.r;
            float dg = pixels[i].g - bgColor.g;
            float db = pixels[i].b - bgColor.b;
            float diff = Mathf.Sqrt(dr * dr + dg * dg + db * db);
            mask[i] = Mathf.Clamp01((diff - MaskThreshold) / 0.05f);
        }

        return mask;
    }

    static Texture2D CompositeWithMask(Texture2D sclera, Texture2D iris, float[] mask, bool applyTint)
    {
        int w = sclera.width;
        int h = sclera.height;
        var result = new Texture2D(w, h, TextureFormat.RGBA32, false);

        Color[] bgPixels = sclera.GetPixels();
        Color[] irisPixels = iris.GetPixels();
        Color[] output = new Color[bgPixels.Length];

        bool sameSize = (iris.width == w && iris.height == h);

        for (int py = 0; py < h; py++)
        {
            for (int px = 0; px < w; px++)
            {
                int idx = py * w + px;

                Color irisCol;
                float m;
                if (sameSize)
                {
                    irisCol = irisPixels[idx];
                    m = mask[idx];
                }
                else
                {
                    float u = (px + 0.5f) / w;
                    float v = (py + 0.5f) / h;
                    int ix = Mathf.Clamp((int)(u * iris.width), 0, iris.width - 1);
                    int iy = Mathf.Clamp((int)(v * iris.height), 0, iris.height - 1);
                    int iIdx = iy * iris.width + ix;
                    irisCol = irisPixels[iIdx];
                    m = mask[iIdx];
                }

                if (m <= 0f)
                {
                    output[idx] = bgPixels[idx];
                }
                else
                {
                    if (applyTint)
                    {
                        float lum = irisCol.grayscale;

                        if (lum < PupilThreshold)
                        {
                            irisCol = new Color(0.01f, 0.01f, 0.01f, 1f);
                        }
                        else
                        {
                            float r = irisCol.r * IrisBrightness;
                            float g = irisCol.g * IrisBrightness;
                            float b = irisCol.b * IrisBrightness;

                            irisCol = new Color(
                                Mathf.Lerp(r, r * IrisTint.r * 1.8f, 0.5f),
                                Mathf.Lerp(g, g * IrisTint.g * 1.8f, 0.5f),
                                Mathf.Lerp(b, b * IrisTint.b * 1.8f, 0.5f),
                                1f
                            );

                            float edgeDarken = Mathf.Lerp(0.6f, 1f, Mathf.Clamp01(m * 2f));
                            irisCol *= edgeDarken;

                            irisCol.r = Mathf.Clamp01(irisCol.r);
                            irisCol.g = Mathf.Clamp01(irisCol.g);
                            irisCol.b = Mathf.Clamp01(irisCol.b);
                        }
                    }

                    output[idx] = Color.Lerp(bgPixels[idx], irisCol, m);
                    output[idx].a = 1f;
                }
            }
        }

        result.SetPixels(output);
        result.Apply();
        return result;
    }

    static Texture2D ShrinkPupil(Texture2D iris)
    {
        int w = iris.width;
        int h = iris.height;
        Color[] pixels = iris.GetPixels();
        Color[] output = (Color[])pixels.Clone();

        float cx = w * 0.5f;
        float cy = h * 0.5f;
        float shrinkPx = PupilShrinkRadius * w;

        float pupilRadiusPx = 0;
        for (int r = 0; r < w / 2; r++)
        {
            int px = (int)(cx + r);
            int py = (int)cy;
            if (px >= w) break;
            Color c = pixels[py * w + px];
            if (c.grayscale > 0.12f)
            {
                pupilRadiusPx = r;
                break;
            }
        }

        if (pupilRadiusPx < 5) return iris;

        float newPupilRadius = pupilRadiusPx - shrinkPx;
        if (newPupilRadius < 3) newPupilRadius = 3;

        Debug.Log($"Pupil shrink: original radius={pupilRadiusPx:F0}px, " +
            $"new={newPupilRadius:F0}px, shrink={shrinkPx:F0}px");

        for (int py = 0; py < h; py++)
        {
            for (int px = 0; px < w; px++)
            {
                float dx = px - cx;
                float dy = py - cy;
                float dist = Mathf.Sqrt(dx * dx + dy * dy);

                if (dist >= newPupilRadius && dist < pupilRadiusPx + 2)
                {
                    float angle = Mathf.Atan2(dy, dx);
                    float sampleDist = pupilRadiusPx + shrinkPx * 0.5f;
                    int sx = Mathf.Clamp((int)(cx + Mathf.Cos(angle) * sampleDist), 0, w - 1);
                    int sy = Mathf.Clamp((int)(cy + Mathf.Sin(angle) * sampleDist), 0, h - 1);
                    Color irisColor = pixels[sy * w + sx];

                    float t = Mathf.Clamp01((dist - newPupilRadius) / (pupilRadiusPx - newPupilRadius));
                    output[py * w + px] = Color.Lerp(pixels[py * w + px], irisColor, t);
                }
            }
        }

        var result = new Texture2D(w, h, TextureFormat.RGBA32, false);
        result.SetPixels(output);
        result.Apply();
        return result;
    }

    static Texture2D LoadReadable(string assetPath)
    {
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
        if (tex == null)
        {
            Debug.LogWarning($"Texture not found: {assetPath}");
            return null;
        }

        var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
        if (importer != null && !importer.isReadable)
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            tex = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
        }

        return tex;
    }

    static void SaveTexture(Texture2D tex, string assetPath)
    {
        string fullPath = Path.Combine(Application.dataPath, "..", assetPath);
        fullPath = Path.GetFullPath(fullPath);
        byte[] bytes = tex.EncodeToPNG();
        File.WriteAllBytes(fullPath, bytes);
        Debug.Log($"Saved: {assetPath}");
    }

    static void SetupEyeShell()
    {
        var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath + "MI_Face_EyeShell.mat");
        if (mat == null) return;

        mat.SetColor("_BaseColor", new Color(1f, 1f, 1f, 0.04f));
        mat.SetColor("_Color", new Color(1f, 1f, 1f, 0.04f));
        mat.SetFloat("_Smoothness", 0.98f);
        mat.SetFloat("_Metallic", 0f);
        mat.SetFloat("_SpecularHighlights", 1f);
        mat.SetFloat("_EnvironmentReflections", 1f);
        mat.SetFloat("_Surface", 1f);
        mat.SetFloat("_Blend", 0f);
        mat.SetFloat("_SrcBlend", 1f);
        mat.SetFloat("_DstBlend", 10f);
        mat.SetFloat("_ZWrite", 0f);
        mat.renderQueue = 3000;
        mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        mat.EnableKeyword("_ALPHAPREMULTIPLY_ON");
        mat.EnableKeyword("_SPECULARHIGHLIGHTS_ON");
        mat.EnableKeyword("_ENVIRONMENTREFLECTIONS_ON");

        EditorUtility.SetDirty(mat);
        Debug.Log("EyeShell configured for corneal wet-look overlay");
    }
}
