using System;
using System.Collections.Generic;

[Serializable]
public class VisemeTimeline {
    public string text;
    public float durationMs;
    public List<VisemeEvent> visemes = new List<VisemeEvent>();
}