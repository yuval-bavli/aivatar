#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class BlendShapeInspector
{
    [MenuItem("Aivatar/Print BlendShapes on Selected")]
    public static void PrintBlendShapes()
    {
        var go = Selection.activeGameObject;
        if (go == null) { Debug.LogError("Select a GameObject first."); return; }

        var skinned = go.GetComponentsInChildren<SkinnedMeshRenderer>();
        var plain   = go.GetComponentsInChildren<MeshRenderer>();

        if (skinned.Length == 0 && plain.Length == 0)
        {
            Debug.LogError($"No renderers found on '{go.name}'. " +
                           "Make sure you selected the instance in the Hierarchy (not the Project panel).");
            return;
        }

        if (skinned.Length == 0)
        {
            Debug.LogWarning($"'{go.name}' has {plain.Length} MeshRenderer(s) but NO SkinnedMeshRenderer. " +
                             "Blendshape-based lip sync requires a skinned mesh. " +
                             "The model may not have been exported with blend shapes.");
            foreach (var mr in plain)
                Debug.Log($"  MeshRenderer: {mr.name}");
            return;
        }

        foreach (var smr in skinned)
        {
            int count = smr.sharedMesh.blendShapeCount;
            Debug.Log($"--- SkinnedMeshRenderer: {smr.name} ({count} blendshapes) ---");
            if (count == 0)
                Debug.LogWarning($"  (no blendshapes — model needs to be exported with facial morphs)");
            for (int i = 0; i < count; i++)
                Debug.Log($"  [{i}] {smr.sharedMesh.GetBlendShapeName(i)}");
        }
    }
}
#endif
