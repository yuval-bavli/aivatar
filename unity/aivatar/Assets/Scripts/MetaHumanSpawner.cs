using UnityEngine;

/// <summary>
/// Spawns the MetaHuman prefab (Body + Face combined) into the scene.
/// Attach this to any GameObject (e.g. an empty "AvatarSpawner" in the scene).
/// Assign the prefab in the Inspector.
/// </summary>
public class MetaHumanSpawner : MonoBehaviour
{
    [Header("Prefab")]
    [Tooltip("Drag your combined Body+Face prefab here")]
    public GameObject metaHumanPrefab;

    [Header("Spawn Settings")]
    public Vector3 spawnPosition = Vector3.zero;
    public Vector3 spawnRotation = Vector3.zero;

    private GameObject _spawnedAvatar;

    void Start()
    {
        SpawnAvatar();
    }

    public void SpawnAvatar()
    {
        if (metaHumanPrefab == null)
        {
            Debug.LogError("MetaHumanSpawner: No prefab assigned!");
            return;
        }

        if (_spawnedAvatar != null)
            Destroy(_spawnedAvatar);

        _spawnedAvatar = Instantiate(
            metaHumanPrefab,
            spawnPosition,
            Quaternion.Euler(spawnRotation)
        );

        _spawnedAvatar.name = "MetaHuman_Avatar";

        FixMaterials(_spawnedAvatar);

        Debug.Log("MetaHuman spawned successfully.");
    }

    /// <summary>
    /// Ensures all SkinnedMeshRenderers have their materials enabled
    /// and are not using the magenta error shader.
    /// </summary>
    private void FixMaterials(GameObject avatar)
    {
        var renderers = avatar.GetComponentsInChildren<SkinnedMeshRenderer>();

        foreach (var smr in renderers)
        {
            foreach (var mat in smr.materials)
            {
                if (mat == null) continue;

                if (mat.shader.name == "Hidden/InternalErrorShader")
                {
                    Debug.LogWarning($"Material '{mat.name}' on '{smr.gameObject.name}' " +
                                     $"is using the error shader. " +
                                     $"Please assign the correct shader for your render pipeline.");
                }
                else
                {
                    Debug.Log($"OK: '{mat.name}' on '{smr.gameObject.name}' using shader: {mat.shader.name}");
                }
            }
        }
    }
}
