using UnityEngine;
using UnityEditor;
using System.Text;

public static class OutputDiagnostics
{
    // Returns a string that gets written to agent_result.txt by the bridge
    public static string Run()
    {
        var sb = new StringBuilder();
        var renderers = Resources.FindObjectsOfTypeAll<Renderer>();
        sb.AppendLine($"Total renderers: {renderers.Length}");
        foreach (var r in renderers)
        {
            if (r.hideFlags != HideFlags.None) continue;
            string mats = "";
            foreach (var m in r.sharedMaterials)
                mats += (m != null ? m.name : "NULL") + "|";
            // Only output interesting ones (not lights/cameras)
            sb.AppendLine($"{r.gameObject.name} | en={r.enabled} | active={r.gameObject.activeInHierarchy} | [{mats}]");
        }
        return sb.ToString();
    }
}
