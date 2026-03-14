using UnityEngine;
using UnityEditor;

public static class FixEyebrowDepth
{
    [MenuItem("Aivatar/Fix Eyebrow Depth")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();

        var browGO = FindRendererByName("Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        var faceGO = FindRendererByName("SKM_model4_FaceMesh");

        if (browGO == null || faceGO == null)
        {
            log.AppendLine($"ERROR: browGO={browGO != null}, faceGO={faceGO != null}");
            return log.ToString();
        }

        var faceRenderer = faceGO.GetComponent<Renderer>();
        var browRenderer = browGO.GetComponent<Renderer>();

        // Target: eyebrows should be just in front of face surface
        // Face front Z ≈ face center Z - half face Z size
        float faceFrontZ = faceRenderer.bounds.center.z - faceRenderer.bounds.extents.z;
        log.AppendLine($"Face front Z: {faceFrontZ}");
        log.AppendLine($"Current eyebrow center Z: {browRenderer.bounds.center.z}");

        // We want eyebrow center at face front Z - 0.005 (5mm in front)
        float targetZ = faceFrontZ - 0.005f;

        // Current Z offset needed
        float zOffset = targetZ - browRenderer.bounds.center.z;
        log.AppendLine($"Z offset needed: {zOffset}");

        // Convert world Z offset to local Y offset (from mapping: local -Y ≈ world -Z)
        // More precisely, use parent's InverseTransformDirection
        Vector3 worldOffset = new Vector3(0, 0, zOffset);
        Vector3 localOffset = browGO.transform.parent.InverseTransformDirection(worldOffset);
        log.AppendLine($"Local offset: {localOffset}");

        browGO.transform.localPosition += localOffset;
        EditorUtility.SetDirty(browGO);

        log.AppendLine($"New local pos: {browGO.transform.localPosition}");
        log.AppendLine($"New world bounds: center={browRenderer.bounds.center}, size={browRenderer.bounds.size}");

        // Keep solid red for testing
        AssetDatabase.SaveAssets();
        string result = log.ToString();
        Debug.Log(result);
        return result;
    }

    static GameObject FindRendererByName(string name)
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
        {
            if (r.gameObject.name == name) return r.gameObject;
        }
        return null;
    }
}
