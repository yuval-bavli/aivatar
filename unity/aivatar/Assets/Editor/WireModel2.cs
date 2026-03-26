#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class WireModel4
{
    // Azure viseme ID → blendshape name (matches both AvatarHead and AvatarTeethLower)
    private static readonly (int id, string name)[] VISEME_MAP =
    {
        ( 0, "sil"), ( 1, "PP"),  ( 2, "FF"),  ( 3, "TH"),  ( 4, "DD"),
        ( 5, "kk"),  ( 6, "CH"),  ( 7, "SS"),  ( 8, "nn"),  ( 9, "RR"),
        (10, "aa"),  (11, "E"),   (12, "ih"),  (13, "oh"),  (14, "ou"),
    };

    [MenuItem("Aivatar/Test Jaw Rotation")]
    public static string TestJawRotation()
    {
        // Find FaceMesh2 SMR and check its bones list for FACIAL_C_Jaw
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"SMRs in scene: {smrs.Length}");
        foreach (var smr in smrs)
        {
            bool hasJaw = false;
            foreach (var b in smr.bones) if (b != null && b.name.Contains("Jaw")) { hasJaw = true; break; }
            sb.AppendLine($"  '{smr.name}'  bones={smr.bones.Length}  hasJawBone={hasJaw}");
            if (hasJaw)
            {
                foreach (var b in smr.bones)
                {
                    if (b == null || !b.name.Contains("Jaw")) continue;
                    // Force-rotate the jaw 30 degrees
                    b.localRotation = b.localRotation * Quaternion.Euler(30, 0, 0);
                    sb.AppendLine($"  -> Rotated '{b.name}' by 30° on X");
                }
            }
        }

        // Also check via GameObject.Find
        var jawGO = GameObject.Find("FACIAL_C_Jaw");
        if (jawGO != null)
        {
            jawGO.transform.localRotation = jawGO.transform.localRotation * Quaternion.Euler(30, 0, 0);
            sb.AppendLine($"Also rotated GameObject.Find('FACIAL_C_Jaw') by 30° on X");
        }
        else sb.AppendLine("GameObject.Find('FACIAL_C_Jaw') = null");

        string result = sb.ToString();
        Debug.Log(result);
        return result;
    }

    [MenuItem("Aivatar/Align FaceMesh2 to Original")]
    public static string AlignFaceMesh2()
    {
        // Find the face SMR with the most bones (FaceMesh2)
        SkinnedMeshRenderer faceSMR = null;
        int maxBones = 0;
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (smr.bones.Length > maxBones) { maxBones = smr.bones.Length; faceSMR = smr; }

        if (faceSMR == null) return "FaceMesh2 SMR not found";

        // Walk all the way up to the scene root (parent == null)
        Transform faceRoot = faceSMR.transform;
        while (faceRoot.parent != null) faceRoot = faceRoot.parent;

        // Find the original static face scene root (top-level, named FaceMesh, different object)
        Transform originalRoot = null;
        foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.transform.parent != null) continue;           // top-level only
            if (go.transform == faceRoot) continue;              // not FaceMesh2 itself
            if (go.name.ToLower().Contains("facemesh")) { originalRoot = go.transform; break; }
        }

        if (originalRoot == null)
            return $"Could not find original FaceMesh root. FaceMesh2 root = '{faceRoot.name}'";

        string before = $"pos={faceRoot.position} rot={faceRoot.eulerAngles}";
        Undo.RecordObject(faceRoot, "Align FaceMesh2");
        faceRoot.position   = originalRoot.position;
        faceRoot.rotation   = originalRoot.rotation;
        faceRoot.localScale = originalRoot.localScale;
        EditorUtility.SetDirty(faceRoot);

        return $"Moved '{faceRoot.name}' to match '{originalRoot.name}' pos={originalRoot.position}  (was {before})";
    }

    [MenuItem("Aivatar/Diagnose BoneLipSync")]
    public static string DiagnoseBoneLipSync()
    {
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) return "Avatar not found";

        var bls = avatarGO.GetComponent<BoneLipSync>();
        if (bls == null) return "BoneLipSync not on Avatar";

        var speech = avatarGO.GetComponent<AzureSpeechManager>();

        return $"BoneLipSync: jaw={bls.jawBone?.name ?? "NULL"}" +
               $" lowerLip={bls.lowerLipBone?.name ?? "NULL"}" +
               $" cornerL={bls.lipCornerL?.name ?? "NULL"}" +
               $" cornerR={bls.lipCornerR?.name ?? "NULL"}" +
               $" | AzureSpeechManager.lipSyncController={(speech?.lipSyncController?.GetType().Name ?? "NULL")}";
    }

    [MenuItem("Aivatar/Diagnose MeshLipSync")]
    public static string DiagnoseMeshLipSync()
    {
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) return "Avatar not found";

        var mls = avatarGO.GetComponent<MeshLipSync>();
        if (mls == null) return "MeshLipSync not on Avatar";

        var speech = avatarGO.GetComponent<AzureSpeechManager>();

        string visemeInfo = "NULL";
        if (mls.visemeMesh != null)
            visemeInfo = $"'{mls.visemeMesh.name}' bs={mls.visemeMesh.blendShapeCount} verts={mls.visemeMesh.vertexCount}";

        return $"MeshLipSync:" +
               $"\n  faceMeshFilter={mls.faceMeshFilter?.name ?? "NULL"}" +
               $"\n  visemeMesh={visemeInfo}" +
               $"\n  AzureSpeech.lipSync={speech?.lipSyncController?.GetType().Name ?? "NULL"}";
    }

    [MenuItem("Aivatar/List Face Bones")]
    public static string ListFaceBones()
    {
        var sb = new System.Text.StringBuilder();

        // Dump all bones from every SMR in scene
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        foreach (var smr in smrs)
        {
            sb.AppendLine($"\nBones on '{smr.name}' ({smr.bones.Length}):");
            foreach (var b in smr.bones)
                if (b != null) sb.AppendLine($"  {b.name}");
        }

        // Also search the entire scene transform hierarchy for jaw/mouth/lip related bones
        sb.AppendLine("\nScene transforms containing 'jaw','mouth','lip','chin' (case-insensitive):");
        foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            string lower = go.name.ToLower();
            if (lower.Contains("jaw") || lower.Contains("mouth") || lower.Contains("lip") || lower.Contains("chin"))
                sb.AppendLine($"  {go.name}");
        }

        string result = sb.ToString();
        Debug.Log(result);
        return result;
    }

    [MenuItem("Aivatar/List SMRs in Scene")]
    public static string ListSMRs()
    {
        var sb = new System.Text.StringBuilder();

        // All SMRs in scene
        var allSMRs = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        sb.AppendLine($"Scene SMRs ({allSMRs.Length}):");
        foreach (var s in allSMRs)
            sb.AppendLine($"  '{s.name}'  bs={s.sharedMesh?.blendShapeCount ?? -1}");

        // Inspect sub-assets of both FBX files directly
        string[] fbxPaths = {
            "Assets/Models/Avatar/SKM_model4_FaceMesh.FBX",
            "Assets/Models/Avatar/SKM_model4_FaceMesh2.FBX",
        };
        foreach (string fbx in fbxPaths)
        {
            sb.AppendLine($"\nSub-asset meshes in {System.IO.Path.GetFileName(fbx)}:");
            int count = 0;
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(fbx))
            {
                if (asset is Mesh m)
                {
                    sb.AppendLine($"  '{m.name}'  bs={m.blendShapeCount}");
                    count++;
                }
            }
            if (count == 0) sb.AppendLine("  (no Mesh sub-assets found — FBX may not be imported yet)");
        }

        string result = sb.ToString();
        Debug.Log("[WireModel4] " + result);
        return result;
    }

    [MenuItem("Aivatar/Wire Model4 (Bones)")]
    public static void WireBones()
    {
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) { Debug.LogError("'Avatar' not found. Run Setup Avatar Scene first."); return; }

        // Remove old blendshape-based component if present, add BoneLipSync
        var oldLipSync = avatarGO.GetComponent<ProLipSync>();
        if (oldLipSync != null) Undo.DestroyObjectImmediate(oldLipSync);

        var boneLipSync = avatarGO.GetComponent<BoneLipSync>();
        if (boneLipSync == null)
            boneLipSync = Undo.AddComponent<BoneLipSync>(avatarGO);

        // Point AzureSpeechManager at the new controller
        var speech = avatarGO.GetComponent<AzureSpeechManager>();
        if (speech != null)
        {
            Undo.RecordObject(speech, "Wire BoneLipSync");
            speech.lipSyncController = boneLipSync;
            EditorUtility.SetDirty(speech);
        }

        // Find the skinned face SMR (the one with the most bones — the full facial rig)
        SkinnedMeshRenderer faceSMR = null;
        int maxBones = 0;
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (smr.bones.Length > maxBones) { maxBones = smr.bones.Length; faceSMR = smr; }
        }

        if (faceSMR == null) { Debug.LogError("[WireBones] No SkinnedMeshRenderer found in scene."); return; }
        Debug.Log($"[WireBones] Using bones from '{faceSMR.name}' ({faceSMR.bones.Length} bones)");

        // Look up bones by name from the SMR's own bone array (avoids finding duplicates from other hierarchies)
        boneLipSync.jawBone      = FindBoneInSMR(faceSMR, "FACIAL_C_Jaw");
        boneLipSync.lowerLipBone = FindBoneInSMR(faceSMR, "FACIAL_C_LowerLipRotation");
        boneLipSync.lipCornerL   = FindBoneInSMR(faceSMR, "FACIAL_L_LipCorner");
        boneLipSync.lipCornerR   = FindBoneInSMR(faceSMR, "FACIAL_R_LipCorner");

        Undo.RecordObject(boneLipSync, "Wire BoneLipSync");
        EditorUtility.SetDirty(boneLipSync);

        string report = $"[WireBones] jaw={boneLipSync.jawBone?.name ?? "NOT FOUND"}" +
                        $"  lowerLip={boneLipSync.lowerLipBone?.name ?? "NOT FOUND"}" +
                        $"  cornerL={boneLipSync.lipCornerL?.name ?? "NOT FOUND"}" +
                        $"  cornerR={boneLipSync.lipCornerR?.name ?? "NOT FOUND"}";
        Debug.Log(report);
        Selection.activeGameObject = avatarGO;
    }

    private static Transform FindBoneInSMR(SkinnedMeshRenderer smr, string boneName)
    {
        foreach (var b in smr.bones)
            if (b != null && b.name == boneName) return b;
        return null;
    }


    [MenuItem("Aivatar/Wire Model4 to Avatar")]
    public static void Wire()
    {
        // 1. Find Avatar + ProLipSync in scene
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) { Debug.LogError("'Avatar' GameObject not found. Run Setup Avatar Scene first."); return; }
        var lipSync = avatarGO.GetComponent<ProLipSync>();
        if (lipSync == null) { Debug.LogError("ProLipSync not found on Avatar."); return; }

        // 2. Find the face mesh SMR anywhere in the scene by name
        var head = FindSMRInScene("SKM_model4_FaceMesh");
        if (head == null) { Debug.LogError("SkinnedMeshRenderer 'SKM_model4_FaceMesh' not found in scene. Make sure the model is in the Hierarchy."); return; }

        // 4. Create VisemeMapping asset
        string assetPath = "Assets/Model4VisemeMapping.asset";
        var mapping = AssetDatabase.LoadAssetAtPath<VisemeMapping>(assetPath);
        if (mapping == null)
        {
            mapping = ScriptableObject.CreateInstance<VisemeMapping>();
            AssetDatabase.CreateAsset(mapping, assetPath);
        }

        mapping.mappings = new VisemeMapping.VisemeMap[VISEME_MAP.Length];
        for (int i = 0; i < VISEME_MAP.Length; i++)
            mapping.mappings[i] = new VisemeMapping.VisemeMap
                { azureId = VISEME_MAP[i].id, blendShapeName = VISEME_MAP[i].name };

        EditorUtility.SetDirty(mapping);
        AssetDatabase.SaveAssets();

        // 5. Wire ProLipSync
        Undo.RecordObject(lipSync, "Wire Model4 to ProLipSync");
        lipSync.faceMesh       = head;
        lipSync.mappingProfile = mapping;
        EditorUtility.SetDirty(lipSync);

        Debug.Log($"[WireModel4] Done. ProLipSync.faceMesh = {head.name}, mapping saved to {assetPath}");
        Selection.activeGameObject = avatarGO;
    }

    private static SkinnedMeshRenderer FindSMRInScene(string name)
    {
        var all = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        Debug.Log($"[WireModel4] Found {all.Length} SkinnedMeshRenderers in scene:");
        foreach (var smr in all)
            Debug.Log($"  - '{smr.name}'  blendShapes={smr.sharedMesh?.blendShapeCount ?? -1}");

        SkinnedMeshRenderer fallback = null;
        foreach (var smr in all)
        {
            if (smr.name != name) continue;
            if (smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0)
                return smr;
            fallback = smr;
        }
        return fallback;
    }
}
#endif
