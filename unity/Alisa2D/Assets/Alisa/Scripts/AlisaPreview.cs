using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace AlisaGame
{
    /// <summary>Animation review scene. The Animator owns the SpriteRenderer's sprite.</summary>
    public sealed class AlisaPreview : MonoBehaviour
    {
        public AlisaActor actor;
        public Camera previewCamera;
        public SpriteRenderer floor;
        public bool closeView = true;
        public bool showPanel = true;

        const float PanelWidth = 348f;
        Vector2 scroll;
        bool showArchive;
        bool movementMode;
        bool wasMoving;
        Vector2 pendingMovementTap;
        bool showFloor = true;
        Vector2 facing = Vector2.down;
        static readonly string[] DirectionNames = { "e", "ne", "n", "nw", "w", "sw", "s", "se" };
        Vector3 home;
        GUIStyle heading, body, selected, button, small;
        Texture2D panelTexture;
        float UiScale => Mathf.Clamp(Screen.height / 850f, 0.85f, 1.35f);

        void Start()
        {
            home = actor.transform.position;
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 1;
        }

        void Update()
        {
            if (Pressed(KeyCode.F1)) showPanel = !showPanel;
            if (Pressed(KeyCode.P)) actor.SetPaused(!actor.Paused);
            if (Pressed(KeyCode.Comma)) actor.Step(-1);
            if (Pressed(KeyCode.Period)) actor.Step(1);
            if (Pressed(KeyCode.R)) ResetPosition();
            if (Pressed(KeyCode.Space))
            {
                PlayClip("Front/dance_original");
                return;
            }

            Vector2 input = Vector2.zero;
            if (Held(KeyCode.A) || Held(KeyCode.LeftArrow)) input.x--;
            if (Held(KeyCode.D) || Held(KeyCode.RightArrow)) input.x++;
            if (Held(KeyCode.S) || Held(KeyCode.DownArrow)) input.y--;
            if (Held(KeyCode.W) || Held(KeyCode.UpArrow)) input.y++;
            if (input.sqrMagnitude == 0) input = pendingMovementTap;
            pendingMovementTap = Vector2.zero;
            ApplyMovementInput(input, Time.deltaTime);
        }

        public void PlayClip(string key)
        {
            movementMode = false;
            wasMoving = false;
            pendingMovementTap = Vector2.zero;
            actor.Select(key);
            actor.SetPaused(false);
        }

        public bool BufferMovementKey(KeyCode key)
        {
            switch (key)
            {
                case KeyCode.A: case KeyCode.LeftArrow: pendingMovementTap.x--; return true;
                case KeyCode.D: case KeyCode.RightArrow: pendingMovementTap.x++; return true;
                case KeyCode.W: case KeyCode.UpArrow: pendingMovementTap.y++; return true;
                case KeyCode.S: case KeyCode.DownArrow: pendingMovementTap.y--; return true;
                default: return false;
            }
        }

        public void ApplyMovementInput(Vector2 input, float deltaTime)
        {
            bool moving = input.sqrMagnitude > 0;
            bool continuingStep = moving && wasMoving && actor.Current != null
                && actor.Current.key.StartsWith("Polished/walk_");
            if (moving && (!movementMode || !wasMoving))
            {
                // Direction keys always leave clip inspection and resume normal control.
                movementMode = true;
                closeView = false;
                actor.SetPaused(false);
            }
            wasMoving = moving;
            if (!movementMode) return;
            if (moving) facing = input.normalized;
            string key = MovementKey(facing, moving);
            if (actor.Current == null || actor.Current.key != key) actor.Select(key, continuingStep);
            if (moving && !actor.Paused)
            {
                Vector3 position = actor.transform.position + (Vector3)(input.normalized * (40f / 16f) * deltaTime * actor.PlaybackSpeed);
                position.x = Mathf.Clamp(position.x, -8.5f, 8.5f);
                position.y = Mathf.Clamp(position.y, -6.6f, 2f);
                actor.transform.position = position;
            }
        }

        static bool Held(KeyCode key)
        {
#if ENABLE_INPUT_SYSTEM
            if (Keyboard.current == null) return false;
            var control = Keyboard.current[InputKey(key)];
            return control.isPressed || control.wasPressedThisFrame;
#else
            return Input.GetKey(key) || Input.GetKeyDown(key);
#endif
        }

        static bool Pressed(KeyCode key)
        {
#if ENABLE_INPUT_SYSTEM
            return Keyboard.current != null && Keyboard.current[InputKey(key)].wasPressedThisFrame;
#else
            return Input.GetKeyDown(key);
#endif
        }

#if ENABLE_INPUT_SYSTEM
        static Key InputKey(KeyCode key) => key switch
        {
            KeyCode.A => Key.A, KeyCode.D => Key.D, KeyCode.S => Key.S, KeyCode.W => Key.W,
            KeyCode.LeftArrow => Key.LeftArrow, KeyCode.RightArrow => Key.RightArrow,
            KeyCode.UpArrow => Key.UpArrow, KeyCode.DownArrow => Key.DownArrow,
            KeyCode.P => Key.P, KeyCode.R => Key.R, KeyCode.Space => Key.Space,
            KeyCode.F1 => Key.F1, KeyCode.Comma => Key.Comma, KeyCode.Period => Key.Period,
            _ => Key.None
        };
#endif

        static string MovementKey(Vector2 direction, bool moving)
        {
            int octant = (Mathf.RoundToInt(Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg / 45f) + 8) % 8;
            return "Polished/" + (moving ? "walk_" : "idle_") + DirectionNames[octant];
        }

        void ResetPosition() => actor.transform.position = home;

        void LateUpdate()
        {
            if (previewCamera == null) return;
            int nativeWidth = closeView ? 160 : 320;
            int nativeHeight = closeView ? 120 : 240;
            float left = showPanel ? (PanelWidth + 16f) * UiScale : 0f;
            float availableWidth = Mathf.Max(1, Screen.width - left);
            int scale = Mathf.Max(1, Mathf.FloorToInt(Mathf.Min(availableWidth / nativeWidth, (Screen.height - 16) / (float)nativeHeight)));
            float width = nativeWidth * scale;
            float height = nativeHeight * scale;
            previewCamera.rect = new Rect((left + (availableWidth - width) / 2f) / Screen.width,
                (Screen.height - height) / 2f / Screen.height, width / Screen.width, height / Screen.height);
            previewCamera.orthographicSize = nativeHeight / 32f;
            Vector3 target = closeView ? actor.transform.position + new Vector3(0, 42f / 16f, 0) : Vector3.zero;
            previewCamera.transform.position = new Vector3(Mathf.Round(target.x * 16) / 16f,
                Mathf.Round(target.y * 16) / 16f, -10);
            // Snap only the rendered child. The root retains smooth movement and has no accumulating rounding error.
            var root = actor.transform.position;
            actor.visual.transform.position = new Vector3(Mathf.Round(root.x * 16) / 16f, Mathf.Round(root.y * 16) / 16f, root.z);
            floor.enabled = showFloor;
            previewCamera.backgroundColor = showFloor ? new Color32(31, 34, 41, 255) : new Color32(89, 93, 103, 255);
        }

        void PrepareStyles()
        {
            if (heading != null) return;
            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            GUI.skin.font = font;
            heading = new GUIStyle(GUI.skin.label) { font = font, fontSize = 22, fontStyle = FontStyle.Bold };
            body = new GUIStyle(GUI.skin.label) { font = font, fontSize = 14, wordWrap = true };
            small = new GUIStyle(body) { fontSize = 12 };
            small.normal.textColor = new Color(0.68f, 0.72f, 0.8f);
            button = new GUIStyle(GUI.skin.button) { font = font, fontSize = 14, wordWrap = true, alignment = TextAnchor.MiddleLeft, padding = new RectOffset(10, 7, 6, 6) };
            selected = new GUIStyle(button);
            selected.normal.textColor = new Color(0.54f, 0.88f, 1f);
            panelTexture = new Texture2D(1, 1);
            panelTexture.SetPixel(0, 0, new Color(0.075f, 0.085f, 0.11f, 0.98f));
            panelTexture.Apply();
        }

        void OnGUI()
        {
            // A camera only clears its current viewport. Cover the old viewport when zoom changes.
            if (previewCamera != null)
            {
                Rect viewport = previewCamera.pixelRect;
                float top = Screen.height - viewport.yMax;
                float bottom = Screen.height - viewport.y;
                GUI.DrawTexture(new Rect(0, 0, Screen.width, top), Texture2D.blackTexture);
                GUI.DrawTexture(new Rect(0, bottom, Screen.width, Screen.height - bottom), Texture2D.blackTexture);
                GUI.DrawTexture(new Rect(0, top, viewport.x, viewport.height), Texture2D.blackTexture);
                GUI.DrawTexture(new Rect(viewport.xMax, top, Screen.width - viewport.xMax, viewport.height), Texture2D.blackTexture);
            }
            // Keep brief GUI key presses until Update, and keep arrows out of the timeline slider.
            var inputEvent = Event.current;
            if (inputEvent.type == EventType.KeyDown && BufferMovementKey(inputEvent.keyCode)) inputEvent.Use();
            if (!showPanel)
            {
                GUI.Label(new Rect(12, 12, 280, 28), "F1 — показать управление");
                return;
            }
            PrepareStyles();
            Matrix4x4 saved = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(Vector3.one * UiScale);
            float height = Screen.height / UiScale;
            GUI.DrawTexture(new Rect(0, 0, PanelWidth + 8, height), panelTexture);
            GUILayout.BeginArea(new Rect(14, 12, PanelWidth - 20, height - 22));
            GUILayout.Label("АЛИСА / просмотр", heading);
            GUILayout.Label("36×86 px  ·  Point  ·  Animator", small);
            GUILayout.Space(8);
            if (actor.Current != null)
            {
                var entry = actor.Current;
                GUILayout.Label(entry.label, body);
                GUILayout.Label($"Кадр {entry.FrameAt(actor.TimeInClip) + 1}/{entry.frames.Length}    {actor.TimeInClip:0.00} / {entry.Duration:0.00} с", small);
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("◀ кадр", GUILayout.Height(28))) actor.Step(-1);
                if (GUILayout.Button(actor.Paused ? "▶ играть" : "Ⅱ пауза", GUILayout.Height(28))) actor.SetPaused(!actor.Paused);
                if (GUILayout.Button("кадр ▶", GUILayout.Height(28))) actor.Step(1);
                GUILayout.EndHorizontal();
                float time = GUILayout.HorizontalSlider(actor.TimeInClip, 0f, Mathf.Max(0.001f, entry.Duration));
                if (Mathf.Abs(time - actor.TimeInClip) > 0.002f)
                {
                    actor.SetPaused(true);
                    actor.Seek(time);
                }
            }
            GUILayout.BeginHorizontal();
            GUILayout.Label("Скорость", small, GUILayout.Width(67));
            foreach (float speed in new[] { 0.25f, 0.5f, 1f })
                if (GUILayout.Button((Mathf.Approximately(actor.PlaybackSpeed, speed) ? "● " : "") + speed.ToString("0.##") + "×", GUILayout.Height(25))) actor.SetSpeed(speed);
            GUILayout.EndHorizontal();
            closeView = GUILayout.Toggle(closeView, "Крупный план");
            showFloor = GUILayout.Toggle(showFloor, "Игровой фон");
            GUILayout.Label("WASD / стрелки — идти; без клавиш — idle", small);
            GUILayout.Label(movementMode ? "Управление с клавиатуры" : "Просмотр клипа — WASD включит ходьбу", small);
            if (movementMode)
                GUILayout.Label("Новые idle и ходьба в 8 направлениях. Поворот сохраняет фазу шага. Space — исходный танец.", small);
            GUILayout.Label("Space — танец · P — пауза · , / . — кадры\nR — вернуть в центр · F1 — скрыть панель", small);
            GUILayout.Space(6);
            showArchive = GUILayout.Toggle(showArchive, "Показать предыдущие эксперименты");
            scroll = GUILayout.BeginScrollView(scroll);
            string group = null;
            foreach (var entry in actor.library.entries)
            {
                if (entry.historical && !showArchive) continue;
                if (group != entry.group)
                {
                    group = entry.group;
                    GUILayout.Space(8);
                    GUILayout.Label(group, small);
                }
                bool active = actor.Current == entry;
                if (GUILayout.Button((active ? "● " : "") + entry.label, active ? selected : button, GUILayout.MinHeight(30)))
                {
                    PlayClip(entry.key);
                    ResetPosition();
                }
            }
            GUILayout.EndScrollView();
            if (actor.Current != null && !string.IsNullOrEmpty(actor.Current.note))
            {
                GUILayout.Space(6);
                GUILayout.Label(actor.Current.note, small);
            }
            GUILayout.EndArea();
            GUI.matrix = saved;
        }

        void OnDestroy()
        {
            if (panelTexture != null) Destroy(panelTexture);
        }
    }
}
