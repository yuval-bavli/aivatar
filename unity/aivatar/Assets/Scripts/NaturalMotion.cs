using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Adds life to the avatar: periodic blinking, subtle head sway and eye
/// micro-saccades. All rotations are applied additively in LateUpdate, on top
/// of whatever AnimClipLipSync wrote during Update, so the two never fight.
///
/// Axis conventions (measured on the MetaHuman rig via BakeMesh):
/// - Upper eyelid (FACIAL_L/R_EyelidUpperA): local +X closes the lid (both sides).
/// - Lower eyelid (FACIAL_L/R_EyelidLowerA): local -X closes (raises) the lid.
/// - Eyeball (FACIAL_L/R_Eye): local +Y = look left, local +X = look down.
/// </summary>
public class NaturalMotion : MonoBehaviour
{
    [Header("References")]
    [Tooltip("Used to detect talking (stronger head motion) and to find the rig root.")]
    public AnimClipLipSync lipSync;

    [Tooltip("Rig root to search for bones. If null, uses lipSync.animRoot.")]
    public GameObject rigRoot;

    [Header("Blinking")]
    public bool enableBlink = true;
    [Tooltip("Random seconds between blinks.")]
    public Vector2 blinkInterval = new Vector2(2.0f, 5.5f);
    [Range(10f, 60f)] public float upperLidCloseAngle = 38f;
    [Range(0f, 20f)] public float lowerLidCloseAngle = 8f;
    [Tooltip("Seconds for lid to close / stay closed / reopen.")]
    public float blinkCloseTime = 0.07f;
    public float blinkHoldTime = 0.04f;
    public float blinkOpenTime = 0.13f;
    [Range(0f, 1f)] public float doubleBlinkChance = 0.12f;

    [Header("Head sway")]
    public bool enableHeadSway = true;
    [Tooltip("Degrees of Perlin sway when idle.")]
    public float idleSwayDegrees = 0.35f;
    [Tooltip("Degrees of Perlin sway while talking.")]
    public float talkSwayDegrees = 1.0f;
    [Tooltip("Sway speed (noise frequency) when idle.")]
    public float idleSwaySpeed = 0.12f;
    [Tooltip("Sway speed while talking.")]
    public float talkSwaySpeed = 0.22f;
    [Tooltip("How much of the sway goes to neck_01 / neck_02 (head gets the rest).")]
    [Range(0f, 1f)] public float neckShare = 0.4f;

    [Header("Eye micro-movement")]
    public bool enableEyeSaccades = true;
    [Tooltip("Max gaze wander in degrees (yaw, pitch).")]
    public Vector2 saccadeRange = new Vector2(2.0f, 1.0f);
    public Vector2 saccadeInterval = new Vector2(0.8f, 3.0f);
    [Tooltip("Degrees/sec the eye moves toward a new gaze target.")]
    public float saccadeSpeed = 60f;

    // --- bone groups (each may have several instances across duplicate skeletons) ---
    private readonly List<Transform> _heads = new List<Transform>();
    private readonly List<Transform> _neck1s = new List<Transform>();
    private readonly List<Transform> _neck2s = new List<Transform>();
    private readonly List<Transform> _upperLids = new List<Transform>();
    private readonly List<Transform> _lowerLids = new List<Transform>();
    private readonly List<Transform> _eyes = new List<Transform>();

    // Base-pose bookkeeping: lip sync rewrites bones every frame; if it ever
    // doesn't, we must not accumulate our own offset. We remember the exact
    // rotation we wrote last frame — if the bone still has it, nobody else
    // wrote and we reuse the remembered base instead of re-capturing.
    private class DrivenBone
    {
        public Transform bone;
        public Quaternion lastWritten;
        public Quaternion base_;
        public bool hasLast;
    }
    private readonly List<DrivenBone> _driven = new List<DrivenBone>();
    private readonly Dictionary<Transform, DrivenBone> _drivenMap = new Dictionary<Transform, DrivenBone>();

    // Blink state
    private float _blinkTimer;
    private float _blinkPhase = -1f; // <0 = not blinking, else seconds into blink
    private bool _queuedDoubleBlink;

    // Head sway state
    private float _swayAmp;
    private float _swayAmpVel;
    private float _noiseT;
    private float _seedA, _seedB, _seedC;

    // Saccade state
    private float _saccadeTimer;
    private Vector2 _gazeTarget;  // (yawDeg, pitchDeg)
    private Vector2 _gazeCurrent;

    void Start()
    {
        if (lipSync == null) lipSync = GetComponent<AnimClipLipSync>();
        var root = rigRoot != null ? rigRoot
                 : (lipSync != null && lipSync.animRoot != null ? lipSync.animRoot : null);
        if (root == null)
        {
            Debug.LogError("[NaturalMotion] No rig root (assign rigRoot or lipSync.animRoot).");
            enabled = false;
            return;
        }

        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            switch (t.name)
            {
                case "head": _heads.Add(t); break;
                case "neck_01": _neck1s.Add(t); break;
                case "neck_02": _neck2s.Add(t); break;
                case "FACIAL_L_EyelidUpperA":
                case "FACIAL_R_EyelidUpperA": _upperLids.Add(t); break;
                case "FACIAL_L_EyelidLowerA":
                case "FACIAL_R_EyelidLowerA": _lowerLids.Add(t); break;
                case "FACIAL_L_Eye":
                case "FACIAL_R_Eye": _eyes.Add(t); break;
            }
        }

        RegisterDriven(_heads);
        RegisterDriven(_neck1s);
        RegisterDriven(_neck2s);
        RegisterDriven(_upperLids);
        RegisterDriven(_lowerLids);
        RegisterDriven(_eyes);

        _seedA = Random.value * 100f;
        _seedB = Random.value * 100f;
        _seedC = Random.value * 100f;
        _blinkTimer = Random.Range(blinkInterval.x, blinkInterval.y);
        _saccadeTimer = Random.Range(saccadeInterval.x, saccadeInterval.y);

        Debug.Log($"[NaturalMotion] Ready: heads={_heads.Count} necks={_neck1s.Count}+{_neck2s.Count} " +
                  $"upperLids={_upperLids.Count} lowerLids={_lowerLids.Count} eyes={_eyes.Count}");
    }

    private void RegisterDriven(List<Transform> bones)
    {
        foreach (var b in bones)
        {
            if (b == null || _drivenMap.ContainsKey(b)) continue;
            var d = new DrivenBone { bone = b };
            _driven.Add(d);
            _drivenMap.Add(b, d);
        }
    }

    void LateUpdate()
    {
        float dt = Time.deltaTime;
        if (dt <= 0f) return;

        // Capture base pose: what the lip sync (or rest pose) put on the bone
        // this frame, with our previous offset stripped if nobody overwrote it.
        foreach (var d in _driven)
        {
            var cur = d.bone.localRotation;
            if (!d.hasLast || !QuaternionApprox(cur, d.lastWritten))
                d.base_ = cur;           // someone (lip sync) wrote a fresh pose
            // else: keep previous base — our own write is still on the bone
        }

        bool talking = lipSync != null && lipSync.isLipSyncPlaying;

        UpdateBlink(dt);
        float blinkWeight = CurrentBlinkWeight();

        // --- head / neck sway ---
        if (enableHeadSway && _heads.Count > 0)
        {
            float targetAmp = talking ? talkSwayDegrees : idleSwayDegrees;
            _swayAmp = Mathf.SmoothDamp(_swayAmp, targetAmp, ref _swayAmpVel, 0.8f);
            _noiseT += dt * (talking ? talkSwaySpeed : idleSwaySpeed);

            float nod  = (Mathf.PerlinNoise(_seedA, _noiseT) - 0.5f) * 2f * _swayAmp;        // pitch
            float turn = (Mathf.PerlinNoise(_seedB, _noiseT) - 0.5f) * 2f * _swayAmp;        // yaw
            float tilt = (Mathf.PerlinNoise(_seedC, _noiseT) - 0.5f) * 2f * _swayAmp * 0.6f; // roll

            // World-space delta so behaviour is independent of bone axis conventions
            Quaternion headDelta = Quaternion.Euler(nod * (1f - neckShare), turn * (1f - neckShare), tilt * (1f - neckShare));
            Quaternion neckDelta = Quaternion.Euler(nod * neckShare * 0.6f, turn * neckShare * 0.6f, tilt * neckShare * 0.6f);
            Quaternion neck2Delta = Quaternion.Euler(nod * neckShare * 0.4f, turn * neckShare * 0.4f, tilt * neckShare * 0.4f);

            ApplyWorldDelta(_heads, headDelta);
            ApplyWorldDelta(_neck1s, neckDelta);
            ApplyWorldDelta(_neck2s, neck2Delta);
        }

        // --- blink (local axes, measured) ---
        if (enableBlink && blinkWeight > 0.001f)
        {
            ApplyLocalDelta(_upperLids, Quaternion.Euler(upperLidCloseAngle * blinkWeight, 0f, 0f));
            ApplyLocalDelta(_lowerLids, Quaternion.Euler(-lowerLidCloseAngle * blinkWeight, 0f, 0f));
        }

        // --- eye saccades ---
        if (enableEyeSaccades && _eyes.Count > 0)
        {
            _saccadeTimer -= dt;
            if (_saccadeTimer <= 0f)
            {
                _saccadeTimer = Random.Range(saccadeInterval.x, saccadeInterval.y);
                // Bias toward center so she keeps "looking at" the user
                _gazeTarget = new Vector2(
                    Random.Range(-saccadeRange.x, saccadeRange.x) * Random.value,
                    Random.Range(-saccadeRange.y, saccadeRange.y) * Random.value);
            }
            _gazeCurrent = Vector2.MoveTowards(_gazeCurrent, _gazeTarget, saccadeSpeed * dt);
            // local +Y = look left, local +X = look down
            ApplyLocalDelta(_eyes, Quaternion.Euler(_gazeCurrent.y, _gazeCurrent.x, 0f));
        }

        // Remember exactly what we wrote so next frame we can tell whether
        // the lip sync refreshed the pose underneath us.
        foreach (var d in _driven)
        {
            d.lastWritten = d.bone.localRotation;
            d.hasLast = true;
        }
    }

    private void ApplyLocalDelta(List<Transform> bones, Quaternion delta)
    {
        foreach (var b in bones)
        {
            if (b == null) continue;
            var d = _drivenMap[b];
            b.localRotation = d.base_ * delta;
        }
    }

    private void ApplyWorldDelta(List<Transform> bones, Quaternion worldDelta)
    {
        foreach (var b in bones)
        {
            if (b == null) continue;
            var d = _drivenMap[b];
            b.localRotation = d.base_;
            b.rotation = worldDelta * b.rotation;
        }
    }

    private void UpdateBlink(float dt)
    {
        if (!enableBlink) { _blinkPhase = -1f; return; }

        if (_blinkPhase < 0f)
        {
            _blinkTimer -= dt;
            if (_blinkTimer <= 0f)
            {
                _blinkPhase = 0f;
                _queuedDoubleBlink = Random.value < doubleBlinkChance;
            }
            return;
        }

        _blinkPhase += dt;
        float total = blinkCloseTime + blinkHoldTime + blinkOpenTime;
        if (_blinkPhase >= total)
        {
            _blinkPhase = -1f;
            if (_queuedDoubleBlink)
            {
                _blinkTimer = 0.18f; // quick second blink
                _queuedDoubleBlink = false;
            }
            else
            {
                _blinkTimer = Random.Range(blinkInterval.x, blinkInterval.y);
            }
        }
    }

    /// <summary>0 = eyes open, 1 = fully closed, eased.</summary>
    private float CurrentBlinkWeight()
    {
        if (_blinkPhase < 0f) return 0f;
        float t = _blinkPhase;
        if (t < blinkCloseTime)
        {
            float u = t / blinkCloseTime;
            return Mathf.SmoothStep(0f, 1f, u);
        }
        t -= blinkCloseTime;
        if (t < blinkHoldTime) return 1f;
        t -= blinkHoldTime;
        float v = Mathf.Clamp01(t / blinkOpenTime);
        return 1f - Mathf.SmoothStep(0f, 1f, v);
    }

    private static bool QuaternionApprox(Quaternion a, Quaternion b)
    {
        return Mathf.Abs(Quaternion.Dot(a, b)) > 0.999999f;
    }
}
