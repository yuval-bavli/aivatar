
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

public static class FixEyebrowRenderer
{
    [MenuItem("Aivatar/Fix Eyebrow Renderer")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        
        // Find eyebrow MeshRenderer (NOT SkinnedMeshRenderer)
        var allMeshR = Object.FindObjectsOfType<MeshRenderer>(true);
        foreach (var mr in allMeshR)
        {
            string goName = mr.gameObject.name.ToLower();
            if (goName.Contains("brow") || goName.Contains("eyebrow"))
            {
                mr.enabled = true;
                mr.gameObject.SetActive(true);
                log.AppendLine("Enabled eyebrow renderer: " + mr.gameObject.name);
                
                // Fix material
                var browMat = mr.sharedMaterial;
                if (browMat != null)
                {
                    log.AppendLine("  Material: " + browMat.name);
                    
                    // Log current texture
                    var mainTex = browMat.mainTexture;
                    log.AppendLine("  MainTexture: " + (mainTex != null ? mainTex.name : "null"));
                    
                    var shader = Shader.Find("Universal Render Pipeline/Lit");
                    if (shader != null) browMat.shader = shader;
                    
                    browMat.SetFloat("_AlphaClip", 1f);
                    browMat.SetFloat("_Cutoff", 0.1f);
                    browMat.SetFloat("_Surface", 0f);
                    browMat.SetFloat("_Cull", (float)CullMode.Off);
                    browMat.SetFloat("_ZWrite", 1f);
                    browMat.SetFloat("_Smoothness", 0.1f);
                    browMat.SetFloat("_Metallic", 0f);
                    browMat.SetFloat("_AlphaToMask", 1f);
                    browMat.EnableKeyword("_ALPHATEST_ON");
                    browMat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    browMat.renderQueue = (int)RenderQueue.AlphaTest + 1;
                    browMat.SetOverrideTag("RenderType", "TransparentCutout");
                    
                    EditorUtility.SetDirty(browMat);
                    log.AppendLine("  Material fixed.");
                }
                else
                {
                    log.AppendLine("  WARNING: No material assigned!");
                }
            }
        }
        
        AssetDatabase.SaveAssets();
        return log.ToString();
    }
}
