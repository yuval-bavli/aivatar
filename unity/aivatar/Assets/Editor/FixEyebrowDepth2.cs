using UnityEngine;
using UnityEditor;
using System.Text;

/// <summary>
/// Fixes the eyebrow card mesh depth issue.
///
/// Root cause: eyebrow local verts at Z~+63. At scale=0.02: world_vert_z = pivot_z + 63*0.02
/// Previous script placed pivot at face.max.z=-8.517, giving world Z=-7.25 (BEHIND face).
/// Fix: pivot_z = -10.04 so world Z = -8.78 (in front of face, face front ~-8.762).
///
/// Y fix: local Y center ~ -3.895. World Y = pivot_y + (-3.895*0.02) = pivot_y - 0.078.
/// To place eyebrows at world Y=1.59 (above eye level 1.52): pivot_y = 1.59+0.078 = 1.668.
/// </summary>
public static class FixEyebrowDepth2
{
    public static string Run()
    {
        return Apply(solidRed: true);
    }

    public static string ApplyNatural()
    {
        return Apply(solidRed: false);
    }

    static string Apply(bool solidRed)
    {
        var sb = new StringBuilder();

        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer found";

        // Mesh local geometry constants (MetaHuman eyebrow card mesh)
        float localMeshZ = 63.0f;   // local Z of eyebrow card verts
        float localMeshYCenter = -3.895f; // local Y center of cards
        float scale = 0.02f;

        // Face bounds for reference
        float faceFrontZ = -8.762f;   // face front surface (faceBounds.min.z from diagnostics)
        float eyeLevelY = 1.515f;     // world Y of eye center (face Y range 1.304-1.671, ~55%)
        float eyebrowWorldY = eyeLevelY + 0.075f; // eyebrows ~7.5cm above eye center

        // Z: place mesh verts just in front of face surface
        float targetWorldVertZ = faceFrontZ - 0.015f; // 1.5cm in front of face front
        float pivotZ = targetWorldVertZ - localMeshZ * scale;

        // Y: place mesh center at eyebrow level
        float pivotY = eyebrowWorldY - localMeshYCenter * scale;  // = eyebrowY + 0.078

        Transform t = browRenderer.transform;
        t.position = new Vector3(0.03f, pivotY, pivotZ);
        t.localScale = new Vector3(scale, scale, scale);
        t.rotation = Quaternion.identity;

        if (solidRed)
        {
            foreach (var m in browRenderer.sharedMaterials)
            {
                if (m == null) continue;
                m.SetFloat("_AlphaClip", 0f);
                m.DisableKeyword("_ALPHATEST_ON");
                m.SetColor("_BaseColor", Color.red);
                m.renderQueue = 2000;
                EditorUtility.SetDirty(m);
            }
            sb.AppendLine("Material: solid red (for visibility test)");
        }
        else
        {
            // Restore natural hair card rendering
            foreach (var m in browRenderer.sharedMaterials)
            {
                if (m == null) continue;
                m.SetFloat("_AlphaClip", 1f);
                m.EnableKeyword("_ALPHATEST_ON");
                m.SetFloat("_Cutoff", 0.15f);
                // Restore natural brow color (dark brown)
                m.SetColor("_BaseColor", new Color(0.18f, 0.10f, 0.06f, 1f));
                m.renderQueue = 2450;
                EditorUtility.SetDirty(m);
            }
            sb.AppendLine("Material: natural hair card (alpha clip ON, dark brown)");
        }

        browRenderer.enabled = true;
        browRenderer.gameObject.SetActive(true);
        EditorUtility.SetDirty(browRenderer.gameObject);
        AssetDatabase.SaveAssets();

        float actualWorldZ = pivotZ + localMeshZ * scale;
        float actualWorldY = pivotY + localMeshYCenter * scale;
        sb.AppendLine($"Pivot: pos=({t.position.x:F3}, {pivotY:F3}, {pivotZ:F3})");
        sb.AppendLine($"World vert Z: {actualWorldZ:F3} (face front: {faceFrontZ:F3}, delta: {faceFrontZ - actualWorldZ:F3}cm in front)");
        sb.AppendLine($"World vert Y center: {actualWorldY:F3} (eye level: {eyeLevelY:F3})");
        sb.AppendLine($"Bounds: center={browRenderer.bounds.center} size={browRenderer.bounds.size}");
        return sb.ToString();
    }
}
