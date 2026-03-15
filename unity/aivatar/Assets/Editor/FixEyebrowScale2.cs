
using UnityEngine;
using UnityEditor;
public static class FixEyebrowScale2
{
    [MenuItem("Aivatar/Fix Eyebrow Scale 2")]
    public static string Run()
    {
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
            if (mr.gameObject.name.ToLower().Contains("brow"))
            {
                mr.transform.localScale = new Vector3(0.024f, 0.024f, 0.024f);
                return "scale=0.024 -> bounds.center=" + mr.bounds.center + " Yrange=[" + (mr.bounds.center.y - mr.bounds.extents.y) + "," + (mr.bounds.center.y + mr.bounds.extents.y) + "]";
            }
        return "Not found";
    }
}
