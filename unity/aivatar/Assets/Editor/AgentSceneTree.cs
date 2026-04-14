#if UNITY_EDITOR
using UnityEngine;
using System.Text;

public static class AgentSceneTree
{
    public static string Run()
    {
        var sb = new StringBuilder();
        var roots = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
        foreach (var root in roots)
        {
            DumpHierarchy(root.transform, sb, 0, 3);
        }
        return sb.ToString();
    }

    static void DumpHierarchy(Transform t, StringBuilder sb, int depth, int maxDepth)
    {
        string indent = new string(' ', depth * 2);
        string components = "";

        var smr = t.GetComponent<SkinnedMeshRenderer>();
        if (smr != null)
            components += $" [SMR: {smr.sharedMesh?.name ?? "null"} bones={smr.bones?.Length ?? 0} blendshapes={smr.sharedMesh?.blendShapeCount ?? 0}]";

        var mr = t.GetComponent<MeshRenderer>();
        if (mr != null)
            components += " [MR]";

        var anim = t.GetComponent<Animator>();
        if (anim != null)
            components += $" [Animator]";

        var audioSrc = t.GetComponent<AudioSource>();
        if (audioSrc != null)
            components += " [AudioSource]";

        var lipSync = t.GetComponent<AnimClipLipSync>();
        if (lipSync != null)
            components += " [AnimClipLipSync]";

        var speech = t.GetComponent<AzureSpeechManager>();
        if (speech != null)
            components += " [AzureSpeechManager]";

        sb.AppendLine($"{indent}{t.name}{components}");

        if (depth < maxDepth)
        {
            for (int i = 0; i < t.childCount; i++)
                DumpHierarchy(t.GetChild(i), sb, depth + 1, maxDepth);
        }
        else if (t.childCount > 0)
        {
            sb.AppendLine($"{indent}  ... ({t.childCount} children)");
        }
    }
}
#endif
