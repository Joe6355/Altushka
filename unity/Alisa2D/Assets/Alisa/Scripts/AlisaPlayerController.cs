using UnityEngine;
using UnityEngine.InputSystem;

namespace AlisaGame
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Rigidbody2D), typeof(Animator), typeof(PlayerInput))]
    [RequireComponent(typeof(CapsuleCollider2D))]
    public sealed class AlisaPlayerController : MonoBehaviour
    {
        [Header("Movement")]
        [Min(0.1f)] public float moveSpeed = 37.5f / 16f;
        [Header("Graphics")]
        public SpriteRenderer visual;
        public SpriteRenderer shadow;

        static readonly int Speed = Animator.StringToHash("Speed");
        static readonly int MoveX = Animator.StringToHash("MoveX");
        static readonly int MoveY = Animator.StringToHash("MoveY");
        static readonly int Dancing = Animator.StringToHash("Dancing");
        static readonly Vector2[] Directions = {
            Vector2.right, new Vector2(1, 1), Vector2.up, new Vector2(-1, 1),
            Vector2.left, new Vector2(-1, -1), Vector2.down, new Vector2(1, -1)
        };

        Rigidbody2D body;
        Animator animator;
        Vector2 movement;
        Vector2 pendingTap;
        Vector2 facing = Vector2.down;

        public bool IsDancing { get; private set; }
        public Vector2 Facing => facing;
        public Rigidbody2D Body => body;
        public Animator Animator => animator;

        void Awake()
        {
            body = GetComponent<Rigidbody2D>();
            animator = GetComponent<Animator>();
        }

        void OnEnable() => UpdateAnimation();

        // PlayerInput sends the Gameplay action map to these methods.
        public void OnMove(InputValue value) => SetMoveInput(value.Get<Vector2>());
        public void OnDance(InputValue value)
        {
            if (value.isPressed) ToggleDance();
        }

        public void SetMoveInput(Vector2 value)
        {
            movement = Vector2.ClampMagnitude(value, 1f);
            if (movement.sqrMagnitude > 0.001f)
            {
                pendingTap = movement;
                IsDancing = false;
                int octant = (Mathf.RoundToInt(Mathf.Atan2(movement.y, movement.x) * Mathf.Rad2Deg / 45f) + 8) % 8;
                facing = Directions[octant];
            }
        }

        public void ToggleDance()
        {
            if (movement.sqrMagnitude > 0.001f) return;
            pendingTap = Vector2.zero;
            IsDancing = !IsDancing;
        }

        void Update() => UpdateAnimation();

        void FixedUpdate()
        {
            // Keep a brief tap for one physics step, even if released between two steps.
            Vector2 input = movement.sqrMagnitude > 0.001f ? movement : pendingTap;
            pendingTap = Vector2.zero;
            body.linearVelocity = IsDancing ? Vector2.zero : input * moveSpeed;
        }

        void UpdateAnimation()
        {
            if (animator == null) return;
            animator.SetFloat(MoveX, facing.x);
            animator.SetFloat(MoveY, facing.y);
            animator.SetFloat(Speed, IsDancing ? 0f : Mathf.Max(movement.magnitude, pendingTap.magnitude));
            animator.SetBool(Dancing, IsDancing);
        }

        void LateUpdate()
        {
            Vector3 position = transform.position;
            Vector3 snapped = new Vector3(Mathf.Round(position.x * 16f) / 16f, Mathf.Round(position.y * 16f) / 16f, position.z);
            if (visual != null)
            {
                visual.transform.position = snapped;
                // The current side revision is drawn facing right. Other views have their own cels.
                visual.flipX = !IsDancing && facing == Vector2.left;
                visual.sortingOrder = Mathf.RoundToInt(-position.y * 100f);
            }
            if (shadow != null)
            {
                shadow.transform.position = snapped;
                shadow.sortingOrder = Mathf.RoundToInt(-position.y * 100f) - 1;
            }
        }

        public void StopMovement()
        {
            movement = pendingTap = Vector2.zero;
            IsDancing = false;
            if (body != null) body.linearVelocity = Vector2.zero;
            UpdateAnimation();
        }

        public void OnDeviceLost(PlayerInput _) => StopMovement();
        void OnApplicationFocus(bool focused) { if (!focused) StopMovement(); }
        void OnApplicationPause(bool paused) { if (paused) StopMovement(); }
        void OnDisable() => StopMovement();
    }
}
