#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class BlendShapeDump
{
    [MenuItem("Aivatar/Dump Face BlendShapes")]
    public static void Dump()
    {
        var all = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None);
        foreach (var smr in all)
        {
            var m = smr.sharedMesh;
            int verts = (m != null) ? m.vertexCount : 0;
            int n = (m != null) ? m.blendShapeCount : 0;
            Debug.Log("SMR: " + smr.name + " verts=" + verts + " blendShapes=" + n);
        }
        Debug.Log("BlendShapeDump done");
    }

    static string GetPath(Transform t)
    {
        if (t.parent == null) return t.name;
        return GetPath(t.parent) + "/" + t.name;
    }
}
#endif
