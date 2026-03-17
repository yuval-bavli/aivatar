using UnityEngine;
using UnityEditor;
using System.Text;
using System.Collections.Generic;

public static class InspectHead {
    public static string Run() {
        StringBuilder sb = new StringBuilder();
        var allTransforms = Resources.FindObjectsOfTypeAll<Transform>();
        
        sb.AppendLine("--- Objects with 'FaceMesh' or 'brow' ---");
        foreach (var t in allTransforms) {
            // Skip assets, only scene objects
            if (!t.gameObject.scene.IsValid()) continue;
            
            string name = t.name.ToLower();
            if (name.Contains("facemesh") || name.Contains("brow") || name.Contains("lash")) {
                // Build path
                string path = t.name;
                Transform p = t.parent;
                while (p != null) {
                    path = p.name + "/" + path;
                    p = p.parent;
                }
                
                sb.AppendLine($"Path: {path} (Active: {t.gameObject.activeInHierarchy})");
                
                var smr = t.GetComponent<SkinnedMeshRenderer>();
                if (smr != null) {
                    string matNames = "";
                    if (smr.sharedMaterials != null) {
                        foreach (var m in smr.sharedMaterials) {
                            if (m != null) matNames += m.name + ", ";
                        }
                    }
                    sb.AppendLine($"  Has SMR, Enabled: {smr.enabled}, Materials: {matNames}");
                }
            }
        }
        return sb.ToString();
    }
}
