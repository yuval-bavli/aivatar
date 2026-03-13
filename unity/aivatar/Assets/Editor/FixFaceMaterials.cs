using UnityEngine;
using UnityEditor;

public class FixFaceMaterials
{
    [MenuItem("Aivatar/Restore Face Materials")]
    static void RestoreFaceMaterials()
    {
        string basePath = "Assets/Models/Avatar/Materials/";
        string[] matPaths = new string[]
        {
            basePath + "MI_Face_Skin_Baked_LOD1_VT.mat",
            basePath + "M_Hide.mat",
            basePath + "MI_Face_LacrimalFluid.mat",
            basePath + "MI_EyeR_Baked.mat",
            basePath + "MI_EyeL_Baked.mat",
            basePath + "MI_Face_EyeShell.mat",
            basePath + "M_Hide_6.mat",
            basePath + "MI_Teeth_Baked.mat",
            basePath + "MI_Face_EyelashesHiLODs.mat",
        };

        // Force reimport all materials from disk to discard in-memory corruption
        Debug.Log("Reimporting all face materials from disk...");
        foreach (string p in matPaths)
        {
            AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
        }

        Material[] mats = new Material[matPaths.Length];
        for (int i = 0; i < matPaths.Length; i++)
        {
            mats[i] = AssetDatabase.LoadAssetAtPath<Material>(matPaths[i]);
            if (mats[i] == null)
                Debug.LogError($"Failed to load material: {matPaths[i]}");
        }

        // Search all renderer types (MeshRenderer and SkinnedMeshRenderer)
        foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
        {
            string path = GetPath(r.transform);
            if (!path.Contains("SKM_model4_FaceMesh")) continue;

            r.sharedMaterials = mats;
            EditorUtility.SetDirty(r);
            Debug.Log($"Face materials restored on '{r.gameObject.name}' ({r.GetType().Name})!");
            return;
        }
        Debug.LogWarning("Face mesh not found! Searched all Renderers for 'SKM_model4_FaceMesh'.");
    }

    [MenuItem("Aivatar/Add Eyeballs to Model4")]
    static void AddEyeballs()
    {
        // Find the face mesh renderer
        MeshFilter faceMeshFilter = null;
        MeshRenderer faceRenderer = null;
        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (path.Contains("SKM_model4_FaceMesh/SKM_model4_FaceMesh"))
            {
                faceRenderer = r;
                faceMeshFilter = r.GetComponent<MeshFilter>();
                break;
            }
        }

        if (faceMeshFilter == null || faceMeshFilter.sharedMesh == null)
        {
            Debug.LogError("Face mesh not found!");
            return;
        }

        Transform parent = faceRenderer.transform.parent;

        // Remove existing eyeballs if any
        for (int i = parent.childCount - 1; i >= 0; i--)
        {
            var child = parent.GetChild(i);
            if (child.name.StartsWith("Eyeball_"))
                Object.DestroyImmediate(child.gameObject);
        }

        // Read the mesh to find eye submesh centers
        // After our swaps: slot 3 = right eye, slot 5 = left eye
        var mesh = faceMeshFilter.sharedMesh;
        var vertices = mesh.vertices;

        Vector3 eyeLCenter = GetSubMeshCenter(mesh, vertices, 5); // left eye
        Vector3 eyeRCenter = GetSubMeshCenter(mesh, vertices, 3); // right eye

        Debug.Log($"Left eye center (local): {eyeLCenter}");
        Debug.Log($"Right eye center (local): {eyeRCenter}");

        // Convert from mesh local space to world space
        Vector3 eyeLWorld = faceRenderer.transform.TransformPoint(eyeLCenter);
        Vector3 eyeRWorld = faceRenderer.transform.TransformPoint(eyeRCenter);

        // Estimate eyeball size from the submesh bounding box
        float eyeSize = GetSubMeshRadius(mesh, vertices, 5, eyeLCenter) * 0.4f;
        float halfEye = eyeSize * 0.5f;

        // The iris disc sits on the front of the eyeball — push the sphere center
        // backward (into the skull) by ~half the sphere radius so the iris aligns
        // with the front surface. Also nudge each eye outward (away from nose).
        // Compute face forward/right from the two eye positions.
        Vector3 midpoint = (eyeLWorld + eyeRWorld) * 0.5f;
        Vector3 rightDir = (eyeRWorld - eyeLWorld).normalized; // left-to-right
        Vector3 upDir = parent.up;
        Vector3 forwardDir = Vector3.Cross(rightDir, upDir).normalized; // face forward

        // Push back into socket, outward from nose, and slightly up
        eyeLWorld += -forwardDir * halfEye * 1.0f - rightDir * halfEye * 1.2f + upDir * halfEye * 0.5f;
        eyeRWorld += -forwardDir * halfEye * 1.0f + rightDir * halfEye * 1.2f + upDir * halfEye * 0.5f;

        Debug.Log($"Left eye (world, adjusted): {eyeLWorld}");
        Debug.Log($"Right eye (world, adjusted): {eyeRWorld}");
        Debug.Log($"Eye sphere diameter: {eyeSize}, forward: {forwardDir}");

        // Load eye materials
        var matL = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_EyeL_Baked.mat");
        var matR = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_EyeR_Baked.mat");

        // Create eyeball spheres
        var eyeL = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        eyeL.name = "Eyeball_L";
        eyeL.transform.SetParent(parent);
        eyeL.transform.position = eyeLWorld;
        eyeL.transform.localScale = Vector3.one * eyeSize;
        eyeL.GetComponent<MeshRenderer>().sharedMaterial = matL;
        Object.DestroyImmediate(eyeL.GetComponent<Collider>());

        var eyeR = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        eyeR.name = "Eyeball_R";
        eyeR.transform.SetParent(parent);
        eyeR.transform.position = eyeRWorld;
        eyeR.transform.localScale = Vector3.one * eyeSize;
        eyeR.GetComponent<MeshRenderer>().sharedMaterial = matR;
        Object.DestroyImmediate(eyeR.GetComponent<Collider>());

        EditorUtility.SetDirty(eyeL);
        EditorUtility.SetDirty(eyeR);

        Debug.Log("Eyeballs added at mesh-derived positions!");
        Selection.activeGameObject = eyeL;
    }

    static Vector3 GetSubMeshCenter(Mesh mesh, Vector3[] vertices, int subMeshIndex)
    {
        var subMesh = mesh.GetSubMesh(subMeshIndex);
        var indices = mesh.GetIndices(subMeshIndex);
        Vector3 sum = Vector3.zero;
        var uniqueVerts = new System.Collections.Generic.HashSet<int>();
        foreach (int idx in indices)
            uniqueVerts.Add(idx);

        foreach (int idx in uniqueVerts)
            sum += vertices[idx];

        return sum / uniqueVerts.Count;
    }

    static float GetSubMeshRadius(Mesh mesh, Vector3[] vertices, int subMeshIndex, Vector3 center)
    {
        var indices = mesh.GetIndices(subMeshIndex);
        float maxDist = 0;
        var uniqueVerts = new System.Collections.Generic.HashSet<int>();
        foreach (int idx in indices)
            uniqueVerts.Add(idx);

        foreach (int idx in uniqueVerts)
        {
            float dist = Vector3.Distance(vertices[idx], center);
            if (dist > maxDist) maxDist = dist;
        }
        return maxDist;
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null) { t = t.parent; path = t.name + "/" + path; }
        return path;
    }
}
