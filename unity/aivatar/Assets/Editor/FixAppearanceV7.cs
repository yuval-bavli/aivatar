using UnityEngine;
using UnityEditor;
using System.IO;

public static class FixAppearanceV7
{
    [MenuItem("Aivatar/Fix Appearance V7")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (browGO != null)
        {
            // The avg world normal of eyebrow faces is roughly (0, -0.11, -0.99)
            // We want to push the eyebrows outward from the face by ~0.003 world units
            Vector3 worldNormal = new Vector3(-0.10f, -0.11f, -0.99f).normalized;
            float pushDistance = 0.003f; // 3mm in world space

            // Convert world direction to local direction
            Vector3 worldOffset = worldNormal * pushDistance;
            // The eyebrow's localPosition is in parent space (SKM_model4_FaceMesh)
            // which is a child of SKM_model4_BodyMesh
            // Use the parent's InverseTransformDirection to get the local offset
            var parent = browGO.transform.parent;
            Vector3 localOffset = Vector3.zero;
            if (parent != null && parent.parent != null)
            {
                // Go through the whole chain
                localOffset = browGO.transform.parent.InverseTransformDirection(
                    browGO.transform.parent.parent.InverseTransformDirection(worldOffset));
            }

            // Reset to original position first, then apply correct offset
            browGO.transform.localPosition = new Vector3(0.04f, 0f, 0.04f); // Original
            browGO.transform.localPosition += localOffset;

            EditorUtility.SetDirty(browGO);
            log.AppendLine($"Eyebrow pushed: worldOffset={worldOffset}, localOffset={localOffset}");
            log.AppendLine($"New local pos: {browGO.transform.localPosition}");
            log.AppendLine($"New world pos: {browGO.transform.position}");
            log.AppendLine($"New world bounds: {browGO.GetComponent<Renderer>().bounds.center}");

            // Also test: temporarily make eyebrows bright red and opaque to confirm visibility
            var browMat = AssetDatabase.LoadAssetAtPath<Material>(
                "Assets/Models/Avatar/Materials/Eyebrows.mat");
            if (browMat != null)
            {
                browMat.SetFloat("_AlphaClip", 0f);
                browMat.DisableKeyword("_ALPHATEST_ON");
                browMat.SetFloat("_Surface", 0f);
                browMat.SetColor("_BaseColor", new Color(1f, 0f, 0f, 1f)); // BRIGHT RED for debugging
                browMat.SetTexture("_BaseMap", null); // No texture - just solid red
                browMat.renderQueue = 2001;
                browMat.SetFloat("_Cull", 0f);
                EditorUtility.SetDirty(browMat);
                log.AppendLine("DEBUG: Eyebrows set to SOLID RED for visibility test");
            }
        }

        AssetDatabase.SaveAssets();
        string result = log.ToString();
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
