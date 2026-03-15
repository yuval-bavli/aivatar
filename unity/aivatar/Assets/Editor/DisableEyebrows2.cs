
using UnityEngine;
using UnityEditor;
public static class DisableEyebrows2
{
    [MenuItem("Aivatar/Disable Eyebrows 2")]
    public static string Run()
    {
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
            if (mr.gameObject.name.ToLower().Contains("brow"))
            { mr.enabled = false; return "Disabled: " + mr.gameObject.name; }
        return "Not found";
    }
}
