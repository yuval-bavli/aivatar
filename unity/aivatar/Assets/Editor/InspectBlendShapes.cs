using UnityEngine;
using UnityEditor;
using System.Text;
using System.Linq;

public class InspectBlendShapes
{
    public static string Run()
    {
        var sb = new StringBuilder();
        string[] paths = new[]
        {
            "Assets/Models/Avatar/SKM_model4_FaceMesh.FBX",
            "Assets/Models/Avatar/SKM_model4_FaceMesh2.FBX",
            "Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX",
        };

        foreach (var path in paths)
        {
            sb.AppendLine($"=== {path} ===");
            var objs = AssetDatabase.LoadAllAssetsAtPath(path);
            if (objs == null || objs.Length == 0)
            {
                sb.AppendLine("  NOT FOUND or empty");
                continue;
            }

            int meshCount = 0, clipCount = 0;
            foreach (var obj in objs)
            {
                if (obj is Mesh mesh)
                {
                    meshCount++;
                    sb.AppendLine($"  Mesh '{mesh.name}': verts={mesh.vertexCount}, blendShapes={mesh.blendShapeCount}");
                }
                else if (obj is AnimationClip clip)
                {
                    clipCount++;
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    sb.AppendLine($"  Clip '{clip.name}': len={clip.length}s, curves={bindings.Length}");
                    foreach (var b in bindings.Take(10))
                        sb.AppendLine($"    {b.path}/{b.propertyName}");
                    if (bindings.Length > 10)
                        sb.AppendLine($"    ... +{bindings.Length - 10} more");
                }
            }
            sb.AppendLine($"  Total: {meshCount} meshes, {clipCount} clips, {objs.Length} assets");
        }

        // List facial bones from scene
        sb.AppendLine("=== Facial Bones (FACIAL_*) on scene SMRs ===");
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (smr.bones == null) continue;
            var facialBones = smr.bones
                .Where(b => b != null && b.name.StartsWith("FACIAL_"))
                .Select(b => b.name)
                .OrderBy(n => n)
                .ToArray();
            sb.AppendLine($"  SMR '{smr.gameObject.name}': {facialBones.Length} FACIAL_ bones");
            // Show lip/mouth/jaw related ones
            var lipBones = facialBones.Where(n =>
                n.Contains("Lip") || n.Contains("Jaw") || n.Contains("Mouth") ||
                n.Contains("lip") || n.Contains("jaw") || n.Contains("mouth")).ToArray();
            sb.AppendLine($"  Lip/Jaw/Mouth bones ({lipBones.Length}):");
            foreach (var b in lipBones)
                sb.AppendLine($"    {b}");
        }

        return sb.ToString();
    }
}
