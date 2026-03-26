#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

public static class TestVisemePoses
{
    static readonly string[] BoneNames = {
        "FACIAL_C_Jaw",               // 0
        "FACIAL_C_LipLower",          // 1
        "FACIAL_C_LipUpper",          // 2
        "FACIAL_L_LipCorner",         // 3
        "FACIAL_R_LipCorner",         // 4
        "FACIAL_C_LowerLipRotation",  // 5
        "FACIAL_L_LipLower",          // 6
        "FACIAL_R_LipLower",          // 7
        "FACIAL_L_LipUpper",          // 8
        "FACIAL_R_LipUpper",          // 9
        "FACIAL_C_MouthLower",        // 10
        "FACIAL_C_MouthUpper",        // 11
        "FACIAL_C_TeethLower",        // 12
        "FACIAL_C_TeethUpper",        // 13
        "FACIAL_C_Tongue1",           // 14
        "FACIAL_C_Tongue2",           // 15
    };
    const int BC = 16;

    static readonly string[] VisemeNames = {
        "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS",
        "nn", "RR", "aa", "E", "ih", "oh", "ou"
    };

    static Vector3[,] posO;
    static Vector3[,] rotO;

    static void BuildPoses()
    {
        posO = new Vector3[15, BC];
        rotO = new Vector3[15, BC];

        // Matches MetaHumanLipSync.cs BuildPoseTable — position-based approach
        // Jaw position drop + rotation + tongue counter-rotation
        void JO(int v, float posY, float deg) {
            P(v,0, 0,posY,0);
            R(v,0, deg,0,0);
            R(v,14, -deg*1.3f,0,0);
            R(v,15, -deg*0.5f,0,0);
        }

        // 0: sil — rest

        // 1: PP — lips pressed
        P(1,1, 0,0.003f,0); P(1,2, 0,-0.003f,0);
        P(1,6, 0,0.002f,0); P(1,7, 0,0.002f,0);
        P(1,8, 0,-0.002f,0); P(1,9, 0,-0.002f,0);

        // 2: FF — lower lip tucked
        JO(2, -0.003f, 3);
        P(2,1, 0,0.004f,-0.002f); P(2,6, 0,0.003f,-0.002f); P(2,7, 0,0.003f,-0.002f);
        R(2,5, 8,0,0);

        // 3: TH — tongue between teeth
        JO(3, -0.010f, 6);
        P(3,1, 0,-0.006f,0); P(3,6, 0,-0.004f,0); P(3,7, 0,-0.004f,0);
        P(3,10, 0,-0.006f,0); P(3,12, 0,-0.005f,0);

        // 4: DD — tongue behind teeth
        JO(4, -0.010f, 6);
        P(4,1, 0,-0.006f,0); P(4,6, 0,-0.004f,0); P(4,7, 0,-0.004f,0);
        P(4,10, 0,-0.006f,0); P(4,12, 0,-0.005f,0);

        // 5: kk — back tongue
        JO(5, -0.008f, 5);
        P(5,1, 0,-0.005f,0); P(5,6, 0,-0.003f,0); P(5,7, 0,-0.003f,0);
        P(5,10, 0,-0.005f,0);

        // 6: CH — lips forward
        JO(6, -0.005f, 3);
        P(6,1, 0,-0.003f,0.004f); P(6,2, 0,0.002f,0.004f);
        P(6,3, 0.003f,0,0.003f); P(6,4, -0.003f,0,0.003f);
        P(6,6, 0.002f,-0.002f,0.003f); P(6,7, -0.002f,-0.002f,0.003f);

        // 7: SS — teeth close, spread
        P(7,1, 0,-0.002f,0);
        P(7,3, -0.005f,-0.001f,0); P(7,4, 0.005f,-0.001f,0);
        P(7,6, -0.003f,-0.002f,0); P(7,7, 0.003f,-0.002f,0);

        // 8: nn — slightly open
        JO(8, -0.005f, 3);
        P(8,1, 0,-0.004f,0); P(8,6, 0,-0.002f,0); P(8,7, 0,-0.002f,0);
        P(8,10, 0,-0.003f,0);

        // 9: RR — lips rounded forward
        JO(9, -0.005f, 3);
        P(9,1, 0,-0.003f,0.003f); P(9,2, 0,0.001f,0.003f);
        P(9,3, 0.002f,0,0.003f); P(9,4, -0.002f,0,0.003f);
        P(9,6, 0.001f,-0.002f,0.002f); P(9,7, -0.001f,-0.002f,0.002f);

        // 10: aa — WIDE OPEN
        JO(10, -0.025f, 15);
        P(10,1, 0,-0.012f,0);
        P(10,3, -0.002f,-0.003f,0); P(10,4, 0.002f,-0.003f,0);
        P(10,6, 0,-0.008f,0); P(10,7, 0,-0.008f,0);
        P(10,10, 0,-0.015f,0); P(10,12, 0,-0.012f,0);

        // 11: E — medium open + spread
        JO(11, -0.015f, 10);
        P(11,1, 0,-0.008f,0);
        P(11,3, -0.004f,-0.002f,0); P(11,4, 0.004f,-0.002f,0);
        P(11,6, -0.002f,-0.006f,0); P(11,7, 0.002f,-0.006f,0);
        P(11,10, 0,-0.010f,0); P(11,12, 0,-0.008f,0);

        // 12: ih — narrow, spread wide
        JO(12, -0.005f, 4);
        P(12,1, 0,-0.003f,0);
        P(12,3, -0.006f,0,0); P(12,4, 0.006f,0,0);
        P(12,6, -0.003f,-0.002f,0); P(12,7, 0.003f,-0.002f,0);
        P(12,10, 0,-0.004f,0);

        // 13: oh — round O
        JO(13, -0.015f, 8);
        P(13,1, 0,-0.008f,0.003f); P(13,2, 0,0.002f,0.003f);
        P(13,3, 0.004f,0,0.002f); P(13,4, -0.004f,0,0.002f);
        P(13,6, 0.002f,-0.005f,0.002f); P(13,7, -0.002f,-0.005f,0.002f);
        P(13,10, 0,-0.010f,0); P(13,12, 0,-0.008f,0);

        // 14: ou — tight pucker
        JO(14, -0.010f, 5);
        P(14,1, 0,-0.005f,0.005f); P(14,2, 0,0.002f,0.005f);
        P(14,3, 0.005f,0,0.004f); P(14,4, -0.005f,0,0.004f);
        P(14,6, 0.003f,-0.003f,0.004f); P(14,7, -0.003f,-0.003f,0.004f);
        P(14,10, 0,-0.006f,0); P(14,12, 0,-0.005f,0);
    }

    static void P(int v, int b, float x, float y, float z) { posO[v,b] = new Vector3(x,y,z); }
    static void R(int v, int b, float x, float y, float z) { rotO[v,b] = new Vector3(x,y,z); }

    static Transform[] bones;
    static Vector3[] restPos;
    static Quaternion[] restRot;

    static bool FindBones()
    {
        var smrs = Object.FindObjectsByType<SkinnedMeshRenderer>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        SkinnedMeshRenderer faceSMR = null;
        foreach (var s in smrs)
            if (s.bones.Length > 500) { faceSMR = s; break; }
        if (faceSMR == null) return false;

        var lookup = new Dictionary<string, Transform>();
        foreach (var b in faceSMR.bones)
            if (b != null) lookup[b.name] = b;

        bones = new Transform[BC];
        restPos = new Vector3[BC];
        restRot = new Quaternion[BC];
        for (int i = 0; i < BC; i++)
        {
            if (lookup.TryGetValue(BoneNames[i], out var t))
            {
                bones[i] = t;
                restPos[i] = t.localPosition;
                restRot[i] = t.localRotation;
            }
        }
        return true;
    }

    static void ApplyViseme(int v)
    {
        for (int b = 0; b < BC; b++)
        {
            if (bones[b] == null) continue;
            Undo.RecordObject(bones[b], "Test Viseme");
            bones[b].localPosition = restPos[b] + posO[v, b];
            bones[b].localRotation = restRot[b] * Quaternion.Euler(rotO[v, b]);
        }
        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();
    }

    static void ResetPose()
    {
        for (int b = 0; b < BC; b++)
        {
            if (bones[b] == null) continue;
            bones[b].localPosition = restPos[b];
            bones[b].localRotation = restRot[b];
        }
        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();
    }

    [MenuItem("Aivatar/Test Viseme aa (wide open)")]
    public static string TestAA()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(10);
        return $"Applied viseme 10 (aa)";
    }

    [MenuItem("Aivatar/Test Viseme oh")]
    public static string TestOH()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(13);
        return $"Applied viseme 13 (oh)";
    }

    [MenuItem("Aivatar/Test Viseme PP (lips closed)")]
    public static string TestPP()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(1);
        return $"Applied viseme 1 (PP)";
    }

    [MenuItem("Aivatar/Test Viseme E")]
    public static string TestE()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(11);
        return $"Applied viseme 11 (E)";
    }

    [MenuItem("Aivatar/Test Viseme ih (ee)")]
    public static string TestIH()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(12);
        return $"Applied viseme 12 (ih)";
    }

    [MenuItem("Aivatar/Test Viseme ou (oo)")]
    public static string TestOU()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ApplyViseme(14);
        return $"Applied viseme 14 (ou)";
    }

    [MenuItem("Aivatar/Reset Viseme")]
    public static string ResetViseme()
    {
        BuildPoses();
        if (!FindBones()) return "Bones not found";
        ResetPose();
        return "Reset to rest pose";
    }
}
#endif
