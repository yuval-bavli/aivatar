using UnityEngine;
using UnityEditor;
using System.Text;

public class TestJawBone
{
    public static string Diagnose()
    {
        var sb = new StringBuilder();
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";

        var go = smr.gameObject;
        sb.AppendLine($"GO: {go.name}, path: {GetPath(go.transform)}");

        // Check for Animator
        var animator = go.GetComponent<Animator>();
        if (animator == null) animator = go.GetComponentInParent<Animator>();
        sb.AppendLine($"Animator: {(animator != null ? $"found on {animator.gameObject.name}, enabled={animator.enabled}, hasController={animator.runtimeAnimatorController != null}" : "NONE")}");

        // Check root bone
        sb.AppendLine($"SMR rootBone: {(smr.rootBone != null ? smr.rootBone.name : "null")}");

        // Check which model/FBX this mesh belongs to
        var mesh = smr.sharedMesh;
        if (mesh != null)
        {
            var meshPath = AssetDatabase.GetAssetPath(mesh);
            sb.AppendLine($"Mesh asset path: {meshPath}");
        }

        // Check the bone hierarchy
        Transform jaw = FindBone(smr, "FACIAL_C_Jaw");
        if (jaw != null)
        {
            sb.AppendLine($"Jaw full path: {GetPath(jaw)}");
            sb.AppendLine($"Jaw parent: {jaw.parent?.name}");
            sb.AppendLine($"Jaw localRot: {jaw.localRotation.eulerAngles}");
            sb.AppendLine($"Jaw worldPos: {jaw.position}");
        }

        // Check all components on the GO and parents
        sb.AppendLine("Components on GO:");
        foreach (var c in go.GetComponents<Component>())
            sb.AppendLine($"  {c.GetType().Name}");

        sb.AppendLine("Components on parent:");
        if (go.transform.parent != null)
            foreach (var c in go.transform.parent.GetComponents<Component>())
                sb.AppendLine($"  {c.GetType().Name}");

        // Check the actual bone transform - is it in the same hierarchy?
        sb.AppendLine($"SMR transform: {GetPath(smr.transform)}");
        if (smr.bones.Length > 0 && smr.bones[0] != null)
            sb.AppendLine($"First bone: {GetPath(smr.bones[0])}");

        // Try BakeMesh to see if bone changes actually affect vertices
        Mesh baked = new Mesh();
        smr.BakeMesh(baked);
        var verts = baked.vertices;
        // Get the original mesh vertices for comparison
        var origVerts = smr.sharedMesh.vertices;
        int diffCount = 0;
        float maxDiff = 0;
        for (int i = 0; i < Mathf.Min(verts.Length, origVerts.Length); i++)
        {
            float d = Vector3.Distance(verts[i], origVerts[i]);
            if (d > 0.0001f) diffCount++;
            if (d > maxDiff) maxDiff = d;
        }
        sb.AppendLine($"BakeMesh: {verts.Length} verts, {diffCount} differ from sharedMesh, maxDiff={maxDiff:F6}");
        Object.DestroyImmediate(baked);

        return sb.ToString();
    }

    public static string ResetAll()
    {
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";
        Transform jaw = FindBone(smr, "FACIAL_C_Jaw");
        if (jaw != null) jaw.localRotation = new Quaternion(0.34202f, 0f, 0f, 0.93969f);
        Transform lipL = FindBone(smr, "FACIAL_L_LipCorner");
        if (lipL != null) lipL.localPosition = new Vector3(-0.02596f, -0.00290f, 0.01452f);
        Transform lipR = FindBone(smr, "FACIAL_R_LipCorner");
        if (lipR != null) lipR.localPosition = new Vector3(0.02589f, -0.00317f, 0.01421f);
        Transform lipLower = FindBone(smr, "FACIAL_C_LipLower");
        if (lipLower != null) lipLower.localPosition = new Vector3(-0.00024f, -0.00776f, 0.02799f);
        EditorUtility.SetDirty(smr);
        SceneView.RepaintAll();
        return "All bones reset";
    }

    static string GetPath(Transform t)
    {
        var sb = new StringBuilder(t.name);
        var p = t.parent;
        while (p != null)
        {
            sb.Insert(0, p.name + "/");
            p = p.parent;
        }
        return sb.ToString();
    }

    static SkinnedMeshRenderer FindFaceSMR()
    {
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (smr.gameObject.name.Contains("FaceMesh") && smr.bones.Length > 800)
                return smr;
        }
        return null;
    }

    static Transform FindBone(SkinnedMeshRenderer smr, string name)
    {
        foreach (var b in smr.bones)
        {
            if (b != null && b.name == name) return b;
        }
        return null;
    }
}
