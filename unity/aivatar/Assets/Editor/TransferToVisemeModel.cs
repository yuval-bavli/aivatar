#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Transfers materials from model4 to the viseme_animation model,
/// reparents hair/eyebrows, and sets up animation-based lip sync.
/// </summary>
public static class TransferToVisemeModel
{
    public static string Diagnose()
    {
        var sb = new System.Text.StringBuilder();

        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);

        sb.AppendLine("=== SkinnedMeshRenderers ===");
        foreach (var smr in allSMRs)
        {
            string path = GetPath(smr.transform);
            sb.AppendLine($"'{smr.name}' path={path} bones={smr.bones.Length} mats={smr.sharedMaterials.Length}");
            for (int i = 0; i < smr.sharedMaterials.Length; i++)
            {
                var mat = smr.sharedMaterials[i];
                sb.AppendLine($"  [{i}] '{mat?.name ?? "NULL"}' tex={mat?.mainTexture?.name ?? "none"}");
            }
        }

        return sb.ToString();
    }

    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Find key objects
        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);

        SkinnedMeshRenderer visemeFace = null;
        SkinnedMeshRenderer model4Face = null;

        foreach (var smr in allSMRs)
        {
            string path = GetPath(smr.transform);
            if (smr.name == "Face_LOD0" && path.Contains("viseme_animation"))
                visemeFace = smr;
            if (smr.name.Contains("FaceMesh") && smr.bones.Length > 100 && !path.Contains("viseme_animation"))
                model4Face = smr;
        }

        if (visemeFace == null) return "ERROR: viseme_animation Face_LOD0 not found";
        if (model4Face == null) return "ERROR: model4 FaceMesh SMR not found";

        sb.AppendLine($"Source: '{model4Face.name}' ({model4Face.sharedMaterials.Length} mats)");
        sb.AppendLine($"Target: '{visemeFace.name}' ({visemeFace.sharedMaterials.Length} mats)");

        // Step 1: Restore model4's original mesh if it was swapped
        var originalMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX");
        if (originalMesh == null)
            originalMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Models/Avatar/SKM_model4_FaceMesh.FBX");
        if (originalMesh != null && model4Face.sharedMesh.name.Contains("VisemesFromAnim"))
        {
            // Find the correct mesh sub-asset
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath("Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX"))
            {
                if (asset is Mesh m && m.name.Contains("FaceMesh"))
                {
                    Undo.RecordObject(model4Face, "Restore original mesh");
                    model4Face.sharedMesh = m;
                    EditorUtility.SetDirty(model4Face);
                    sb.AppendLine($"Restored model4 original mesh: '{m.name}' verts={m.vertexCount}");
                    break;
                }
            }
        }

        // Step 2: Copy materials from model4 to viseme_animation Face_LOD0
        // Both are 9-submesh MetaHuman face meshes. The submesh ordering may differ
        // between FBX exports, so we need to match by geometry (vertex ranges).
        //
        // Strategy: just copy the materials array. Both FBXes come from the same
        // MetaHuman so the submesh order should match. If it looks wrong, we'll fix.
        var srcMats = model4Face.sharedMaterials;
        var dstMats = new Material[visemeFace.sharedMaterials.Length];

        // Copy materials index by index (both have 9 slots)
        int copyCount = Mathf.Min(srcMats.Length, dstMats.Length);
        for (int i = 0; i < copyCount; i++)
            dstMats[i] = srcMats[i];
        // Fill remaining with default if target has more slots
        for (int i = copyCount; i < dstMats.Length; i++)
            dstMats[i] = visemeFace.sharedMaterials[i];

        Undo.RecordObject(visemeFace, "Copy materials");
        visemeFace.sharedMaterials = dstMats;
        EditorUtility.SetDirty(visemeFace);

        sb.AppendLine("\nMaterial mapping:");
        for (int i = 0; i < dstMats.Length; i++)
            sb.AppendLine($"  [{i}] '{dstMats[i]?.name ?? "NULL"}'");

        // Step 3: Find and reparent hair/eyebrows to viseme_animation
        Transform visemeRoot = visemeFace.transform;
        while (visemeRoot.parent != null) visemeRoot = visemeRoot.parent;

        // Find the head bone in viseme_animation to parent hair/eyebrows to
        Transform visemeHeadBone = FindBoneRecursive(visemeRoot, "head");
        if (visemeHeadBone == null)
            visemeHeadBone = visemeFace.transform; // fallback

        sb.AppendLine($"\nViseme head bone: '{visemeHeadBone.name}' at {GetPath(visemeHeadBone)}");

        var allMRs = Object.FindObjectsByType<MeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        foreach (var mr in allMRs)
        {
            string path = GetPath(mr.transform);
            if (path.Contains("Hair_") || path.Contains("Eyebrows_"))
            {
                if (!path.Contains("viseme_animation")) // don't reparent if already under viseme
                {
                    sb.AppendLine($"Found: '{mr.name}' at {path}");
                    // Store world transform
                    Vector3 worldPos = mr.transform.position;
                    Quaternion worldRot = mr.transform.rotation;
                    Vector3 worldScale = mr.transform.lossyScale;

                    Undo.SetTransformParent(mr.transform, visemeHeadBone, "Reparent hair/eyebrows");
                    mr.transform.position = worldPos;
                    mr.transform.rotation = worldRot;
                    // Approximate scale preservation
                    if (visemeHeadBone.lossyScale.x > 0.0001f)
                        mr.transform.localScale = new Vector3(
                            worldScale.x / visemeHeadBone.lossyScale.x,
                            worldScale.y / visemeHeadBone.lossyScale.y,
                            worldScale.z / visemeHeadBone.lossyScale.z);

                    sb.AppendLine($"  -> Reparented to '{visemeHeadBone.name}'");
                }
            }
        }

        // Step 4: Also copy materials to Body LOD0 on viseme_animation
        foreach (var smr in allSMRs)
        {
            string path = GetPath(smr.transform);
            if (smr.name == "Body_LOD0" && path.Contains("viseme_animation"))
            {
                // Find model4's body mesh
                SkinnedMeshRenderer model4Body = null;
                foreach (var s in allSMRs)
                {
                    if (s.name == "SKM_model4_BodyMesh" && !GetPath(s.transform).Contains("viseme"))
                    {
                        model4Body = s;
                        break;
                    }
                }
                if (model4Body != null)
                {
                    var bodyMats = new Material[smr.sharedMaterials.Length];
                    for (int i = 0; i < bodyMats.Length; i++)
                    {
                        if (i < model4Body.sharedMaterials.Length)
                            bodyMats[i] = model4Body.sharedMaterials[i];
                        else
                            bodyMats[i] = smr.sharedMaterials[i];
                    }
                    Undo.RecordObject(smr, "Copy body materials");
                    smr.sharedMaterials = bodyMats;
                    EditorUtility.SetDirty(smr);
                    sb.AppendLine($"\nCopied body materials to '{smr.name}'");
                }
            }
        }

        // Step 5: Align viseme_animation position to match model4
        Transform model4Root = model4Face.transform;
        while (model4Root.parent != null) model4Root = model4Root.parent;

        // Both should be at origin, but just in case
        Undo.RecordObject(visemeRoot, "Align viseme model");
        visemeRoot.position = model4Root.position;
        visemeRoot.rotation = model4Root.rotation;
        visemeRoot.localScale = model4Root.localScale;
        EditorUtility.SetDirty(visemeRoot);
        sb.AppendLine($"\nAligned viseme_animation to model4 root position");

        // Step 6: Hide model4 objects (don't delete - keep as backup)
        // Find all top-level model4 GameObjects
        var model4Roots = new List<GameObject>();
        foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.transform.parent == null)
            {
                string name = go.name;
                if (name.Contains("SKM_model4") || name == "SKM_model4_FaceMesh_Visemes")
                    model4Roots.Add(go);
            }
        }

        foreach (var go in model4Roots)
        {
            Undo.RecordObject(go, "Hide model4");
            go.SetActive(false);
            EditorUtility.SetDirty(go);
            sb.AppendLine($"Disabled '{go.name}'");
        }

        sb.AppendLine("\nDone! Materials transferred, hair reparented, model4 hidden.");
        sb.AppendLine("Next: set up AnimLipSync on the Avatar to drive viseme_animation.");
        return sb.ToString();
    }

    private static Transform FindBoneRecursive(Transform root, string boneName)
    {
        if (root.name == boneName) return root;
        foreach (Transform child in root)
        {
            var found = FindBoneRecursive(child, boneName);
            if (found != null) return found;
        }
        return null;
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
