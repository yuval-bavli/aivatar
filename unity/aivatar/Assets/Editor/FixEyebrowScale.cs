
using UnityEngine;
using UnityEditor;
public static class FixEyebrowScale
{
    [MenuItem("Aivatar/Fix Eyebrow Scale")]
    public static string Run()
    {
        foreach (var mr in Object.FindObjectsOfType<MeshRenderer>(true))
        {
            if (mr.gameObject.name.ToLower().Contains("brow"))
            {
                mr.enabled = true;
                // Scale to place eyebrows at ~Y=1.60 (upper face, eye level)
                mr.transform.localScale = new Vector3(0.027f, 0.027f, 0.027f);
                var newBounds = mr.bounds;
                return "Eyebrow repositioned. New bounds.center=" + newBounds.center + " extents=" + newBounds.extents;
            }
        }
        return "Not found";
    }
}
