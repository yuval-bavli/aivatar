#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class FixEyebrows
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Find eyebrow
        MeshRenderer eyebrowMR = null;
        foreach (var mr in Object.FindObjectsByType<MeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mr.name.Contains("Eyebrow"))
            {
                eyebrowMR = mr;
                break;
            }
        }
        if (eyebrowMR == null) return "ERROR: No eyebrow MeshRenderer found";

        // Find viseme_animation root
        Transform visemeRoot = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.name == "viseme_animation" && go.transform.parent == null)
            {
                visemeRoot = go.transform;
                break;
            }
        }
        if (visemeRoot == null) return "ERROR: viseme_animation root not found";

        var t = eyebrowMR.transform;

        // 1. Enable renderer
        Undo.RecordObject(eyebrowMR, "Fix eyebrows");
        eyebrowMR.enabled = true;
        EditorUtility.SetDirty(eyebrowMR);

        // 2. Parent to viseme_animation root, scale 0.01 (cm->m)
        Undo.SetTransformParent(t, visemeRoot, "Reparent eyebrows");
        t.localRotation = Quaternion.identity;
        t.localScale = Vector3.one * 0.01f;
        // The eyebrow mesh Y range is -12 to -7 (cm), meaning they sit ~10cm behind
        // the face surface. Push forward by adjusting local Z (Unity) = mesh Y * scale.
        // Mesh avg Y ≈ -9.7cm. We need to push forward ~10cm = 0.10m in world Z.
        // In local space at scale 0.01, that's localPos.z offset.
        // But actually: localPos is applied BEFORE scale, so to move 0.10m in world,
        // we set localPos.z = 0.10 (since parent is visemeRoot at world origin area).
        // Actually no — localPos IS in parent space and doesn't get multiplied by localScale.
        // Wait, localPosition IS in parent space units (meters). So just set z offset directly.
        // Face Z=-8.63, eyebrows Z=-8.71, need to push Z toward camera (+Z direction)
        // Also the Y is 1.68 vs face 1.48 — too high by 0.1m. Adjust both.
        // Try pushing in Y (in mesh local: this is Z in UE = height, already correct)
        // The issue is depth: mesh Y=-9.7cm average needs to come forward.
        // In Unity world: more positive Z = toward camera (face is at Z=-8.63)
        // So we need localPos that maps to world Z = -8.63 instead of -8.71
        // That's a delta of +0.08 in world Z. Let's try localPos adjustments.
        t.localPosition = new Vector3(0, 0.10f, -0.10f);
        EditorUtility.SetDirty(t);

        // 3. Fix material to ensure visibility
        var mat = eyebrowMR.sharedMaterial;
        if (mat != null)
        {
            Undo.RecordObject(mat, "Fix eyebrow material");

            // Check texture alpha channel
            var tex = mat.GetTexture("_BaseMap") as Texture2D;
            sb.AppendLine($"Texture: {tex?.name ?? "NULL"} format={tex?.format} size={tex?.width}x{tex?.height}");

            // Use the EyebrowOverlay shader if available, otherwise fix URP/Lit settings
            var overlayShader = Shader.Find("Custom/EyebrowOverlay");
            if (overlayShader == null)
                overlayShader = Shader.Find("EyebrowPass");

            if (overlayShader != null)
            {
                mat.shader = overlayShader;
                sb.AppendLine($"Switched to overlay shader: {overlayShader.name}");
            }
            else
            {
                // Stay on URP/Lit but ensure it renders on top
                // Set depth bias to push forward
                mat.renderQueue = 2451; // Just above TransparentCutout
                sb.AppendLine("No overlay shader found, using URP/Lit with queue 2451");
            }

            EditorUtility.SetDirty(mat);
        }

        // Report
        sb.AppendLine($"World bounds: center={eyebrowMR.bounds.center} size={eyebrowMR.bounds.size}");
        sb.AppendLine($"Enabled: {eyebrowMR.enabled}");

        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (smr.name == "Face_LOD0" && GetPath(smr.transform).Contains("viseme_animation"))
            {
                sb.AppendLine($"Face bounds: center={smr.bounds.center} size={smr.bounds.size}");
                break;
            }
        }

        return sb.ToString();
    }

    /// <summary>
    /// Debug: try different scale values to find the right one
    /// </summary>
    public static string TryScale()
    {
        var sb = new System.Text.StringBuilder();

        MeshRenderer eyebrowMR = null;
        foreach (var mr in Object.FindObjectsByType<MeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (mr.name.Contains("Eyebrow"))
            {
                eyebrowMR = mr;
                break;
            }
        }
        if (eyebrowMR == null) return "ERROR: No eyebrow";

        // Enable
        eyebrowMR.enabled = true;

        var mf = eyebrowMR.GetComponent<MeshFilter>();
        var mesh = mf.sharedMesh;
        sb.AppendLine($"Mesh verts={mesh.vertexCount}");
        sb.AppendLine($"Mesh bounds: center={mesh.bounds.center} size={mesh.bounds.size}");

        // Check a few vertices to understand the coordinate space
        if (mesh.isReadable)
        {
            var verts = mesh.vertices;
            float minX = float.MaxValue, maxX = float.MinValue;
            float minY = float.MaxValue, maxY = float.MinValue;
            float minZ = float.MaxValue, maxZ = float.MinValue;
            foreach (var v in verts)
            {
                if (v.x < minX) minX = v.x;
                if (v.x > maxX) maxX = v.x;
                if (v.y < minY) minY = v.y;
                if (v.y > maxY) maxY = v.y;
                if (v.z < minZ) minZ = v.z;
                if (v.z > maxZ) maxZ = v.z;
            }
            sb.AppendLine($"Vertex ranges: X=[{minX:F2},{maxX:F2}] Y=[{minY:F2},{maxY:F2}] Z=[{minZ:F2},{maxZ:F2}]");
        }
        else
        {
            sb.AppendLine("Mesh not readable!");
        }

        // Get face SMR bone positions for reference
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (smr.name == "Face_LOD0" && GetPath(smr.transform).Contains("viseme_animation"))
            {
                // Find FACIAL_L_browMidInner bone
                foreach (var bone in smr.bones)
                {
                    if (bone != null && bone.name.Contains("brow"))
                    {
                        sb.AppendLine($"Bone '{bone.name}' world={bone.position}");
                    }
                }
                break;
            }
        }

        return sb.ToString();
    }

    private static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null)
        {
            t = t.parent;
            path = t.name + "/" + path;
        }
        return path;
    }
}
#endif
