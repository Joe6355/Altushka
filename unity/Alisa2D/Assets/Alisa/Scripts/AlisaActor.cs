using UnityEngine;

namespace AlisaGame
{
    [RequireComponent(typeof(Animator))]
    public sealed class AlisaActor : MonoBehaviour
    {
        public AlisaAnimationLibrary library;
        public SpriteRenderer visual;
        public Animator Animator { get; private set; }
        public AlisaAnimationLibrary.Entry Current { get; private set; }
        public bool Paused { get; private set; }
        public float PlaybackSpeed { get; private set; } = 1f;
        static readonly int AnimationIndex = UnityEngine.Animator.StringToHash("AnimationIndex");

        public float TimeInClip
        {
            get
            {
                if (Current == null || Animator == null) return 0;
                var state = Animator.GetCurrentAnimatorStateInfo(0);
                return Current.loop
                    ? Mathf.Repeat(state.normalizedTime, 1f) * Current.Duration
                    : Mathf.Clamp01(state.normalizedTime) * Current.Duration;
            }
        }

        void Awake() => Animator = GetComponent<Animator>();

        void Start()
        {
            if (Current == null && library != null) Select(library.defaultKey);
        }

        public void Select(string key)
        {
            var entry = library != null ? library.Find(key) : null;
            if (entry == null) return;
            if (Animator == null) Animator = GetComponent<Animator>();
            Current = entry;
            Animator.SetInteger(AnimationIndex, entry.id);
            Animator.Play(entry.StateHash, 0, 0f);
            Animator.Update(0f);
            ApplySpeed();
        }

        public void SetPaused(bool paused)
        {
            Paused = paused;
            ApplySpeed();
        }

        public void SetSpeed(float value)
        {
            PlaybackSpeed = Mathf.Clamp(value, 0.1f, 2f);
            ApplySpeed();
        }

        void ApplySpeed()
        {
            if (Animator != null) Animator.speed = Paused ? 0f : PlaybackSpeed;
        }

        public void Seek(float seconds)
        {
            if (Current == null || Current.Duration <= 0) return;
            // Leave a non-looping clip on its last cel rather than entering another state.
            float time = Mathf.Clamp(seconds, 0f, Mathf.Max(0f, Current.Duration - 0.0001f));
            Animator.Play(Current.StateHash, 0, time / Current.Duration);
            Animator.Update(0f);
        }

        public void Step(int delta)
        {
            if (Current == null) return;
            int frame = Current.FrameAt(TimeInClip);
            int count = Current.frames.Length;
            int target = Current.loop ? (frame + delta + count) % count : Mathf.Clamp(frame + delta, 0, count - 1);
            SetPaused(true);
            Seek(Current.FrameTime(target) + 0.00001f);
        }
    }
}
