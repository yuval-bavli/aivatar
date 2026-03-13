#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class WireModel2
{
    // Azure viseme ID → blendshape name (matches both AvatarHead and AvatarTeethLower)
    private static readonly (int id, string name)[] VISEME_MAP =
    {
        ( 0, "sil"), ( 1, "PP"),  ( 2, "FF"),  ( 3, "TH"),  ( 4, "DD"),
        ( 5, "kk"),  ( 6, "CH"),  ( 7, "SS"),  ( 8, "nn"),  ( 9, "RR"),
        (10, "aa"),  (11, "E"),   (12, "ih"),  (13, "oh"),  (14, "ou"),
    };

    [MenuItem("Aivatar/Wire Model2 to Avatar")]
    public static void Wire()
    {
        // 1. Find Avatar + ProLipSync in scene
        var avatarGO = GameObject.Find("Avatar");
        if (avatarGO == null) { Debug.LogError("'Avatar' GameObject not found. Run Setup Avatar Scene first."); return; }
        var lipSync = avatarGO.GetComponent<ProLipSync>();
        if (lipSync == null) { Debug.LogError("ProLipSync not found on Avatar."); return; }

        // 2. Find model2 in scene (top-level or child)
        var model2GO = GameObject.Find("model2_embedded");
        if (model2GO == null) { Debug.LogError("'model2_embedded' not found in scene. Drag model2_embedded into the Hierarchy first."); return; }

        // 3. Get AvatarHead — has all 15 viseme blendshapes
        var head = FindSMR(model2GO, "AvatarHead");
        if (head == null) { Debug.LogError("SkinnedMeshRenderer 'AvatarHead' not found under model2."); return; }

        // 4. Create VisemeMapping asset
        string assetPath = "Assets/Model2VisemeMapping.asset";
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
        Undo.RecordObject(lipSync, "Wire Model2 to ProLipSync");
        lipSync.faceMesh       = head;
        lipSync.mappingProfile = mapping;
        EditorUtility.SetDirty(lipSync);

        Debug.Log($"[WireModel2] Done. ProLipSync.faceMesh = {head.name}, mapping saved to {assetPath}");
        Selection.activeGameObject = avatarGO;
    }

    private static SkinnedMeshRenderer FindSMR(GameObject root, string name)
    {
        foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>())
            if (smr.name == name) return smr;
        return null;
    }
}
#endif
