using UnityEngine;
using UnityEditor;

public static class CheckEyebrowMat
{
    public static string Run()
    {
        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no brow renderer";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Renderer: {browRenderer.gameObject.name} enabled={browRenderer.enabled}");
        foreach (var m in browRenderer.sharedMaterials)
        {
            if (m == null) { sb.AppendLine("  mat: NULL"); continue; }
            Color bc = m.GetColor("_BaseColor");
            float cutoff = m.GetFloat("_Cutoff");
            bool alphaTest = m.IsKeywordEnabled("_ALPHATEST_ON");
            Texture baseMap = m.GetTexture("_BaseMap");
            sb.AppendLine($"  mat: {m.name}");
            sb.AppendLine($"    _BaseColor: R={bc.r:F3} G={bc.g:F3} B={bc.b:F3} A={bc.a:F3}");
            sb.AppendLine($"    _Cutoff={cutoff:F3} _ALPHATEST_ON={alphaTest}");
            sb.AppendLine($"    _BaseMap: {(baseMap != null ? baseMap.name : \"NULL\")}");
            sb.AppendLine($"    renderQueue={m.renderQueue}");

            // Force set bright color for test
            m.SetColor("_BaseColor", new Color(0.9f, 0.7f, 0.4f, 1f));
            m.SetFloat("_Cutoff", 0.15f);
            m.EnableKeyword("_ALPHATEST_ON");
            EditorUtility.SetDirty(m);
        }
        AssetDatabase.SaveAssets();
        sb.AppendLine(">> Set BaseColor to bright warm (0.9, 0.7, 0.4)");
        return sb.ToString();
    }
}
