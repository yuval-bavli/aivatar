using System;
using UnityEngine;

[CreateAssetMenu(fileName = "NewVisemeMapping", menuName = "LipSync/Viseme Mapping")]
public class VisemeMapping : ScriptableObject
{
    [Serializable]
    public struct VisemeMap
    {
        public int azureId;
        public string blendShapeName;
    }

    [Tooltip("Map Azure Viseme IDs (0-21) to your mesh's BlendShape names.")]
    public VisemeMap[] mappings;
}