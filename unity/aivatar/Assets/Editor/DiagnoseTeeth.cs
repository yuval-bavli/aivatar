using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.Linq;

public class DiagnoseTeeth
{
    public static string Run()
    {
        var sb = new System.Text.StringBuilder();

        SkinnedMeshRenderer smr = null;
        foreach (var s in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (s.gameObject.name.Contains("FaceMesh") && s.bones.Length > 800)
            {
                smr = s;
                break;
            }
        }
        if (smr == null) return "ERROR: No face SMR found";

        var mesh = smr.sharedMesh;
        sb.AppendLine($"Mesh: {mesh.name}, submeshes: {mesh.subMeshCount}, bones: {smr.bones.Length}");

        // Get teeth submesh (index 1 based on FixMaterials analysis)
        var teethTris = mesh.GetTriangles(1);
        var teethVertIndices = new HashSet<int>(teethTris);
        sb.AppendLine($"Teeth submesh: {teethVertIndices.Count} unique verts, {teethTris.Length/3} tris");

        // Get bone weights for teeth verts
        var allWeights = mesh.GetAllBoneWeights();
        var bonesPerVertex = mesh.GetBonesPerVertex();

        // Count which bones influence teeth verts and how much
        var boneInfluence = new Dictionary<int, float>();  // boneIdx -> total weight
        var boneVertCount = new Dictionary<int, int>();    // boneIdx -> vert count

        int weightOffset = 0;
        for (int v = 0; v < mesh.vertexCount; v++)
        {
            int count = bonesPerVertex[v];
            if (teethVertIndices.Contains(v))
            {
                for (int w = 0; w < count; w++)
                {
                    var bw = allWeights[weightOffset + w];
                    if (!boneInfluence.ContainsKey(bw.boneIndex))
                    {
                        boneInfluence[bw.boneIndex] = 0;
                        boneVertCount[bw.boneIndex] = 0;
                    }
                    boneInfluence[bw.boneIndex] += bw.weight;
                    boneVertCount[bw.boneIndex]++;
                }
            }
            weightOffset += count;
        }

        // Sort by total influence
        var sorted = boneInfluence.OrderByDescending(kv => kv.Value).Take(30);
        sb.AppendLine("\nTop 30 bones influencing teeth submesh:");
        foreach (var kv in sorted)
        {
            var boneName = kv.Key < smr.bones.Length && smr.bones[kv.Key] != null
                ? smr.bones[kv.Key].name : $"bone_{kv.Key}";
            sb.AppendLine($"  [{kv.Key}] {boneName}: totalWeight={kv.Value:F2}, verts={boneVertCount[kv.Key]}");
        }

        // Also check: which of our driven bones appear?
        string[] drivenBones = {
            "FACIAL_C_Jaw", "FACIAL_C_LipLower", "FACIAL_C_LipUpper",
            "FACIAL_L_LipCorner", "FACIAL_R_LipCorner", "FACIAL_C_LowerLipRotation",
            "FACIAL_L_LipLower", "FACIAL_R_LipLower", "FACIAL_L_LipUpper", "FACIAL_R_LipUpper",
            "FACIAL_C_MouthLower", "FACIAL_C_MouthUpper"
        };

        sb.AppendLine("\nOur driven bones' influence on teeth:");
        for (int i = 0; i < smr.bones.Length; i++)
        {
            if (smr.bones[i] == null) continue;
            for (int d = 0; d < drivenBones.Length; d++)
            {
                if (smr.bones[i].name == drivenBones[d])
                {
                    float totalW = boneInfluence.ContainsKey(i) ? boneInfluence[i] : 0;
                    int vc = boneVertCount.ContainsKey(i) ? boneVertCount[i] : 0;
                    sb.AppendLine($"  {drivenBones[d]}: totalWeight={totalW:F2}, verts={vc}");
                }
            }
        }

        return sb.ToString();
    }
}
