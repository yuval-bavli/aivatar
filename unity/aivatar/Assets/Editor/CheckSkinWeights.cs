#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

public static class CheckSkinWeights
{
    [MenuItem("Aivatar/Check Skin Weights")]
    public static string Check()
    {
        var sb = new System.Text.StringBuilder();

        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);

        foreach (var smr in smrs)
        {
            var mesh = smr.sharedMesh;
            if (mesh == null) continue;

            sb.AppendLine($"\nSMR '{smr.name}': bones={smr.bones.Length}  verts={mesh.vertexCount}");
            sb.AppendLine($"  bindposes: {mesh.bindposes.Length}");
            sb.AppendLine($"  skinWeightBufferLayout: {mesh.skinWeightBufferLayout}");

            // Check bone weights
            var boneWeights = mesh.boneWeights;
            sb.AppendLine($"  boneWeights (legacy): {boneWeights.Length}");

            if (boneWeights.Length > 0)
            {
                // Check if any weights are non-zero
                int nonZero = 0;
                int jawInfluenced = 0;

                // Find jaw bone index
                int jawIdx = -1;
                for (int i = 0; i < smr.bones.Length; i++)
                    if (smr.bones[i] != null && smr.bones[i].name == "FACIAL_C_Jaw")
                    { jawIdx = i; break; }

                sb.AppendLine($"  jawBoneIndex: {jawIdx}");

                for (int i = 0; i < Mathf.Min(boneWeights.Length, mesh.vertexCount); i++)
                {
                    var bw = boneWeights[i];
                    if (bw.weight0 > 0) nonZero++;
                    if (jawIdx >= 0)
                    {
                        if ((bw.boneIndex0 == jawIdx && bw.weight0 > 0) ||
                            (bw.boneIndex1 == jawIdx && bw.weight1 > 0) ||
                            (bw.boneIndex2 == jawIdx && bw.weight2 > 0) ||
                            (bw.boneIndex3 == jawIdx && bw.weight3 > 0))
                            jawInfluenced++;
                    }
                }
                sb.AppendLine($"  Non-zero weight verts: {nonZero}/{boneWeights.Length}");
                sb.AppendLine($"  Jaw-influenced verts: {jawInfluenced}");

                // Sample first few with nonzero
                int shown = 0;
                for (int i = 0; i < boneWeights.Length && shown < 5; i++)
                {
                    var bw = boneWeights[i];
                    if (bw.weight0 > 0)
                    {
                        sb.AppendLine($"  vert[{i}]: b0={bw.boneIndex0} w0={bw.weight0:F3} b1={bw.boneIndex1} w1={bw.weight1:F3}");
                        shown++;
                    }
                }
            }
            else
            {
                // Try GetAllBoneWeights (new API)
                var allWeights = mesh.GetAllBoneWeights();
                var bonesPerVertex = mesh.GetBonesPerVertex();
                sb.AppendLine($"  GetAllBoneWeights: {allWeights.Length}");
                sb.AppendLine($"  GetBonesPerVertex: {bonesPerVertex.Length}");

                if (allWeights.Length > 0)
                {
                    int shown = 0;
                    for (int i = 0; i < Mathf.Min(allWeights.Length, 10); i++)
                    {
                        sb.AppendLine($"  weight[{i}]: bone={allWeights[i].boneIndex} w={allWeights[i].weight:F3}");
                        shown++;
                    }
                }
            }

            // Check if mesh is being used as skinned or static
            sb.AppendLine($"  rootBone: {(smr.rootBone != null ? smr.rootBone.name : "null")}");
            sb.AppendLine($"  updateWhenOffscreen: {smr.updateWhenOffscreen}");
            sb.AppendLine($"  forceMatrixRecalculationPerRender: {smr.forceMatrixRecalculationPerRender}");
        }

        string result = sb.ToString();
        Debug.Log("[CheckSkinWeights] " + result);
        return result;
    }
}
#endif
