using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

public class InspectFBXDeep
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        string[] fbxPaths = {
            "Assets/Models/Avatar/SKM_model4_FaceMesh.FBX",
            "Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX",
        };

        foreach (var path in fbxPaths)
        {
            sb.AppendLine($"\n=== {path} ===");

            // Load all assets at path
            var allAssets = AssetDatabase.LoadAllAssetsAtPath(path);
            sb.AppendLine($"Total sub-assets: {allAssets.Length}");

            int meshCount = 0, clipCount = 0, avatarCount = 0, otherCount = 0;
            foreach (var asset in allAssets)
            {
                if (asset == null) continue;

                if (asset is Mesh m)
                {
                    meshCount++;
                    sb.AppendLine($"  Mesh: '{m.name}' verts={m.vertexCount} submeshes={m.subMeshCount} blendShapes={m.blendShapeCount}");
                }
                else if (asset is AnimationClip clip)
                {
                    clipCount++;
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    sb.AppendLine($"  AnimClip: '{clip.name}' length={clip.length:F3}s curves={bindings.Length}");
                    // Show first 10 curve bindings
                    for (int i = 0; i < Mathf.Min(bindings.Length, 20); i++)
                    {
                        sb.AppendLine($"    [{i}] {bindings[i].path} / {bindings[i].propertyName} (type={bindings[i].type.Name})");
                    }
                    if (bindings.Length > 20) sb.AppendLine($"    ... and {bindings.Length - 20} more");
                }
                else if (asset is Avatar av)
                {
                    avatarCount++;
                    sb.AppendLine($"  Avatar: '{av.name}' isHuman={av.isHuman}");
                }
                else
                {
                    otherCount++;
                }
            }
            sb.AppendLine($"Summary: {meshCount} meshes, {clipCount} clips, {avatarCount} avatars, {otherCount} other");

            // Check importer settings
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer != null)
            {
                sb.AppendLine($"  Import settings:");
                sb.AppendLine($"    isReadable: {importer.isReadable}");
                sb.AppendLine($"    animationType: {importer.animationType}");
                sb.AppendLine($"    importAnimation: {importer.importAnimation}");
                sb.AppendLine($"    importBlendShapes: {importer.importBlendShapes}");
                sb.AppendLine($"    importBlendShapeNormals: {importer.importBlendShapeNormals}");

                // Check animation clips in importer
                var clips = importer.clipAnimations;
                sb.AppendLine($"    clipAnimations count: {clips.Length}");
                var defaultClips = importer.defaultClipAnimations;
                sb.AppendLine($"    defaultClipAnimations count: {defaultClips.Length}");
                foreach (var c in defaultClips)
                {
                    sb.AppendLine($"      default clip: '{c.name}' {c.firstFrame}-{c.lastFrame}");
                }
            }
        }

        return sb.ToString();
    }
}
