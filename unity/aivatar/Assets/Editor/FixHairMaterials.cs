using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

/// FixHairMaterials — assigns haircut.mat to all slots of the hair mesh renderer
public static class FixHairMaterials
{
    [MenuItem("Aivatar/Fix Hair Materials")]
    public static string Run()
    {
        var hairMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Models/Avatar/Materials/haircut.mat");
        if (hairMat == null) return "ERROR: haircut.mat not found";

        int fixedRenderers = 0;
        int fixedSlots = 0;

        // Fix SkinnedMeshRenderers
        foreach (var r in GameObject.FindObjectsOfType<SkinnedMeshRenderer>(true))
        {
            if (r.gameObject.name.Contains("Hair_M_BobMessy"))
            {
                var mats = new Material[r.sharedMaterials.Length];
                for (int i = 0; i < mats.Length; i++) mats[i] = hairMat;
                r.sharedMaterials = mats;
                EditorUtility.SetDirty(r);
                fixedRenderers++;
                fixedSlots += mats.Length;
            }
        }

        // Fix MeshRenderers
        foreach (var r in GameObject.FindObjectsOfType<MeshRenderer>(true))
        {
            if (r.gameObject.name.Contains("Hair_M_BobMessy"))
            {
                var mats = new Material[r.sharedMaterials.Length];
                for (int i = 0; i < mats.Length; i++) mats[i] = hairMat;
                r.sharedMaterials = mats;
                EditorUtility.SetDirty(r);
                fixedRenderers++;
                fixedSlots += mats.Length;
            }
        }

        EditorSceneManager.SaveOpenScenes();
        return $"FixHairMaterials: fixed {fixedRenderers} renderers ({fixedSlots} material slots), scene saved";
    }
}
