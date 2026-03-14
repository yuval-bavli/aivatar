using UnityEngine;
using UnityEditor;

public static class FixEyebrowPosition
{
    [MenuItem("Aivatar/Fix Eyebrow Position")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        // Clean up debug cube
        var oldCube = GameObject.Find("DEBUG_BROW_CUBE");
        if (oldCube != null) Object.DestroyImmediate(oldCube);

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        var faceGO = FindRendererByName("SKM_model4_FaceMesh");

        if (browGO == null || faceGO == null)
        {
            log.AppendLine("ERROR: Could not find eyebrow or face mesh");
            return log.ToString();
        }

        var faceRenderer = faceGO.GetComponent<Renderer>();
        var browRenderer = browGO.GetComponent<Renderer>();

        if (faceRenderer == null || browRenderer == null)
        {
            log.AppendLine("ERROR: Missing renderers");
            return log.ToString();
        }

        // Face bounds: center Y=1.49, top of face Y ≈ 1.68
        // Eyebrows should be at roughly face center Y + 0.10 (just above eye level)
        Vector3 targetCenter = faceRenderer.bounds.center;
        targetCenter.y += 0.10f; // Slightly above face center (eyebrow height)
        targetCenter.z -= 0.01f; // Slightly forward from face center

        // Current eyebrow center in world space
        Vector3 currentCenter = browRenderer.bounds.center;
        log.AppendLine($"Face center: {faceRenderer.bounds.center}");
        log.AppendLine($"Face size: {faceRenderer.bounds.size}");
        log.AppendLine($"Current eyebrow center: {currentCenter}");
        log.AppendLine($"Target eyebrow center: {targetCenter}");

        // Compute the world offset needed
        Vector3 worldOffset = targetCenter - currentCenter;
        log.AppendLine($"World offset needed: {worldOffset}");

        // Convert world offset to local position adjustment
        // The eyebrow's parent is SKM_model4_FaceMesh, which is a child of SKM_model4_BodyMesh
        // We need to transform the world offset into the parent's local space
        var parent = browGO.transform.parent;
        Vector3 localOffset = Vector3.zero;

        if (parent != null)
        {
            // Transform world offset to parent local space direction
            // parent.InverseTransformDirection handles the rotation chain
            Transform root = parent;
            while (root.parent != null) root = root.parent;
            localOffset = parent.InverseTransformDirection(worldOffset);
            // But wait - parent (SKM_model4_FaceMesh) has identity transform
            // So we need to go to grandparent
            if (parent.parent != null)
            {
                localOffset = parent.InverseTransformDirection(worldOffset);
            }
        }

        log.AppendLine($"Local offset computed: {localOffset}");

        // Apply the offset to current local position
        Vector3 newLocalPos = browGO.transform.localPosition + localOffset;
        browGO.transform.localPosition = newLocalPos;
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"New local pos: {browGO.transform.localPosition}");
        log.AppendLine($"New world pos: {browGO.transform.position}");
        log.AppendLine($"New world bounds: center={browRenderer.bounds.center}, size={browRenderer.bounds.size}");

        // Now restore the eyebrow material to proper settings (not debug red)
        var browMat = AssetDatabase.LoadAssetAtPath<Material>(
            "Assets/Models/Avatar/Materials/Eyebrows.mat");
        var hairTex = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Color_1K.png");
        var hairNorm = AssetDatabase.LoadAssetAtPath<Texture2D>(
            "Assets/Models/Avatar/Textures/HairCard0_Normal_1K.jpg");

        if (browMat != null)
        {
            browMat.SetTexture("_BaseMap", hairTex);
            browMat.SetTexture("_BumpMap", hairNorm);
            browMat.SetColor("_BaseColor", new Color(0.14f, 0.09f, 0.06f, 1f));
            browMat.SetFloat("_AlphaClip", 1f);
            browMat.EnableKeyword("_ALPHATEST_ON");
            browMat.EnableKeyword("_NORMALMAP");
            browMat.SetFloat("_Cutoff", 0.03f);
            browMat.SetFloat("_Smoothness", 0.1f);
            browMat.SetFloat("_Cull", 0f); // Double-sided
            browMat.SetFloat("_Surface", 0f); // Opaque
            browMat.renderQueue = 2451;
            EditorUtility.SetDirty(browMat);
            log.AppendLine("Eyebrow material restored to proper settings");
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

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == name) return r.gameObject;
        }
        return null;
    }
}
