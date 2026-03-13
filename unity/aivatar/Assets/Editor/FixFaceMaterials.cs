using UnityEngine;
using UnityEditor;

public class FixFaceMaterials
{
    [MenuItem("Aivatar/Restore Face Materials")]
    static void RestoreFaceMaterials()
    {
        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (!path.Contains("SKM_model4_FaceMesh")) continue;

            string basePath = "Assets/Models/Avatar/Materials/";
            string[] matPaths = new string[]
            {
                basePath + "MI_Face_Skin_Baked_LOD1_VT.mat",
                basePath + "M_Hide.mat",
                basePath + "MI_Face_LacrimalFluid.mat",
                basePath + "MI_EyeR_Baked.mat",
                basePath + "MI_Face_EyeShell.mat",
                basePath + "MI_EyeL_Baked.mat",
                basePath + "M_Hide_6.mat",
                basePath + "MI_Teeth_Baked.mat",
                basePath + "MI_Face_EyelashesHiLODs.mat",
            };

            Material[] mats = new Material[matPaths.Length];
            for (int i = 0; i < matPaths.Length; i++)
            {
                mats[i] = AssetDatabase.LoadAssetAtPath<Material>(matPaths[i]);
                if (mats[i] == null)
                    Debug.LogError($"Failed to load material: {matPaths[i]}");
            }

            r.sharedMaterials = mats;
            EditorUtility.SetDirty(r);
            Debug.Log("Face materials restored successfully!");
            return;
        }
        Debug.LogWarning("Face mesh not found!");
    }

    [MenuItem("Aivatar/Add Eyeballs to Model4")]
    static void AddEyeballs()
    {
        // Find the face mesh to position eyeballs relative to it
        Transform faceMeshTransform = null;
        var meshRenderers = Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
        foreach (var r in meshRenderers)
        {
            string path = GetPath(r.transform);
            if (path.Contains("SKM_model4_FaceMesh/SKM_model4_FaceMesh"))
            {
                faceMeshTransform = r.transform;
                break;
            }
        }

        if (faceMeshTransform == null)
        {
            Debug.LogError("Face mesh not found!");
            return;
        }

        // Remove existing eyeballs if any
        var existing = faceMeshTransform.parent.Find("Eyeball_L");
        if (existing != null) Object.DestroyImmediate(existing.gameObject);
        existing = faceMeshTransform.parent.Find("Eyeball_R");
        if (existing != null) Object.DestroyImmediate(existing.gameObject);

        // Load eye materials
        var matL = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_EyeL_Baked.mat");
        var matR = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/MI_EyeR_Baked.mat");

        // Create eyeball spheres
        // MetaHuman eye positions are roughly at these offsets from the face mesh root
        // The face mesh bounds center is at (0, -0.03, 1.49)
        float eyeY = 1.52f;  // slightly above face center
        float eyeX = 0.032f; // horizontal offset from center
        float eyeZ = -0.015f; // depth
        float scale = 0.025f; // eyeball radius

        var eyeL = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        eyeL.name = "Eyeball_L";
        eyeL.transform.SetParent(faceMeshTransform.parent);
        eyeL.transform.localPosition = new Vector3(-eyeX, eyeZ, eyeY);
        eyeL.transform.localScale = Vector3.one * scale;
        eyeL.GetComponent<MeshRenderer>().sharedMaterial = matL;
        // Remove collider - not needed
        Object.DestroyImmediate(eyeL.GetComponent<Collider>());

        var eyeR = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        eyeR.name = "Eyeball_R";
        eyeR.transform.SetParent(faceMeshTransform.parent);
        eyeR.transform.localPosition = new Vector3(eyeX, eyeZ, eyeY);
        eyeR.transform.localScale = Vector3.one * scale;
        eyeR.GetComponent<MeshRenderer>().sharedMaterial = matR;
        Object.DestroyImmediate(eyeR.GetComponent<Collider>());

        EditorUtility.SetDirty(eyeL);
        EditorUtility.SetDirty(eyeR);

        Debug.Log("Eyeballs added! Adjust position/scale in the Scene view if needed.");
        Selection.activeGameObject = eyeL;
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null) { t = t.parent; path = t.name + "/" + path; }
        return path;
    }
}
