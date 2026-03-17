#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;

public class FixFaceMaterials
{
    [MenuItem("Aivatar/Restore Face Materials")]
    public static string RestoreFaceMaterials()
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
            AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);

        Material[] mats = new Material[matPaths.Length];
        for (int i = 0; i < matPaths.Length; i++)
        {
            mats[i] = AssetDatabase.LoadAssetAtPath<Material>(matPaths[i]);
            if (mats[i] == null)
                Debug.LogError($"Failed to load material: {matPaths[i]}");
        }

        // Target the SkinnedMeshRenderer (FaceMesh2) specifically
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (!smr.name.Contains("SKM_model4_FaceMesh")) continue;

            Undo.RecordObject(smr, "Restore Face Materials");
            smr.sharedMaterials = mats;
            EditorUtility.SetDirty(smr);
            string msg = $"Face materials restored on '{smr.gameObject.name}' (SkinnedMeshRenderer)!";
            Debug.Log(msg);
            return msg;
        }

        return "SkinnedMeshRenderer with 'SKM_model4_FaceMesh' not found!";
    }

    static string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null) { t = t.parent; path = t.name + "/" + path; }
        return path;
    }
}
#endif
