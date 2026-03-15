
using UnityEngine;
using UnityEditor;

public static class DiagEyebrows
{
    [MenuItem("Aivatar/Diag Eyebrows")]
    public static string Run()
    {
        var log = new System.Text.StringBuilder();
        var allMeshR = Object.FindObjectsOfType<MeshRenderer>(true);
        foreach (var mr in allMeshR)
        {
            string n = mr.gameObject.name.ToLower();
            if (n.Contains("brow") || n.Contains("eyebrow"))
            {
                log.AppendLine("Name: " + mr.gameObject.name);
                log.AppendLine("Enabled: " + mr.enabled);
                log.AppendLine("Bounds: " + mr.bounds);
                if (mr.sharedMaterial != null)
                {
                    log.AppendLine("Material: " + mr.sharedMaterial.name);
                    log.AppendLine("Shader: " + mr.sharedMaterial.shader.name);
                    var tex = mr.sharedMaterial.mainTexture;
                    log.AppendLine("Texture: " + (tex != null ? tex.name : "null") + (tex != null ? " (" + tex.width + "x" + tex.height + ")" : ""));
                    log.AppendLine("_Cutoff: " + mr.sharedMaterial.GetFloat("_Cutoff"));
                    log.AppendLine("_AlphaClip: " + mr.sharedMaterial.GetFloat("_AlphaClip"));
                }
                var mesh = mr.GetComponent<MeshFilter>();
                if (mesh != null && mesh.sharedMesh != null)
                    log.AppendLine("Mesh verts: " + mesh.sharedMesh.vertexCount + " tris: " + (mesh.sharedMesh.triangles.Length/3));
            }
        }
        return log.ToString();
    }
}
