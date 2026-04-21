using System;
using System.Collections.Generic;

[Serializable]
public class SentenceEvent {
    public string text;
    public float endTimeMs;
}

[Serializable]
public class VisemeTimeline {
    public string text;
    public float durationMs;
    public List<VisemeEvent> visemes = new();
    public List<SentenceEvent> sentences = new();
}