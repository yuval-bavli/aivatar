using UnityEngine;
using UnityEditor;
using System.Text;

public static class DiagnoseEyebrowWorld
{
    public static string Run()
    {
        var sb = new StringBuilder();

        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer found";

        Transform t = browRenderer.transform;
        Mesh mesh = null;
        var meshFilter = browRenderer.GetComponent<MeshFilter>();
        if (meshFilter != null) mesh = meshFilter.sharedMesh;
        var smr = browRenderer as SkinnedMeshRenderer;
        if (smr != null) mesh = smr.sharedMesh;

        sb.AppendLine($"=== Eyebrow: {browRenderer.gameObject.name} ===");
        sb.AppendLine($"Pivot pos: {t.position}");
        sb.AppendLine($"Bounds (world): center={browRenderer.bounds.center} size={browRenderer.bounds.size}");

        // Find face mesh transform position
        Renderer faceSMR = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name == "SKM_model4_FaceMesh") { faceSMR = r; break; }
        }
        if (faceSMR != null)
        {
            sb.AppendLine($"=== Face mesh ===");
            sb.AppendLine($"Face transform pos: {faceSMR.transform.position}");
            sb.AppendLine($"Face bounds: center={faceSMR.bounds.center} size={faceSMR.bounds.size}");
        }

        // Check camera frustum
        Camera cam = Camera.main;
        if (cam == null && SceneView.lastActiveSceneView != null)
            cam = SceneView.lastActiveSceneView.camera;
        if (cam != null)
        {
            sb.AppendLine($"Camera: pos={cam.transform.position} forward={cam.transform.forward:F3}");
            Plane[] planes = GeometryUtility.CalculateFrustumPlanes(cam);
            bool visible = GeometryUtility.TestPlanesAABB(planes, browRenderer.bounds);
            sb.AppendLine($"In camera frustum: {visible}");
        }

        if (mesh != null)
        {
            Vector3[] verts = mesh.vertices;
            sb.AppendLine($"Mesh verts: {verts.Length}");
            // Sample world-space vertex positions
            int step = Mathf.Max(1, verts.Length / 8);
            sb.AppendLine("Sample world-space verts:");
            for (int i = 0; i < verts.Length; i += step)
            {
                Vector3 w = t.TransformPoint(verts[i]);
                sb.AppendLine($"  v[{i}] local={verts[i]:F3} -> world={w:F3}");
            }
        }

        return sb.ToString();
    }

    // Sets the eyebrow pivot to the same origin as the face mesh transform
    public static string AlignTofacePivot()
    {
        var sb = new StringBuilder();

        Renderer browRenderer = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name.ToLower().Contains("eyebrow") || r.gameObject.name.ToLower().Contains("brow"))
            { browRenderer = r; break; }
        }
        if (browRenderer == null) return "ERROR: no eyebrow renderer";

        Renderer faceSMR = null;
        foreach (var r in Resources.FindObjectsOfTypeAll<Renderer>())
        {
            if (r.hideFlags != HideFlags.None) continue;
            if (r.gameObject.name == "SKM_model4_FaceMesh") { faceSMR = r; break; }
        }
        if (faceSMR == null) return "ERROR: face mesh not found";

        Transform browT = browRenderer.transform;
        Transform faceT = faceSMR.transform;

        sb.AppendLine($"Face pivot: {faceT.position}, scale: {faceT.localScale}");

        // Set eyebrow pivot to face pivot, same scale
        // But adjust Z so mesh verts land in front of face surface
        // Mesh local Z ~63, face front Z ~faceBounds.min.z
        // world_vert_z = face_pivot_z + 63 * scale_z
        // We want world_vert_z = faceBounds.min.z - 0.01 (just in front)
        float targetZ = faceSMR.bounds.min.z - 0.01f;
        float localMeshZ = 63.0f;
        float scaleZ = faceT.localScale.z != 0 ? faceT.localScale.z : 0.02f;
        float pivotZ = targetZ - localMeshZ * scaleZ;

        // Also get face mesh local Y center to figure out eyebrow Y offset
        // The face mesh bounds center in world = face_pivot + local_center * scale
        // So local_center_y = (bounds.center.y - pivot.y) / scale.y
        float scaleY = faceT.localScale.y != 0 ? faceT.localScale.y : 0.02f;
        float faceLocalCenterY = (faceSMR.bounds.center.y - faceT.position.y) / scaleY;
        sb.AppendLine($"Face local center Y: {faceLocalCenterY:F3}, scale: {scaleZ}");

        // Use same X/Y as face pivot
        browT.position = new Vector3(faceT.position.x, faceT.position.y, pivotZ);
        browT.localScale = faceT.localScale;
        browT.rotation = faceT.rotation;

        browRenderer.enabled = true;
        browRenderer.gameObject.SetActive(true);
        EditorUtility.SetDirty(browRenderer.gameObject);
        AssetDatabase.SaveAssets();

        sb.AppendLine($"Eyebrow pivot set to: {browT.position}");
        sb.AppendLine($"Target world vert Z: {targetZ:F3}");
        sb.AppendLine($"Bounds: center={browRenderer.bounds.center} size={browRenderer.bounds.size}");
        return sb.ToString();
    }
}
