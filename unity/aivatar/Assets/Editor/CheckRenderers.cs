#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class CheckRenderers
{
    [MenuItem("Aivatar/Check All Renderers")]
    public static string Check()
    {
        var sb = new System.Text.StringBuilder();

        // Find ALL renderers in scene
        var renderers = Object.FindObjectsByType<Renderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);

        sb.AppendLine($"Total renderers: {renderers.Length}");

        foreach (var r in renderers)
        {
            string type = r.GetType().Name;
            string name = r.name;
            bool active = r.gameObject.activeInHierarchy;
            bool enabled = r.enabled;

            // Only show face-related or if it's a mesh renderer near face area
            bool isFace = name.ToLower().Contains("face") ||
                          name.ToLower().Contains("head") ||
                          name.ToLower().Contains("eye") ||
                          name.ToLower().Contains("teeth") ||
                          name.ToLower().Contains("hair") ||
                          name.ToLower().Contains("brow");

            if (isFace || type == "SkinnedMeshRenderer")
            {
                sb.AppendLine($"\n  [{type}] '{name}'  active={active}  enabled={enabled}");
                sb.AppendLine($"    path: {GetPath(r.transform)}");

                if (r is SkinnedMeshRenderer smr)
                    sb.AppendLine($"    bones={smr.bones.Length}  rootBone={smr.rootBone?.name ?? "null"}");
                if (r is MeshRenderer mr)
                {
                    var mf = mr.GetComponent<MeshFilter>();
                    if (mf != null && mf.sharedMesh != null)
                        sb.AppendLine($"    mesh: '{mf.sharedMesh.name}'  verts={mf.sharedMesh.vertexCount}");
                }
            }
        }

        // Also find MeshFilters that might have face-related names
        var mfs = Object.FindObjectsByType<MeshFilter>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        sb.AppendLine($"\n\nMeshFilters containing 'face':");
        foreach (var mf in mfs)
        {
            if (mf.name.ToLower().Contains("face") ||
                (mf.sharedMesh != null && mf.sharedMesh.name.ToLower().Contains("face")))
            {
                bool active = mf.gameObject.activeInHierarchy;
                sb.AppendLine($"  '{mf.name}' mesh='{mf.sharedMesh?.name}' active={active}");
                sb.AppendLine($"    path: {GetPath(mf.transform)}");
            }
        }

        string result = sb.ToString();
        Debug.Log("[CheckRenderers] " + result);
        return result;
    }

    static string GetPath(Transform t)
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
