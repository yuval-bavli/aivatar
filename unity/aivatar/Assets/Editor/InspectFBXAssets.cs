using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

public class InspectFBXAssets
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();
        string path = "Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX";

        var allAssets = AssetDatabase.LoadAllAssetsAtPath(path);
        sb.AppendLine($"FaceMesh3: {allAssets.Length} total sub-assets");

        // Count by type
        var typeCounts = new Dictionary<string, int>();
        foreach (var asset in allAssets)
        {
            if (asset == null) continue;
            string typeName = asset.GetType().Name;
            if (!typeCounts.ContainsKey(typeName)) typeCounts[typeName] = 0;
            typeCounts[typeName]++;
        }

        sb.AppendLine("\nAsset types:");
        foreach (var kv in typeCounts)
        {
            sb.AppendLine($"  {kv.Key}: {kv.Value}");
        }

        // Check if any are AnimationClip, Avatar, or unusual types
        foreach (var asset in allAssets)
        {
            if (asset == null) continue;
            if (asset is AnimationClip || asset is Avatar || asset is RuntimeAnimatorController)
            {
                sb.AppendLine($"\nSpecial asset: {asset.GetType().Name} '{asset.name}'");
            }
        }

        // Also check: does enabling isReadable + reimport reveal blendshapes?
        // First just report what the FBX binary might contain
        // Check the bone diff between original and FaceMesh3
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None);
        foreach (var smr in smrs)
        {
            if (!smr.gameObject.name.Contains("FaceMesh")) continue;
            sb.AppendLine($"\nScene SMR '{smr.gameObject.name}': bones={smr.bones.Length}, mesh='{smr.sharedMesh?.name}', blendShapes={smr.sharedMesh?.blendShapeCount}");
        }

        return sb.ToString();
    }
}
