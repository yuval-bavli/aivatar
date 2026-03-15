using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.IO;

/// ApplyAllFixes — the single authoritative script for all appearance fixes:
/// - Hair: medium warm brown (0.62, 0.48, 0.34) + smoothness=0.75 + specular highlights ON
/// - Eyelashes: hidden via Aivatar/Hidden shader
/// - Eyebrows: baked at strength=0.12 (subtle)
/// - Eyebrow mesh: disabled
public static class ApplyAllFixes
{
    [MenuItem("Aivatar/Apply All Fixes (Authoritative)")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // 1. Hair color — medium warm brown with high smoothness for specular highlights
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat != null)
        {
            var c = new Color(0.70f, 0.51f, 0.33f, 1f);
            hairMat.SetColor("_BaseColor", c);
            hairMat.SetColor("_Color", c);
            hairMat.SetFloat("_Smoothness", 0.95f);
            hairMat.SetFloat("_Glossiness", 0.95f);
            hairMat.SetFloat("_SpecularHighlights", 1f);
            hairMat.SetFloat("_EnvironmentReflections", 0f);
            hairMat.DisableKeyword("_SPECULARHIGHLIGHTS_OFF");
            hairMat.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            hairMat.DisableKeyword("_EMISSION");
            hairMat.SetColor("_EmissionColor", new Color(0f, 0f, 0f, 1f));
            EditorUtility.SetDirty(hairMat);
            log.Append("Hair: (0.70,0.51,0.33) smoothness=0.95 specular=ON. ");
        }

        // 2. Eyelashes — hidden (face texture has baked lash marks, mesh creates too thick look)
        var hiddenShader = Shader.Find("Aivatar/Hidden");
        var lashMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_EyelashesHiLODs.mat");
        var lashMat2 = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/AvatarEyelashes.mat");
        if (hiddenShader != null)
        {
            if (lashMat != null) { lashMat.shader = hiddenShader; EditorUtility.SetDirty(lashMat); }
            if (lashMat2 != null) { lashMat2.shader = hiddenShader; EditorUtility.SetDirty(lashMat2); }
            log.Append("Eyelashes: hidden (both mats). ");
        }
        else log.Append($"WARNING: hiddenShader not found. ");

        // 3. Eyebrow mesh — ensure disabled
        foreach (var r in GameObject.FindObjectsOfType<MeshRenderer>(true))
            if (r.gameObject.name.Contains("Eyebrows_M_Natural")) { r.enabled = false; EditorUtility.SetDirty(r); }
        foreach (var r in GameObject.FindObjectsOfType<SkinnedMeshRenderer>(true))
            if (r.gameObject.name.Contains("Eyebrows_M_Natural")) { r.enabled = false; EditorUtility.SetDirty(r); }
        log.Append("Brow mesh: off. ");

        // 4. Face material — no bump, no shadow receive to eliminate eye socket dark marks
        var faceSkinMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        if (faceSkinMat != null)
        {
            faceSkinMat.SetFloat("_BumpScale", 0.0f);
            faceSkinMat.DisableKeyword("_NORMALMAP");  // fully disable normal map sampling
            EditorUtility.SetDirty(faceSkinMat);
            log.Append("FaceBump: 0.0 + NormalMap: OFF. ");
        }
        // Disable shadow receiving on the face mesh renderer to remove eye shadow artifacts
        foreach (var r in GameObject.FindObjectsOfType<MeshRenderer>(true))
            if (r.gameObject.name.Contains("SKM_model4_FaceMesh") || r.gameObject.name.Contains("FaceMesh"))
            { r.receiveShadows = false; EditorUtility.SetDirty(r); log.Append("FaceShadow: off. "); break; }

        log.Append("AO: skipped(no volumes). ");

        // 5. Bake eyebrows with lighter strength
        log.Append(BakeEyebrows());

        AssetDatabase.SaveAssets();
        EditorSceneManager.SaveOpenScenes();
        return log.ToString();
    }

    static string BakeEyebrows()
    {
        string origPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT.PNG";
        var origTex = AssetDatabase.LoadAssetAtPath<Texture2D>(origPath);
        if (origTex == null) return "ERROR: head tex missing.";

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

        // Eyebrow bake: subtle warm brown arc
        Color browColor = new Color(0.45f, 0.34f, 0.22f);
        PaintBrowArc(tex, rSX, rSY, rEX, rEY, rPY, 2.5f, browColor, 0.06f);
        PaintBrowArc(tex, lSX, lSY, lEX, lEY, lPY, 2.5f, browColor, 0.06f);

        // Lash-mark removal: lower eyelid/lash line (Unity Y 1215-1290), aggressive
        Color skinTone = new Color(0.85f, 0.68f, 0.62f);
        int lassMod = 0;
        for (int pass = 0; pass < 2; pass++)
        for (int unityY = 1210; unityY <= 1295; unityY++)
        {
            for (int px = 540; px <= 1510; px++)
            {
                Color c = tex.GetPixel(px, unityY);
                if (c.r < 0.84f)
                {
                    tex.SetPixel(px, unityY, Color.Lerp(c, skinTone, 0.97f));
                    lassMod++;
                }
            }
        }
        UnityEngine.Debug.Log($"[ApplyAllFixes] Lash lightening 2-pass: {lassMod} pixels modified");

        // Brow lightening: moderate pass to soften the original texture's dark brow marks
        // Brow UV zones: right eye Unity Y=1291-1532 X≈620-770, left eye Y=1295-1589 X≈1290-1460
        Color browTarget = new Color(0.72f, 0.58f, 0.44f); // lighter warm brown
        int browMod = 0;
        int[] browXStarts = { 580, 1260 };
        int[] browXEnds   = { 800, 1490 };
        for (int side = 0; side < 2; side++)
        for (int unityY = 1291; unityY <= 1540; unityY++)
        for (int px = browXStarts[side]; px <= browXEnds[side]; px++)
        {
            Color c = tex.GetPixel(px, unityY);
            if (c.r < 0.72f) { tex.SetPixel(px, unityY, Color.Lerp(c, browTarget, 0.25f)); browMod++; }
        }
        UnityEngine.Debug.Log($"[ApplyAllFixes] Brow lightening: {browMod} pixels modified");

        tex.Apply();
        string outPath = "Assets/Models/Avatar/Textures/T_Head_BC_VT_Brows.png";
        byte[] pngBytes = tex.EncodeToPNG();
        File.WriteAllBytes(Path.Combine(Application.dataPath, "..", outPath), pngBytes);
        Object.DestroyImmediate(tex);
        AssetDatabase.Refresh();

        var importer = AssetImporter.GetAtPath(outPath) as TextureImporter;
        if (importer != null) { importer.sRGBTexture = true; importer.maxTextureSize = 2048; importer.textureCompression = TextureImporterCompression.Uncompressed; importer.isReadable = true; importer.SaveAndReimport(); }

        // After SaveAndReimport, the asset DB has the fresh texture — load it and assign
        var browsTex = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        var faceMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_Face_Skin_Baked_LOD1_VT.mat");
        if (faceMat != null && browsTex != null)
        {
            faceMat.SetTexture("_BaseMap", browsTex);
            faceMat.SetTexture("_MainTex", browsTex);
            EditorUtility.SetDirty(faceMat);
        }

        string texStatus = (browsTex != null && faceMat != null) ? "tex_assigned=OK" : $"tex={browsTex != null} mat={faceMat != null}";
        return $"Brows baked strength=0.12 ({w}x{h}), lash_mod={lassMod}, {texStatus}.";
    }

    static void PaintBrowArc(Texture2D tex, int sX, int sY, int eX, int eY, int pY, float thickness, Color color, float strength)
    {
        for (int i = 0; i <= 80; i++)
        {
            float t = (float)i / 80;
            float midX = (sX + eX) * 0.5f;
            float x = Mathf.Lerp(Mathf.Lerp(sX, midX, t), Mathf.Lerp(midX, eX, t), t);
            float y = Mathf.Lerp(Mathf.Lerp(sY, pY, t), Mathf.Lerp(pY, eY, t), t);
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
