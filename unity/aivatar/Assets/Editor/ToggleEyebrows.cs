
using UnityEngine;
using UnityEditor;

public static class ToggleEyebrows
{
    [MenuItem("Aivatar/Toggle Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        var allMeshR = Object.FindObjectsOfType<MeshRenderer>(true);
        foreach (var mr in allMeshR)
        {
            if (mr.gameObject.name.ToLower().Contains("brow"))
            {
                mr.enabled = false;
                log.AppendLine("Disabled: " + mr.gameObject.name);
            }
        }
        return log.ToString();
    }
}
