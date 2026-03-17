using UnityEngine;
using UnityEditor;

public static class TransferEyebrows {
    public static string Run() {
        var oldBrow = GameObject.Find("SKM_model4_BodyMesh/SKM_model4_FaceMesh/Eyebrows_M_Natural_CardsMesh_Group0_LOD0");
        if (oldBrow == null) return "Old eyebrows not found";
        
        var newHeadParent = GameObject.Find("SKM_model4_FaceMesh2/SKM_model4_FaceMesh");
        if (newHeadParent == null) return "New head not found";
        
        // Ensure no duplicates
        var existingNewBrow = newHeadParent.transform.Find("Eyebrows_M_Natural_CardsMesh_Group0_LOD0_Copied");
        if (existingNewBrow != null) {
            Object.DestroyImmediate(existingNewBrow.gameObject);
        }
        
        // Copy GameObject
        var newBrowGO = Object.Instantiate(oldBrow);
        newBrowGO.name = "Eyebrows_M_Natural_CardsMesh_Group0_LOD0_Copied";
        newBrowGO.transform.SetParent(newHeadParent.transform, false);
        
        // Fix Material on MeshRenderer
        var mr = newBrowGO.GetComponent<MeshRenderer>();
        if (mr != null) {
            var browMat = mr.sharedMaterial;
            if (browMat != null) {
                browMat.SetFloat("_AlphaClip", 1f);
                browMat.SetFloat("_Cutoff", 0.3f);
                browMat.SetFloat("_Cull", (float)UnityEngine.Rendering.CullMode.Off);
                browMat.SetFloat("_ZWrite", 1f);
                browMat.SetFloat("_Surface", 0f);
                browMat.SetFloat("_Smoothness", 0.15f);
                browMat.EnableKeyword("_ALPHATEST_ON");
                browMat.renderQueue = 2451;
                browMat.SetOverrideTag("RenderType", "TransparentCutout");
                EditorUtility.SetDirty(browMat);
            }
            return "Eyebrows successfully copied as MeshRenderer.";
        }
        
        return "Eyebrows copied but no MeshRenderer found.";
    }
}
