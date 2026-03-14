using UnityEngine;
using UnityEditor;
using System.IO;
using System.Text;

public static class DiagnoseAppearance
{
    [MenuItem("Aivatar/Diagnose Appearance")]
    public static string Run()
    {
        var sb = new StringBuilder();

        // Find all renderers in the scene
        var renderers = Object.FindObjectsOfType<Renderer>();
        sb.AppendLine($"=== SCENE RENDERERS ({renderers.Length}) ===");
        foreach (var r in renderers)
        {
            sb.AppendLine($"\nRenderer: {r.gameObject.name} (path: {GetPath(r.transform)})");
            sb.AppendLine($"  Type: {r.GetType().Name}, Enabled: {r.enabled}, GO Active: {r.gameObject.activeInHierarchy}");
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                var m = mats[i];
                if (m == null) { sb.AppendLine($"  Mat[{i}]: NULL"); continue; }
                sb.AppendLine($"  Mat[{i}]: {m.name} | Shader: {m.shader.name} | RenderQueue: {m.renderQueue}");

                // Check key properties
                if (m.HasProperty("_BaseMap"))
                {
                    var tex = m.GetTexture("_BaseMap");
                    sb.AppendLine($"    _BaseMap: {(tex != null ? tex.name + " (" + tex.width + "x" + tex.height + ")" : "NULL")}");
                }
                if (m.HasProperty("_BaseColor"))
                    sb.AppendLine($"    _BaseColor: {m.GetColor("_BaseColor")}");
                if (m.HasProperty("_Cutoff"))
                    sb.AppendLine($"    _Cutoff: {m.GetFloat("_Cutoff")}");
                if (m.HasProperty("_Surface"))
                    sb.AppendLine($"    _Surface: {m.GetFloat("_Surface")} (0=Opaque,1=Transparent)");
                if (m.HasProperty("_AlphaClip"))
                    sb.AppendLine($"    _AlphaClip: {m.GetFloat("_AlphaClip")}");
                if (m.HasProperty("_Blend"))
                    sb.AppendLine($"    _Blend: {m.GetFloat("_Blend")}");
                if (m.HasProperty("_Cull"))
                    sb.AppendLine($"    _Cull: {m.GetFloat("_Cull")} (0=Off,1=Front,2=Back)");
                if (m.HasProperty("_BumpMap"))
                {
                    var nm = m.GetTexture("_BumpMap");
                    sb.AppendLine($"    _BumpMap: {(nm != null ? nm.name : "NULL")}");
                }

                // Check all keywords
                var keywords = m.shaderKeywords;
                if (keywords.Length > 0)
                    sb.AppendLine($"    Keywords: {string.Join(", ", keywords)}");
            }

            // If SkinnedMeshRenderer, show blendshape count and mesh info
            if (r is SkinnedMeshRenderer smr && smr.sharedMesh != null)
            {
                sb.AppendLine($"  Mesh: {smr.sharedMesh.name}, Submeshes: {smr.sharedMesh.subMeshCount}, BlendShapes: {smr.sharedMesh.blendShapeCount}");
            }
            else if (r is MeshRenderer mr)
            {
                var mf = r.GetComponent<MeshFilter>();
                if (mf != null && mf.sharedMesh != null)
                    sb.AppendLine($"  Mesh: {mf.sharedMesh.name}, Submeshes: {mf.sharedMesh.subMeshCount}");
            }
        }

        // Check hair texture import settings
        sb.AppendLine("\n=== TEXTURE IMPORT SETTINGS ===");
        string[] texPaths = {
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png",
            "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_BaseColor_8.png",
            "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_Opacity_8.png",
            "Assets/Models/Avatar/MI_Face_EyelashesHiLODs_OpacityMask_8.png",
        };
        foreach (var tp in texPaths)
        {
            var importer = AssetImporter.GetAtPath(tp) as TextureImporter;
            if (importer == null) { sb.AppendLine($"{tp}: NOT FOUND"); continue; }
            sb.AppendLine($"\n{tp}:");
            sb.AppendLine($"  textureType: {importer.textureType}");
            sb.AppendLine($"  alphaSource: {importer.alphaSource}");
            sb.AppendLine($"  alphaIsTransparency: {importer.alphaIsTransparency}");
            sb.AppendLine($"  sRGBTexture: {importer.sRGBTexture}");
            sb.AppendLine($"  maxTextureSize: {importer.maxTextureSize}");
            sb.AppendLine($"  textureCompression: {importer.textureCompression}");
            sb.AppendLine($"  isReadable: {importer.isReadable}");
        }

        // Check for eyebrow-related GameObjects
        sb.AppendLine("\n=== EYEBROW SEARCH ===");
        var allTransforms = Object.FindObjectsOfType<Transform>();
        foreach (var t in allTransforms)
        {
            string name = t.gameObject.name.ToLower();
            if (name.Contains("brow") || name.Contains("eyebrow"))
            {
                sb.AppendLine($"  Found: {GetPath(t)} (active: {t.gameObject.activeInHierarchy})");
                var ren = t.GetComponent<Renderer>();
                if (ren != null)
                {
                    sb.AppendLine($"    Has Renderer: {ren.GetType().Name}, enabled: {ren.enabled}");
                    foreach (var m in ren.sharedMaterials)
                        sb.AppendLine($"    Material: {(m != null ? m.name : "NULL")}");
                }
            }
        }

        // Also search for hair-related GameObjects
        sb.AppendLine("\n=== HAIR SEARCH ===");
        foreach (var t in allTransforms)
        {
            string name = t.gameObject.name.ToLower();
            if (name.Contains("hair") || name.Contains("haircut"))
            {
                sb.AppendLine($"  Found: {GetPath(t)} (active: {t.gameObject.activeInHierarchy})");
                var ren = t.GetComponent<Renderer>();
                if (ren != null)
                {
                    sb.AppendLine($"    Has Renderer: {ren.GetType().Name}, enabled: {ren.enabled}");
                    foreach (var m in ren.sharedMaterials)
                        sb.AppendLine($"    Material: {(m != null ? m.name : "NULL")}");
                }
            }
        }

        // Sample hair texture pixels to understand the alpha
        sb.AppendLine("\n=== HAIR TEXTURE PIXEL SAMPLING ===");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        if (hairTex != null)
        {
            // Make readable copy
            var rt = RenderTexture.GetTemporary(hairTex.width, hairTex.height, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(hairTex, rt);
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var readable = new Texture2D(hairTex.width, hairTex.height, TextureFormat.RGBA32, false);
            readable.ReadPixels(new Rect(0, 0, hairTex.width, hairTex.height), 0, 0);
            readable.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);

            // Sample pixels in a grid
            int alphaZero = 0, alphaFull = 0, alphaPartial = 0;
            for (int y = 0; y < readable.height; y += 16)
            {
                for (int x = 0; x < readable.width; x += 16)
                {
                    var c = readable.GetPixel(x, y);
                    if (c.a < 0.01f) alphaZero++;
                    else if (c.a > 0.99f) alphaFull++;
                    else alphaPartial++;
                }
            }
            sb.AppendLine($"  Size: {readable.width}x{readable.height}");
            sb.AppendLine($"  Alpha distribution (sampled every 16px): zero={alphaZero}, partial={alphaPartial}, full={alphaFull}");

            // Sample some specific pixels to see colors
            sb.AppendLine("  Sample pixels (center area):");
            for (int y = 400; y <= 600; y += 50)
            {
                for (int x = 400; x <= 600; x += 50)
                {
                    var c = readable.GetPixel(x, y);
                    sb.AppendLine($"    [{x},{y}] RGBA=({c.r:F2},{c.g:F2},{c.b:F2},{c.a:F2})");
                }
            }

            Object.DestroyImmediate(readable);
        }

        string result = sb.ToString();
        string path = Path.Combine(Application.dataPath, "..", "diagnose_result.txt");
        File.WriteAllText(path, result);
        Debug.Log($"Diagnosis written to {path}");
        return result;
    }

    static string GetPath(Transform t)
    {
        if (t.parent == null) return t.name;
        return GetPath(t.parent) + "/" + t.name;
    }
}
