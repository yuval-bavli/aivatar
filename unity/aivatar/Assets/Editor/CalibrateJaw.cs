#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

public static class CalibrateJaw
{
    static Transform[] bones;
    static Vector3[] restPos;
    static Quaternion[] restRot;

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

    static bool Init()
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

    static void Reset()
    {
        for (int b = 0; b < BC; b++)
        {
            if (bones[b] == null) continue;
            bones[b].localPosition = restPos[b];
            bones[b].localRotation = restRot[b];
        }
    }

    static void P(int b, float x, float y, float z)
    {
        if (bones[b] == null) return;
        Undo.RecordObject(bones[b], "Cal");
        bones[b].localPosition = restPos[b] + new Vector3(x, y, z);
    }
    static void R(int b, float x, float y, float z)
    {
        if (bones[b] == null) return;
        Undo.RecordObject(bones[b], "Cal");
        bones[b].localRotation = restRot[b] * Quaternion.Euler(x, y, z);
    }

    static void Finish()
    {
        SceneView.RepaintAll();
        EditorApplication.QueuePlayerLoopUpdate();
    }

    // ===== VISEME TESTS =====

    // 10: aa — WIDE OPEN (most dramatic)
    [MenuItem("Aivatar/V10 aa (wide open)")]
    public static string V_aa()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.025f, 0);         // jaw down
        R(0, 15, 0, 0);              // jaw rotate open
        P(1, 0, -0.012f, 0);         // center lower lip down
        P(6, 0, -0.008f, 0);         // L lower lip down
        P(7, 0, -0.008f, 0);         // R lower lip down
        P(3, -0.002f, -0.003f, 0);   // L corner out+down
        P(4, 0.002f, -0.003f, 0);    // R corner out+down
        P(10, 0, -0.015f, 0);        // inner mouth lower down
        P(12, 0, -0.012f, 0);        // lower teeth down
        R(14, -20, 0, 0);            // tongue counter-rotate (stay in mouth)
        R(15, -10, 0, 0);
        Finish();
        return "V10 aa: jaw -0.025 + 15°, lips down, tongue counter";
    }

    // 13: oh — round O shape
    [MenuItem("Aivatar/V13 oh (round)")]
    public static string V_oh()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.015f, 0);         // jaw down moderate
        R(0, 8, 0, 0);
        P(1, 0, -0.008f, 0.003f);    // lower lip down + forward
        P(2, 0, 0.002f, 0.003f);     // upper lip up + forward
        P(3, 0.004f, 0, 0.002f);     // L corner in + forward (pucker)
        P(4, -0.004f, 0, 0.002f);    // R corner in + forward
        P(6, 0.002f, -0.005f, 0.002f);
        P(7, -0.002f, -0.005f, 0.002f);
        P(10, 0, -0.010f, 0);
        P(12, 0, -0.008f, 0);
        R(14, -12, 0, 0);
        R(15, -5, 0, 0);
        Finish();
        return "V13 oh: round O";
    }

    // 14: ou — tight pucker (oo)
    [MenuItem("Aivatar/V14 ou (pucker)")]
    public static string V_ou()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.010f, 0);
        R(0, 5, 0, 0);
        P(1, 0, -0.005f, 0.005f);    // lips forward
        P(2, 0, 0.002f, 0.005f);
        P(3, 0.005f, 0, 0.004f);     // corners strongly in + forward
        P(4, -0.005f, 0, 0.004f);
        P(6, 0.003f, -0.003f, 0.004f);
        P(7, -0.003f, -0.003f, 0.004f);
        P(10, 0, -0.006f, 0);
        P(12, 0, -0.005f, 0);
        R(14, -8, 0, 0);
        R(15, -3, 0, 0);
        Finish();
        return "V14 ou: tight pucker";
    }

    // 1: PP — lips pressed together
    [MenuItem("Aivatar/V01 PP (lips closed)")]
    public static string V_PP()
    {
        if (!Init()) return "No bones";
        Reset();
        P(1, 0, 0.003f, 0);          // lower lip UP (press against upper)
        P(2, 0, -0.003f, 0);         // upper lip DOWN
        P(6, 0, 0.002f, 0);
        P(7, 0, 0.002f, 0);
        P(8, 0, -0.002f, 0);
        P(9, 0, -0.002f, 0);
        Finish();
        return "V01 PP: lips pressed";
    }

    // 11: E — medium open + spread
    [MenuItem("Aivatar/V11 E (eh)")]
    public static string V_E()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.015f, 0);
        R(0, 10, 0, 0);
        P(1, 0, -0.008f, 0);
        P(6, -0.002f, -0.006f, 0);   // L lower lip down+out
        P(7, 0.002f, -0.006f, 0);    // R lower lip down+out
        P(3, -0.004f, -0.002f, 0);   // corners spread wide
        P(4, 0.004f, -0.002f, 0);
        P(10, 0, -0.010f, 0);
        P(12, 0, -0.008f, 0);
        R(14, -15, 0, 0);
        R(15, -6, 0, 0);
        Finish();
        return "V11 E: medium open, spread";
    }

    // 12: ih — narrow, lips spread (ee)
    [MenuItem("Aivatar/V12 ih (ee)")]
    public static string V_ih()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.005f, 0);
        R(0, 4, 0, 0);
        P(1, 0, -0.003f, 0);
        P(3, -0.006f, 0, 0);         // corners spread wide
        P(4, 0.006f, 0, 0);
        P(6, -0.003f, -0.002f, 0);
        P(7, 0.003f, -0.002f, 0);
        P(10, 0, -0.004f, 0);
        R(14, -6, 0, 0);
        R(15, -2, 0, 0);
        Finish();
        return "V12 ih: narrow spread (ee)";
    }

    // 7: SS — teeth close, lips spread
    [MenuItem("Aivatar/V07 SS (teeth)")]
    public static string V_SS()
    {
        if (!Init()) return "No bones";
        Reset();
        P(1, 0, -0.002f, 0);
        P(3, -0.005f, -0.001f, 0);   // corners spread
        P(4, 0.005f, -0.001f, 0);
        P(6, -0.003f, -0.002f, 0);
        P(7, 0.003f, -0.002f, 0);
        Finish();
        return "V07 SS: teeth close, spread";
    }

    // 2: FF — lower lip under upper teeth
    [MenuItem("Aivatar/V02 FF")]
    public static string V_FF()
    {
        if (!Init()) return "No bones";
        Reset();
        P(0, 0, -0.003f, 0);
        R(0, 3, 0, 0);
        P(1, 0, 0.004f, -0.002f);    // lower lip UP and BACK (under teeth)
        P(6, 0, 0.003f, -0.002f);
        P(7, 0, 0.003f, -0.002f);
        R(5, 8, 0, 0);               // lower lip rotation up
        Finish();
        return "V02 FF: lower lip tucked";
    }

    [MenuItem("Aivatar/Calibrate Reset")]
    public static string CalReset()
    {
        if (!Init()) return "No bones";
        Reset();
        Finish();
        return "Reset to rest";
    }
}
#endif
