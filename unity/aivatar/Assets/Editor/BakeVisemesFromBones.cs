using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

/// <summary>
/// Bakes MetaHuman facial bone poses into blendshapes for each Azure viseme.
/// Drives 12 bones for natural-looking deformation, primarily through jaw rotation.
/// </summary>
public class BakeVisemesFromBones
{
    static readonly string[] VisemeNames = {
        "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS",
        "nn", "RR", "aa", "E", "ih", "oh", "ou"
    };

    // All bone names we drive
    static readonly string[] BoneNames = {
        "FACIAL_C_Jaw",               // 0  - primary jaw open/close
        "FACIAL_C_LipLower",          // 1  - center lower lip
        "FACIAL_C_LipUpper",          // 2  - center upper lip
        "FACIAL_L_LipCorner",         // 3  - left lip corner
        "FACIAL_R_LipCorner",         // 4  - right lip corner
        "FACIAL_C_LowerLipRotation",  // 5  - lower lip roll
        "FACIAL_L_LipLower",          // 6  - left lower lip
        "FACIAL_R_LipLower",          // 7  - right lower lip
        "FACIAL_L_LipUpper",          // 8  - left upper lip
        "FACIAL_R_LipUpper",          // 9  - right upper lip
        "FACIAL_C_MouthLower",        // 10 - inner mouth lower
        "FACIAL_C_MouthUpper",        // 11 - inner mouth upper
    };

    // Per-viseme pose: which bones to move and how.
    // Each viseme is defined as a set of bone adjustments.
    struct BoneAdj
    {
        public int boneIdx;
        public Vector3 posOffset;    // local position offset
        public Vector3 rotOffset;    // euler angles offset
    }

    static BoneAdj[][] GetVisemePoses()
    {
        // Jaw open degrees → rotation offset
        // Lip corner spread → position X offset (negative for left = outward, positive for right = outward)
        // Lip forward → position Z offset
        // Lip Y → position Y offset

        var poses = new BoneAdj[15][];

        // 0: sil — rest pose, no adjustments
        poses[0] = new BoneAdj[0];

        // 1: PP — lips pressed, jaw barely open
        poses[1] = new BoneAdj[] {
            Rot(0, 5, 0, 0),                      // jaw barely open
            Pos(1, 0, 0.003f, 0),                  // lower lip up slightly
            Pos(2, 0, -0.002f, 0),                 // upper lip down slightly
            Pos(3, 0.003f, 0, 0),                  // left corner inward
            Pos(4, -0.003f, 0, 0),                 // right corner inward
        };

        // 2: FF — lower lip touches upper teeth
        poses[2] = new BoneAdj[] {
            Rot(0, 8, 0, 0),                       // jaw slightly open
            Pos(1, 0, 0.006f, -0.002f),             // lower lip up and back
            Rot(5, 10, 0, 0),                       // lower lip roll inward
            Pos(6, 0, 0.004f, -0.001f),             // L lower lip up
            Pos(7, 0, 0.004f, -0.001f),             // R lower lip up
        };

        // 3: TH — tongue tip, jaw medium open
        poses[3] = new BoneAdj[] {
            Rot(0, 20, 0, 0),                      // jaw medium open
            Pos(1, 0, -0.002f, 0),                  // lower lip slightly down
        };

        // 4: DD — tongue behind teeth, jaw medium
        poses[4] = new BoneAdj[] {
            Rot(0, 25, 0, 0),                      // jaw medium open
        };

        // 5: kk — back tongue, jaw medium
        poses[5] = new BoneAdj[] {
            Rot(0, 20, 0, 0),                      // jaw open
        };

        // 6: CH — "sh" sound, lips slightly forward
        poses[6] = new BoneAdj[] {
            Rot(0, 15, 0, 0),                      // jaw slightly open
            Pos(3, 0.002f, 0, 0.004f),              // left corner slightly in + forward
            Pos(4, -0.002f, 0, 0.004f),             // right corner slightly in + forward
            Pos(1, 0, 0, 0.003f),                   // lower lip forward
            Pos(2, 0, 0, 0.003f),                   // upper lip forward
        };

        // 7: SS — teeth close, lips spread
        poses[7] = new BoneAdj[] {
            Rot(0, 8, 0, 0),                       // jaw barely open
            Pos(3, -0.005f, 0, 0),                  // left corner outward
            Pos(4, 0.005f, 0, 0),                   // right corner outward
            Pos(6, -0.003f, 0, 0),                  // L lower lip outward
            Pos(7, 0.003f, 0, 0),                   // R lower lip outward
            Pos(8, -0.003f, 0, 0),                  // L upper lip outward
            Pos(9, 0.003f, 0, 0),                   // R upper lip outward
        };

        // 8: nn — tongue behind teeth, relaxed
        poses[8] = new BoneAdj[] {
            Rot(0, 15, 0, 0),                      // jaw slightly open
        };

        // 9: RR — lips slightly rounded
        poses[9] = new BoneAdj[] {
            Rot(0, 18, 0, 0),                      // jaw medium
            Pos(3, 0.002f, 0, 0.003f),              // left corner slightly in + forward
            Pos(4, -0.002f, 0, 0.003f),             // right corner slightly in + forward
            Pos(1, 0, 0, 0.002f),                   // lower lip forward
            Pos(2, 0, 0, 0.002f),                   // upper lip forward
        };

        // 10: aa — wide open mouth (most dramatic)
        poses[10] = new BoneAdj[] {
            Rot(0, 60, 0, 0),                      // jaw wide open
            Pos(1, 0, -0.008f, 0),                  // lower lip down
            Pos(2, 0, 0.004f, 0),                   // upper lip up
            Pos(3, -0.003f, 0, 0),                  // left corner outward
            Pos(4, 0.003f, 0, 0),                   // right corner outward
            Pos(6, -0.002f, -0.005f, 0),            // L lower lip out + down
            Pos(7, 0.002f, -0.005f, 0),             // R lower lip out + down
            Pos(8, -0.002f, 0.003f, 0),             // L upper lip out + up
            Pos(9, 0.002f, 0.003f, 0),              // R upper lip out + up
        };

        // 11: E — "eh" medium open, lips spread
        poses[11] = new BoneAdj[] {
            Rot(0, 35, 0, 0),                      // jaw medium open
            Pos(1, 0, -0.004f, 0),                  // lower lip down
            Pos(2, 0, 0.002f, 0),                   // upper lip up slightly
            Pos(3, -0.004f, 0, 0),                  // left corner outward
            Pos(4, 0.004f, 0, 0),                   // right corner outward
            Pos(6, -0.002f, -0.002f, 0),            // L lower out+down
            Pos(7, 0.002f, -0.002f, 0),             // R lower out+down
        };

        // 12: ih — "ee" narrow opening, lips spread wide
        poses[12] = new BoneAdj[] {
            Rot(0, 15, 0, 0),                      // jaw slightly open
            Pos(3, -0.006f, 0, 0),                  // left corner outward (spread)
            Pos(4, 0.006f, 0, 0),                   // right corner outward
            Pos(6, -0.004f, 0, 0),                  // L lower lip out
            Pos(7, 0.004f, 0, 0),                   // R lower lip out
            Pos(8, -0.004f, 0, 0),                  // L upper lip out
            Pos(9, 0.004f, 0, 0),                   // R upper lip out
        };

        // 13: oh — round open, lips forward
        poses[13] = new BoneAdj[] {
            Rot(0, 45, 0, 0),                      // jaw medium-wide
            Pos(1, 0, -0.004f, 0.004f),             // lower lip down + forward
            Pos(2, 0, 0.002f, 0.004f),              // upper lip up + forward
            Pos(3, 0.003f, 0, 0.004f),              // left corner inward + forward
            Pos(4, -0.003f, 0, 0.004f),             // right corner inward + forward
            Pos(6, 0.002f, -0.002f, 0.003f),        // L lower lip in + fwd
            Pos(7, -0.002f, -0.002f, 0.003f),       // R lower lip in + fwd
            Pos(8, 0.002f, 0.001f, 0.003f),         // L upper lip in + fwd
            Pos(9, -0.002f, 0.001f, 0.003f),        // R upper lip in + fwd
        };

        // 14: ou — "oo" tight round, lips pucker forward
        poses[14] = new BoneAdj[] {
            Rot(0, 25, 0, 0),                      // jaw slightly open
            Pos(1, 0, -0.002f, 0.006f),             // lower lip forward
            Pos(2, 0, 0.001f, 0.006f),              // upper lip forward
            Pos(3, 0.005f, 0, 0.005f),              // left corner inward + forward
            Pos(4, -0.005f, 0, 0.005f),             // right corner inward + forward
            Pos(6, 0.003f, 0, 0.004f),              // L lower lip inward + fwd
            Pos(7, -0.003f, 0, 0.004f),             // R lower lip inward + fwd
            Pos(8, 0.003f, 0, 0.004f),              // L upper lip inward + fwd
            Pos(9, -0.003f, 0, 0.004f),             // R upper lip inward + fwd
        };

        return poses;
    }

    // Helper constructors
    static BoneAdj Pos(int idx, float x, float y, float z)
    {
        return new BoneAdj { boneIdx = idx, posOffset = new Vector3(x, y, z), rotOffset = Vector3.zero };
    }
    static BoneAdj Rot(int idx, float x, float y, float z)
    {
        return new BoneAdj { boneIdx = idx, posOffset = Vector3.zero, rotOffset = new Vector3(x, y, z) };
    }

    struct BoneRestPose
    {
        public Transform bone;
        public Vector3 localPos;
        public Quaternion localRot;
    }

    [MenuItem("Aivatar/Bake Visemes From Bones")]
    public static void Bake()
    {
        var result = Run();
        Debug.Log(result);
    }

    public static string Run()
    {
        // Find the face SMR with the most bones (MetaHuman rig)
        SkinnedMeshRenderer smr = null;
        foreach (var s in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (s.gameObject.name.Contains("FaceMesh") && s.bones.Length > 800)
            {
                smr = s;
                break;
            }
        }
        if (smr == null) return "ERROR: No MetaHuman face SMR found (need >800 bones)";

        // Find all needed bones
        var bones = new Transform[BoneNames.Length];
        foreach (var b in smr.bones)
        {
            if (b == null) continue;
            for (int i = 0; i < BoneNames.Length; i++)
            {
                if (b.name == BoneNames[i]) bones[i] = b;
            }
        }
        // Only jaw is strictly required
        if (bones[0] == null) return "ERROR: FACIAL_C_Jaw not found";

        // Ensure we're working with the original FBX mesh
        Mesh originalMesh = smr.sharedMesh;
        string meshAssetPath = AssetDatabase.GetAssetPath(originalMesh);
        if (string.IsNullOrEmpty(meshAssetPath) || meshAssetPath.EndsWith(".asset"))
        {
            var fbxMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Models/Avatar/SKM_model4_FaceMesh3.FBX");
            if (fbxMesh != null)
            {
                smr.sharedMesh = fbxMesh;
                originalMesh = fbxMesh;
            }
        }

        // Save rest poses
        var restPoses = new BoneRestPose[BoneNames.Length];
        for (int i = 0; i < BoneNames.Length; i++)
        {
            if (bones[i] != null)
            {
                restPoses[i] = new BoneRestPose {
                    bone = bones[i],
                    localPos = bones[i].localPosition,
                    localRot = bones[i].localRotation
                };
            }
        }

        // Bake rest pose
        Mesh restMesh = new Mesh();
        smr.BakeMesh(restMesh);
        Vector3[] restVerts = restMesh.vertices;
        int vertCount = restVerts.Length;

        // Create target mesh
        Mesh targetMesh = Object.Instantiate(originalMesh);
        targetMesh.name = "SKM_model4_FaceMesh3_Visemes";

        var visemePoses = GetVisemePoses();
        var report = new System.Text.StringBuilder();
        report.AppendLine($"Source: {smr.gameObject.name}, verts: {vertCount}, bones: {BoneNames.Length}");

        for (int v = 0; v < VisemeNames.Length; v++)
        {
            // Apply bone adjustments for this viseme
            var adjs = visemePoses[v];
            foreach (var adj in adjs)
            {
                if (bones[adj.boneIdx] == null) continue;
                var rest = restPoses[adj.boneIdx];

                if (adj.posOffset != Vector3.zero)
                    bones[adj.boneIdx].localPosition = rest.localPos + adj.posOffset;
                if (adj.rotOffset != Vector3.zero)
                    bones[adj.boneIdx].localRotation = rest.localRot * Quaternion.Euler(adj.rotOffset);
            }

            // Bake posed mesh
            Mesh posedMesh = new Mesh();
            smr.BakeMesh(posedMesh);
            Vector3[] posedVerts = posedMesh.vertices;

            // Compute deltas
            Vector3[] deltas = new Vector3[vertCount];
            Vector3[] deltaNormals = new Vector3[vertCount];
            Vector3[] deltaTangents = new Vector3[vertCount];
            int movedCount = 0;
            float maxDelta = 0;
            for (int i = 0; i < vertCount; i++)
            {
                deltas[i] = posedVerts[i] - restVerts[i];
                float d = deltas[i].magnitude;
                if (d > 0.0001f) movedCount++;
                if (d > maxDelta) maxDelta = d;
            }

            targetMesh.AddBlendShapeFrame(VisemeNames[v], 100f, deltas, deltaNormals, deltaTangents);
            report.AppendLine($"  [{v}] {VisemeNames[v]}: {movedCount} verts, maxDelta={maxDelta:F5}");

            // Reset all bones to rest
            for (int i = 0; i < BoneNames.Length; i++)
            {
                if (bones[i] != null)
                {
                    bones[i].localPosition = restPoses[i].localPos;
                    bones[i].localRotation = restPoses[i].localRot;
                }
            }

            Object.DestroyImmediate(posedMesh);
        }

        Object.DestroyImmediate(restMesh);

        // Save asset
        string assetPath = "Assets/Models/Avatar/SKM_model4_FaceMesh3_Visemes.asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
        if (existing != null)
            AssetDatabase.DeleteAsset(assetPath);
        AssetDatabase.CreateAsset(targetMesh, assetPath);
        AssetDatabase.SaveAssets();

        smr.sharedMesh = targetMesh;
        EditorUtility.SetDirty(smr);

        report.AppendLine($"Saved to {assetPath}");
        return report.ToString();
    }
}
