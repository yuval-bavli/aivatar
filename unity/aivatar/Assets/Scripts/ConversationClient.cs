using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

/// <summary>
/// Connects to the aivatar_app orchestrator (ws://127.0.0.1:5124).
/// Receives speak/status messages, plays audio+visemes via the attached LipSync controller.
///
/// Speak messages are queued so the orchestrator can pipeline multiple sentence segments
/// without waiting — each segment plays immediately after the previous one finishes,
/// and a "done" acknowledgement is sent for every segment.
///
/// Sends "stop" on Esc or the Stop button.
/// </summary>
[DisallowMultipleComponent]
public class ConversationClient : MonoBehaviour
{
    private const string TAG = "ConversationClient";
    private static ConversationClient _instance;

    [Header("Orchestrator")]
    public string orchestratorUrl = "ws://127.0.0.1:5124";

    [Header("References")]
    public LipSyncBase lipSyncController;

    [Header("UI (optional)")]
    public Text statusLabel;

    // ── DTOs ─────────────────────────────────────────────────────────────────

    [Serializable]
    private class TypedMessage { public string type; }

    [Serializable]
    private class SpeakMessage
    {
        public string                               type;
        public string                               audio_base64;
        public int                                  sample_rate;
        public float                                duration_ms;
        public AudioVisemeDecoder.VisemeEventData[] viseme_events;
    }

    [Serializable]
    private class StatusMessage { public string type; public string state; }

    // ── Events ───────────────────────────────────────────────────────────────

    public event Action<string> OnStateChanged;

    // ── State ─────────────────────────────────────────────────────────────────

    private ClientWebSocket               _ws;
    private CancellationTokenSource       _cts;
    private readonly ConcurrentQueue<string> _inbox = new();
    private SemaphoreSlim                 _sendLock = new(1, 1);
    private AudioSource                   _audioSource;

    // Speak queue — supports pipelined multi-segment replies
    private readonly Queue<SpeakMessage>  _speakQueue = new();
    private bool                          _isPlaying;
    private bool                          _playbackStarted;
    private int                           _speakCount;

    private int                           _connectAttempt;

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    private void Awake()
    {
        if (_instance != null)
        {
            AivatarLogger.Warn(TAG, "Duplicate ConversationClient detected — destroying this GameObject");
            Destroy(gameObject);
            return;
        }
        _instance = this;

        if (lipSyncController == null)
        {
            AivatarLogger.Error(TAG, "lipSyncController is not assigned — cannot monitor playback");
            enabled = false;
            return;
        }
        _audioSource = lipSyncController.GetComponent<AudioSource>();
        AivatarLogger.Log(TAG, $"Awake — orchestratorUrl={orchestratorUrl}");
    }

    private void Start()
    {
        AivatarLogger.Log(TAG, "Start — launching connect loop");
        _cts = new CancellationTokenSource();
        _ = ConnectLoopAsync();
    }

    private void Update()
    {
        // Dispatch messages queued by the receive background task
        while (_inbox.TryDequeue(out var raw))
            HandleMessage(raw);

        // Playback state machine:
        // • If playing and audio has started then stopped → send done, try next in queue.
        // • If not playing and queue has items → start next.
        if (_isPlaying)
        {
            if (_audioSource.isPlaying)
            {
                _playbackStarted = true;
            }
            else if (_playbackStarted)
            {
                _isPlaying = false;
                _playbackStarted = false;
                AivatarLogger.Log(TAG, $"[speak#{_speakCount}] AudioSource finished — sending done");
                _ = SendJsonAsync("{\"type\":\"done\"}");

                // Start next queued segment immediately if available
                TryStartNextSegment();
            }
        }
        else
        {
            // Not currently playing — start next if queued
            TryStartNextSegment();
        }

        if (Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame)
        {
            AivatarLogger.Log(TAG, "Esc key pressed — stopping session");
            Stop();
        }
    }

    private void OnDestroy()
    {
        if (_instance == this) _instance = null;
        AivatarLogger.Log(TAG, "OnDestroy — stopping session");
        StopSession();
    }

    // ── Connection ────────────────────────────────────────────────────────────

    private async Task ConnectLoopAsync()
    {
        while (!_cts.IsCancellationRequested)
        {
            _connectAttempt++;
            AivatarLogger.Log(TAG, $"Connection attempt #{_connectAttempt} -> {orchestratorUrl}");
            _ws = new ClientWebSocket();
            try
            {
                var sw = Stopwatch.StartNew();
                await _ws.ConnectAsync(new Uri(orchestratorUrl), _cts.Token);
                AivatarLogger.Log(TAG,
                    $"Connected to orchestrator (attempt #{_connectAttempt}, {sw.ElapsedMilliseconds} ms)");
                await ReceiveLoopAsync();
                AivatarLogger.Log(TAG, "Receive loop exited — will reconnect");
            }
            catch (OperationCanceledException)
            {
                AivatarLogger.Log(TAG, "Connect loop cancelled — exiting");
                return;
            }
            catch (Exception e)
            {
                AivatarLogger.Warn(TAG,
                    $"Connection failed (attempt #{_connectAttempt}): {e.Message} — retrying in 3 s");
                _ws?.Dispose();
                _ws = null;
                try { await Task.Delay(3000, _cts.Token); }
                catch (OperationCanceledException) { return; }
            }
        }
    }

    private async Task ReceiveLoopAsync()
    {
        var chunk     = new byte[64 * 1024];
        var assembled = new List<byte>(1024 * 1024);
        int msgCount  = 0;

        AivatarLogger.Log(TAG, "Receive loop started");

        while (_ws.State == WebSocketState.Open && !_cts.IsCancellationRequested)
        {
            assembled.Clear();
            WebSocketReceiveResult result;
            int chunks = 0;
            do
            {
                result = await _ws.ReceiveAsync(new ArraySegment<byte>(chunk), _cts.Token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    AivatarLogger.Log(TAG, $"WebSocket close frame received after {msgCount} messages");
                    return;
                }
                assembled.AddRange(new ArraySegment<byte>(chunk, 0, result.Count));
                chunks++;
            }
            while (!result.EndOfMessage);

            msgCount++;
            int totalBytes = assembled.Count;
            var raw = Encoding.UTF8.GetString(assembled.ToArray());

            var logPreview = raw.Length > 200
                ? raw.Substring(0, 200) + $"... ({raw.Length} chars total, {chunks} chunks)"
                : raw;
            AivatarLogger.Log(TAG, $"[msg#{msgCount}] Received {totalBytes} bytes: {logPreview}");

            _inbox.Enqueue(raw);
        }

        AivatarLogger.Log(TAG, $"Receive loop ended — ws.State={_ws?.State} total_msgs={msgCount}");
    }

    // ── Message handling (main thread) ────────────────────────────────────────

    private void HandleMessage(string raw)
    {
        try
        {
            var typed = JsonUtility.FromJson<TypedMessage>(raw);
            switch (typed?.type)
            {
                case "speak":
                    var speak = JsonUtility.FromJson<SpeakMessage>(raw);
                    AivatarLogger.Log(TAG,
                        $"[speak] Queuing segment — sample_rate={speak?.sample_rate} " +
                        $"duration_ms={speak?.duration_ms:F0} " +
                        $"visemes={speak?.viseme_events?.Length ?? 0} " +
                        $"audio_b64_len={speak?.audio_base64?.Length ?? 0}");
                    if (speak != null)
                        _speakQueue.Enqueue(speak);
                    break;

                case "status":
                    var status = JsonUtility.FromJson<StatusMessage>(raw);
                    AivatarLogger.Log(TAG, $"[status] Orchestrator state -> {status?.state}");
                    // On "listening", clear any stale queued segments
                    if (status?.state == "listening")
                        _speakQueue.Clear();
                    SetStatusLabel(status?.state ?? "");
                    break;

                case "error":
                    AivatarLogger.Error(TAG, $"[error] Orchestrator error: {raw}");
                    break;

                default:
                    AivatarLogger.Warn(TAG, $"Unknown message type '{typed?.type}': {raw.Substring(0, Math.Min(raw.Length, 120))}");
                    break;
            }
        }
        catch (Exception e)
        {
            AivatarLogger.Error(TAG, "Parse error", e);
        }
    }

    // ── Speak queue management (called from Update on main thread) ────────────

    private void TryStartNextSegment()
    {
        if (_isPlaying || _speakQueue.Count == 0)
            return;

        var msg = _speakQueue.Dequeue();
        StartSegment(msg);
    }

    private void StartSegment(SpeakMessage msg)
    {
        _speakCount++;
        AivatarLogger.Log(TAG, $"[speak#{_speakCount}] Decoding audio...");

        var sw = Stopwatch.StartNew();
        AudioClip clip;
        VisemeTimeline timeline;
        try
        {
            (clip, timeline) = AudioVisemeDecoder.Decode(
                msg.audio_base64, msg.viseme_events, msg.duration_ms);
        }
        catch (Exception e)
        {
            AivatarLogger.Error(TAG, $"[speak#{_speakCount}] Audio decode failed", e);
            // Send done so the orchestrator's pending counter stays in sync
            _ = SendJsonAsync("{\"type\":\"done\"}");
            return;
        }

        AivatarLogger.Log(TAG,
            $"[speak#{_speakCount}] Decode ok — clip.length={clip.length:F3}s " +
            $"viseme_events={timeline.visemes.Count} decode_ms={sw.ElapsedMilliseconds}");

        _isPlaying = true;
        _playbackStarted = false;
        lipSyncController.Play(timeline, clip);
        AivatarLogger.Log(TAG, $"[speak#{_speakCount}] Play() called");
    }

    private void SetStatusLabel(string state)
    {
        OnStateChanged?.Invoke(state);
        if (statusLabel != null)
            statusLabel.text = state;
    }

    // ── Send ──────────────────────────────────────────────────────────────────

    private async Task SendJsonAsync(string json)
    {
        if (_ws?.State != WebSocketState.Open)
        {
            AivatarLogger.Warn(TAG, $"SendJsonAsync skipped — ws.State={_ws?.State}: {json}");
            return;
        }

        AivatarLogger.Log(TAG, $"Sending to orchestrator: {json}");
        var bytes = Encoding.UTF8.GetBytes(json);
        await _sendLock.WaitAsync(_cts.Token);
        try
        {
            await _ws.SendAsync(
                new ArraySegment<byte>(bytes),
                WebSocketMessageType.Text,
                endOfMessage: true,
                cancellationToken: _cts.Token);
            AivatarLogger.Log(TAG, $"Sent ok ({bytes.Length} bytes)");
        }
        catch (Exception e)
        {
            AivatarLogger.Error(TAG, $"Send failed: {json}", e);
        }
        finally
        {
            _sendLock.Release();
        }
    }

    // ── Stop ──────────────────────────────────────────────────────────────────

    public void Stop()
    {
        AivatarLogger.Log(TAG, "Stop() called — sending stop to orchestrator");
        _ = SendJsonAsync("{\"type\":\"stop\"}");
        StopSession();
    }

    private void StopSession()
    {
        AivatarLogger.Log(TAG, "StopSession — cancelling tasks and closing WebSocket");
        _cts?.Cancel();
        _ws?.Dispose();
        _ws = null;
        _isPlaying = false;
        _speakQueue.Clear();
        AivatarLogger.Log(TAG, "Session stopped");
    }
}
