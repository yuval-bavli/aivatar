using UnityEngine;
using UnityEditor;
using System.Text;

public static class FixEyebrowPosition
{
    public static string Run()
    {
        var sb = new StringBuilder();

        // Find face renderer
        Renderer faceRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name == "SKM_model4_FaceMesh") { faceRenderer = r; break; }
        }

        if (faceRenderer == null)
            return "ERROR: face mesh not found";

        Bounds fb = faceRenderer.bounds;
        sb.AppendLine($"Face bounds: center={fb.center} size={fb.size}");
        sb.AppendLine($"Face Z: min={fb.min.z:F3} max={fb.max.z:F3}");

        // Eyebrow should sit IN FRONT OF the face (max Z + small offset toward camera)
        float browY = fb.min.y + (fb.max.y - fb.min.y) * 0.82f;
        float browZ = fb.max.z + 0.008f;  // 8mm in front of face surface
        float browX = fb.center.x;

        sb.AppendLine($"Target: Y={browY:F3}, Z={browZ:F3}");

        // Find eyebrow renderer
        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return sb.ToString() + "\nERROR: no eyebrow renderer";

        sb.AppendLine($"Brow: {browRenderer.gameObject.name}");

        browRenderer.enabled = true;
        browRenderer.gameObject.SetActive(true);

        Transform t = browRenderer.transform;
        t.position = new Vector3(browX, browY, browZ);
        t.localScale = new Vector3(0.022f, 0.022f, 0.022f);
        t.rotation = Quaternion.identity;  // reset any rotation

        sb.AppendLine($"Set pos={t.position} scale={t.localScale}");

        EditorUtility.SetDirty(browRenderer.gameObject);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(t.gameObject.scene);
        return sb.ToString() + "\nDone";
    }
}
