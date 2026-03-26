using UnityEngine;

/// <summary>
/// Runtime test: cycles through viseme blendshapes to verify they work in play mode.
/// Attach to the same GameObject as the SkinnedMeshRenderer with baked visemes.
/// Press Space to cycle through visemes, R to reset.
/// </summary>
public class TestVisemePlayMode : MonoBehaviour
{
    public SkinnedMeshRenderer faceMesh;
    private int currentViseme = -1;
    private string[] visemeNames;
    private float autoTimer = 0;
    public bool autoCycle = true;
    public float cycleSpeed = 1.0f;

    void Start()
    {
        if (faceMesh == null)
            faceMesh = GetComponent<SkinnedMeshRenderer>();

        if (faceMesh == null || faceMesh.sharedMesh == null)
        {
            Debug.LogError("TestVisemePlayMode: No SkinnedMeshRenderer with mesh found!");
            enabled = false;
            return;
        }

        int count = faceMesh.sharedMesh.blendShapeCount;
        visemeNames = new string[count];
        for (int i = 0; i < count; i++)
            visemeNames[i] = faceMesh.sharedMesh.GetBlendShapeName(i);

        Debug.Log($"TestVisemePlayMode: Found {count} blendshapes. Press Space to cycle, R to reset.");

        // Start with aa to verify deformation
        if (count > 0)
        {
            int aaIdx = faceMesh.sharedMesh.GetBlendShapeIndex("aa");
            if (aaIdx >= 0)
            {
                faceMesh.SetBlendShapeWeight(aaIdx, 100f);
                currentViseme = aaIdx;
                Debug.Log($"Starting with 'aa' (idx {aaIdx}) at 100%");
            }
        }
    }

    void Update()
    {
        if (faceMesh == null) return;

        if (Input.GetKeyDown(KeyCode.Space))
        {
            NextViseme();
        }

        if (Input.GetKeyDown(KeyCode.R))
        {
            ResetAll();
        }

        // Auto-cycle
        if (autoCycle)
        {
            autoTimer += Time.deltaTime;
            if (autoTimer >= cycleSpeed)
            {
                autoTimer = 0;
                NextViseme();
            }
        }
    }

    void NextViseme()
    {
        int count = faceMesh.sharedMesh.blendShapeCount;
        if (count == 0) return;

        // Reset current
        if (currentViseme >= 0)
            faceMesh.SetBlendShapeWeight(currentViseme, 0);

        currentViseme = (currentViseme + 1) % count;
        faceMesh.SetBlendShapeWeight(currentViseme, 100f);

        string name = currentViseme < visemeNames.Length ? visemeNames[currentViseme] : "?";
        Debug.Log($"Viseme: [{currentViseme}] {name}");
    }

    void ResetAll()
    {
        for (int i = 0; i < faceMesh.sharedMesh.blendShapeCount; i++)
            faceMesh.SetBlendShapeWeight(i, 0);
        currentViseme = -1;
        Debug.Log("All visemes reset");
    }
}
