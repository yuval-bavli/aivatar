#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class CheckEyebrows
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        // Find all MeshRenderers with Eyebrows in name
        var allMRs = Object.FindObjectsByType<MeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        sb.AppendLine("=== MeshRenderers with 'Eyebrow' ===");
        foreach (var mr in allMRs)
        {
            if (mr.name.Contains("Eyebrow") || mr.name.Contains("eyebrow"))
            {
                string path = GetPath(mr.transform);
                sb.AppendLine($"'{mr.name}' active={mr.gameObject.activeInHierarchy} path={path}");
                for (int i = 0; i < mr.sharedMaterials.Length; i++)
                {
                    var mat = mr.sharedMaterials[i];
                    sb.AppendLine($"  mat[{i}] '{mat?.name ?? "NULL"}' shader={mat?.shader?.name ?? "?"}");
                }
            }
        }

        // Also check if viseme_animation has any eyebrow children
        sb.AppendLine("\n=== viseme_animation children with 'Eyebrow' ===");
        foreach (var go in Object.FindObjectsByType<GameObject>(
            FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (go.name == "viseme_animation" && go.transform.parent == null)
            {
                SearchChildren(go.transform, "Eyebrow", sb, 0);
                break;
            }
        }

        return sb.ToString();
    }

    private static void SearchChildren(Transform t, string search, System.Text.StringBuilder sb, int depth)
    {
        if (t.name.Contains(search))
            sb.AppendLine($"{'|' + new string('-', depth)} {t.name} active={t.gameObject.activeSelf}");
        foreach (Transform child in t)
            SearchChildren(child, search, sb, depth + 1);
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
