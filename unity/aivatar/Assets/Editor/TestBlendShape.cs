using UnityEngine;
using UnityEditor;

public class TestBlendShape
{
    // Directly modify sharedMesh vertices to test if rendering updates
    public static string DirectDeform()
    {
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";
        var mesh = smr.sharedMesh;

        // Get the aa blendshape deltas
        int aaIdx = mesh.GetBlendShapeIndex("aa");
        if (aaIdx < 0) return "ERROR: 'aa' not found";

        Vector3[] deltas = new Vector3[mesh.vertexCount];
        Vector3[] normals = new Vector3[mesh.vertexCount];
        Vector3[] tangents = new Vector3[mesh.vertexCount];
        mesh.GetBlendShapeFrameVertices(aaIdx, 0, deltas, normals, tangents);

        // Apply deltas directly to vertex positions
        Vector3[] verts = mesh.vertices;
        for (int i = 0; i < verts.Length; i++)
            verts[i] += deltas[i];
        mesh.vertices = verts;
        mesh.RecalculateBounds();

        EditorUtility.SetDirty(smr);
        SceneView.RepaintAll();
        return $"Applied {mesh.vertexCount} vertex offsets directly to mesh";
    }

    public static string UndoDeform()
    {
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";
        var mesh = smr.sharedMesh;

        int aaIdx = mesh.GetBlendShapeIndex("aa");
        if (aaIdx < 0) return "ERROR: 'aa' not found";

        Vector3[] deltas = new Vector3[mesh.vertexCount];
        Vector3[] normals = new Vector3[mesh.vertexCount];
        Vector3[] tangents = new Vector3[mesh.vertexCount];
        mesh.GetBlendShapeFrameVertices(aaIdx, 0, deltas, normals, tangents);

        Vector3[] verts = mesh.vertices;
        for (int i = 0; i < verts.Length; i++)
            verts[i] -= deltas[i];
        mesh.vertices = verts;
        mesh.RecalculateBounds();

        // Reset blendshape weights too
        for (int i = 0; i < mesh.blendShapeCount; i++)
            smr.SetBlendShapeWeight(i, 0);

        EditorUtility.SetDirty(smr);
        SceneView.RepaintAll();
        return "Undone vertex deform";
    }

    public static string Reset()
    {
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";
        for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++)
            smr.SetBlendShapeWeight(i, 0);
        EditorUtility.SetDirty(smr);
        SceneView.RepaintAll();
        return "All blendshapes reset to 0";
    }

    public static string VerifyAA()
    {
        var smr = FindFaceSMR();
        if (smr == null) return "ERROR: No face SMR found";
        var mesh = smr.sharedMesh;

        int aaIdx = mesh.GetBlendShapeIndex("aa");
        if (aaIdx < 0) return "ERROR: 'aa' not found";

        for (int i = 0; i < mesh.blendShapeCount; i++)
            smr.SetBlendShapeWeight(i, 0);
        Mesh rest = new Mesh();
        smr.BakeMesh(rest);
        var restV = rest.vertices;

        smr.SetBlendShapeWeight(aaIdx, 100f);
        Mesh posed = new Mesh();
        smr.BakeMesh(posed);
        var posedV = posed.vertices;

        int moved = 0; float maxD = 0;
        for (int i = 0; i < restV.Length; i++)
        {
            float d = Vector3.Distance(restV[i], posedV[i]);
            if (d > 0.0001f) moved++;
            if (d > maxD) maxD = d;
        }

        Object.DestroyImmediate(rest);
        Object.DestroyImmediate(posed);

        Vector3[] deltas = new Vector3[mesh.vertexCount];
        Vector3[] normals = new Vector3[mesh.vertexCount];
        Vector3[] tangents = new Vector3[mesh.vertexCount];
        mesh.GetBlendShapeFrameVertices(aaIdx, 0, deltas, normals, tangents);
        float maxBSDelta = 0;
        int bsMoved = 0;
        for (int i = 0; i < deltas.Length; i++)
        {
            float d = deltas[i].magnitude;
            if (d > 0.0001f) bsMoved++;
            if (d > maxBSDelta) maxBSDelta = d;
        }

        return $"Mesh: {mesh.name}, verts: {restV.Length}\n" +
               $"aa=100 vs aa=0: {moved} verts moved, maxDelta={maxD:F6}\n" +
               $"BlendShape stored deltas: {bsMoved} non-zero, maxDelta={maxBSDelta:F6}";
    }

    static SkinnedMeshRenderer FindFaceSMR()
    {
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (smr.gameObject.name.Contains("FaceMesh") && smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0)
                return smr;
        }
        foreach (var smr in Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
        {
            if (smr.gameObject.name.Contains("FaceMesh") && smr.bones.Length > 800)
                return smr;
        }
        return null;
    }
}
