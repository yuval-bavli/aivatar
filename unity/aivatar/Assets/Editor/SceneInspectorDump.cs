#if UNITY_EDITOR
using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Dumps key scene object properties (materials, transforms) as JSON.
/// Called by the Python improver via the agent bridge:
///   execute SceneInspectorDump.DumpAll
/// </summary>
public static class SceneInspectorDump
{
    [MenuItem("Aivatar/Dump Scene Inspector (JSON)")]
    public static string DumpAll()
    {
        var sb = new StringBuilder();
        sb.Append("{");

        // ── Materials ────────────────────────────────────────────────────
        sb.Append("\"materials\":{");
        bool firstMat = true;
        string[] matNames = {
            "Eyebrows", "haircut", "MI_Face_EyelashesHiLODs",
            "M_Hide", "M_Hide_6",
            "MID_M_DG_bodyShapeB_Shirt_70", "MID_M_DG_bodyShapeB_Short_71"
        };
        foreach (var name in matNames)
        {
            string path = $"Assets/Models/Avatar/Materials/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) continue;

            if (!firstMat) sb.Append(",");
            firstMat = false;

            sb.Append($"\"{name}\":{{");
            sb.Append("\"floats\":{");

            string[] floatProps = {
                "_Cutoff", "_Smoothness", "_BumpScale", "_Metallic",
                "_SpecularHighlights", "_EnvironmentReflections", "_AlphaClip"
            };
            bool firstF = true;
            foreach (var prop in floatProps)
            {
                if (!mat.HasProperty(prop)) continue;
                if (!firstF) sb.Append(",");
                firstF = false;
                sb.Append($"\"{prop}\":{mat.GetFloat(prop):F6}");
            }
            sb.Append("},\"colors\":{");

            string[] colorProps = { "_BaseColor" };
            bool firstC = true;
            foreach (var prop in colorProps)
            {
                if (!mat.HasProperty(prop)) continue;
                if (!firstC) sb.Append(",");
                firstC = false;
                var c = mat.GetColor(prop);
                sb.Append($"\"{prop}\":[{c.r:F6},{c.g:F6},{c.b:F6},{c.a:F6}]");
            }
            sb.Append("}}");
        }
        sb.Append("},");

        // ── Key transforms ───────────────────────────────────────────────
        sb.Append("\"transforms\":{");
        string[] objNames = {
            "Eyebrows_M_Natural_CardsMesh_Group0_LOD0",
            "Hair_M_BobMessy_CardsMesh_Group0_LOD0",
            "SKM_model4_FaceMesh"
        };
        bool firstObj = true;
        foreach (var objName in objNames)
        {
            var go = GameObject.Find(objName);
            if (go == null) continue;

            if (!firstObj) sb.Append(",");
            firstObj = false;

            var t = go.transform;
            var lp = t.localPosition;
            var wp = t.position;
            bool enabled = go.activeSelf;

            sb.Append($"\"{objName}\":{{");
            sb.Append($"\"enabled\":{(enabled ? "true" : "false")},");
            sb.Append($"\"localPos\":[{lp.x:F4},{lp.y:F4},{lp.z:F4}],");
            sb.Append($"\"worldPos\":[{wp.x:F4},{wp.y:F4},{wp.z:F4}]");
            sb.Append("}");
        }
        sb.Append("}");

        sb.Append("}");
        return sb.ToString();
    }
}
#endif
