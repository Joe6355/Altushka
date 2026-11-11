using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AlisaGame.Editor
{
    [InitializeOnLoad]
    internal static class AlisaGameplayCheck
    {
        const string RunKey = "Alisa.RunGameplayCheck";
        static AlisaPlayerController player;
        static Keyboard testKeyboard, previousKeyboard;
        static Camera camera;
        static Vector2 home, before, homeFacing;
        static Vector3 cameraPosition;
        static int phase, direction;
        static float beforeTurn;
        static double next, timeout;
        static readonly Key[][] Keys = {
            new[] { Key.RightArrow }, new[] { Key.RightArrow, Key.UpArrow }, new[] { Key.UpArrow },
            new[] { Key.LeftArrow, Key.UpArrow }, new[] { Key.LeftArrow }, new[] { Key.LeftArrow, Key.DownArrow },
            new[] { Key.DownArrow }, new[] { Key.RightArrow, Key.DownArrow }
        };

        static AlisaGameplayCheck() => EditorApplication.playModeStateChanged += OnPlayMode;

        internal static void VerifyStructure()
        {
            var scene = SceneManager.GetSceneByPath(AlisaGameSetup.ScenePath);
            bool close = !scene.isLoaded;
            if (close) scene = EditorSceneManager.OpenScene(AlisaGameSetup.ScenePath, OpenSceneMode.Additive);
            try
            {
                var roots = scene.GetRootGameObjects();
                Require(new[] { "World", "Actors", "Main Camera" }.All(name => roots.Any(o => o.name == name)), "Gameplay hierarchy is not organised.");
                var behaviours = roots.SelectMany(o => o.GetComponentsInChildren<MonoBehaviour>(true)).ToArray();
                Require(behaviours.All(b => b != null && b.GetType().Name != "AlisaPreview"), "Legacy preview or a missing script remains in the scene.");
                var players = roots.SelectMany(o => o.GetComponentsInChildren<AlisaPlayerController>(true)).ToArray();
                Require(players.Length == 1 && PrefabUtility.IsPartOfPrefabInstance(players[0]), "Exactly one player prefab is required.");
                var cameras = roots.SelectMany(o => o.GetComponentsInChildren<Camera>(true)).Where(c => c.enabled).ToArray();
                Require(cameras.Length == 1 && cameras[0].rect == new Rect(0, 0, 1, 1), "A single full-viewport camera is required.");
                Require(cameras[0].clearFlags == CameraClearFlags.SolidColor, "Camera must clear the full image.");
                var pixels = cameras[0].GetComponent<PixelPerfectCamera>();
                Require(pixels != null && pixels.assetsPPU == 16 && pixels.cropFrame == PixelPerfectCamera.CropFrame.None, "Pixel Perfect Camera settings are incorrect.");
                var input = players[0].GetComponent<PlayerInput>();
                Require(input.actions != null && input.defaultActionMap == "Gameplay" && input.notificationBehavior == PlayerNotifications.SendMessages, "PlayerInput is not connected.");
                Require(input.actions.FindAction("Gameplay/Move", true).bindings.Any(b => b.path == "<Keyboard>/w"), "WASD binding is missing.");
                Require(input.actions.FindAction("Gameplay/Dance", true).bindings.Any(b => b.path == "<Keyboard>/space"), "Dance binding is missing.");
                var body = players[0].GetComponent<Rigidbody2D>();
                Require(body.bodyType == RigidbodyType2D.Dynamic && body.gravityScale == 0 && players[0].GetComponent<CapsuleCollider2D>() != null, "Player physics is not connected.");
                var controller = players[0].GetComponent<Animator>().runtimeAnimatorController as AnimatorController;
                var states = controller.layers[0].stateMachine.states.Select(s => s.state).ToArray();
                Require(new[] { "Idle", "Walk", "Dance" }.All(name => states.Any(s => s.name == name)), "Gameplay states are missing.");
                Require(controller.parameters.All(p => p.name != "AnimationIndex"), "The clip-browser parameter is still in the game Animator.");
                foreach (string name in new[] { "Idle", "Walk" })
                    Require(states.Single(s => s.name == name).motion is BlendTree tree && tree.children.Length == 8, "Directional animation tree is missing.");
            }
            finally { if (close) EditorSceneManager.CloseScene(scene, true); }
        }

        [MenuItem("Alisa/Проверить игровое управление (Play)")]
        public static void StartCheck()
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode, "Stop Play mode before starting this check.");
            AlisaProjectBuilder.OpenGame();
            VerifyStructure();
            SessionState.SetBool(RunKey, true);
            EditorApplication.isPlaying = true;
        }

        static void OnPlayMode(PlayModeStateChange state)
        {
            if (state == PlayModeStateChange.EnteredPlayMode && SessionState.GetBool(RunKey, false))
            {
                SessionState.SetBool(RunKey, false);
                phase = -1;
                next = EditorApplication.timeSinceStartup + .2;
                timeout = EditorApplication.timeSinceStartup + 20;
                EditorApplication.update += Tick;
            }
            else if (state == PlayModeStateChange.ExitingPlayMode) Cleanup();
        }

        static void Queue(params Key[] keys)
        {
            InputSystem.QueueStateEvent(testKeyboard, new KeyboardState(keys));
            InputSystem.Update();
        }

        static void RequireClip(int direction, bool walking)
        {
            var clip = player.Animator.GetCurrentAnimatorClipInfo(0).OrderByDescending(c => c.weight).First().clip;
            string expected = AlisaGameSetup.ClipKey(direction, walking).Replace("/", "__");
            Require(clip.name == expected, "Expected " + expected + ", received " + clip.name);
        }

        static void Tick()
        {
            try
            {
                Require(EditorApplication.timeSinceStartup < timeout, "Gameplay check timed out.");
                if (EditorApplication.timeSinceStartup < next) return;
                if (phase == -1)
                {
                    player = UnityEngine.Object.FindAnyObjectByType<AlisaPlayerController>();
                    Require(player != null && player.Body != null, "Player did not initialise.");
                    camera = Camera.main;
                    cameraPosition = camera.transform.position;
                    home = player.Body.position;
                    homeFacing = player.Facing;
                    previousKeyboard = Keyboard.current;
                    testKeyboard = InputSystem.AddDevice<Keyboard>();
                    player.GetComponent<PlayerInput>().SwitchCurrentControlScheme("Keyboard", testKeyboard);
                    direction = 0; before = player.Body.position; Queue(Keys[0]); phase = 0;
                }
                else
                {
                    Require(camera.rect == new Rect(0, 0, 1, 1) && camera.transform.position == cameraPosition, "Movement changed the camera viewport or position.");
                    if (phase == 0)
                    {
                        Vector2 wanted = AlisaGameSetup.Directions[direction].normalized;
                        Require(Vector2.Distance(player.Body.linearVelocity, wanted * player.moveSpeed) < .02f, "Wrong movement speed or direction.");
                        Require(Vector2.Dot(player.Body.position - before, wanted) > .04f, "The actual player did not move.");
                        Require(player.Animator.GetCurrentAnimatorStateInfo(0).IsName("Walk"), "Movement did not enter Walk.");
                        RequireClip(direction, true);
                        Require(player.visual.flipX == (direction == 4), "Left side mirroring is incorrect.");
                        direction++;
                        if (direction < 8) { before = player.Body.position; Queue(Keys[direction]); }
                        else
                        {
                            beforeTurn = player.Animator.GetCurrentAnimatorStateInfo(0).normalizedTime;
                            Queue(Keys[5]);
                            phase = 8;
                        }
                    }
                    else if (phase == 8)
                    {
                        var walk = player.Animator.GetCurrentAnimatorStateInfo(0);
                        Require(walk.IsName("Walk") && walk.normalizedTime > beforeTurn,
                            "Switching between front diagonals restarted the walking phase.");
                        RequireClip(5, true);
                        Queue(); phase = 9;
                    }
                    else if (phase == 9)
                    {
                        Require(player.Animator.GetCurrentAnimatorStateInfo(0).IsName("Idle"), "Left diagonal did not settle in Idle.");
                        RequireClip(5, false);
                        Queue(Keys[7]); phase = 10;
                    }
                    else if (phase == 10)
                    {
                        RequireClip(7, true);
                        Queue(); phase = 1;
                    }
                    else if (phase == 1)
                    {
                        Require(player.Body.linearVelocity.sqrMagnitude < .0001f && player.Animator.GetCurrentAnimatorStateInfo(0).IsName("Idle"), "Release did not stop in Idle.");
                        RequireClip(7, false);
                        Queue(Key.Space); phase = 2;
                    }
                    else if (phase == 2)
                    {
                        Require(player.IsDancing && player.Animator.GetCurrentAnimatorStateInfo(0).IsName("Dance"), "Space did not enter Dance.");
                        Queue(); Queue(Key.RightArrow); phase = 3;
                    }
                    else if (phase == 3)
                    {
                        Require(!player.IsDancing && player.Animator.GetCurrentAnimatorStateInfo(0).IsName("Walk"), "Movement did not interrupt Dance.");
                        Queue(); phase = 4;
                    }
                    else if (phase == 4)
                    {
                        before = player.Body.position;
                        Queue(Key.LeftArrow); Queue(); phase = 5;
                    }
                    else if (phase == 5)
                    {
                        Require(player.Body.position.x < before.x - .001f, "A short keyboard tap was lost before the physics step.");
                        player.Body.position = new Vector2(8.3f, -2.5f); Queue(Key.RightArrow); phase = 6;
                        next = EditorApplication.timeSinceStartup + .45; return;
                    }
                    else
                    {
                        Require(player.Body.position.x > 8.4f && player.Body.position.x < 8.58f, "The boundary collider did not stop the player.");
                        player.Body.position = home; player.StopMovement();
                        player.SetMoveInput(homeFacing); player.SetMoveInput(Vector2.zero); player.StopMovement();
                        Cleanup();
                        const string result = "ALISA_GAMEPLAY_OK: real PlayerInput keyboard, 8 directions, front-diagonal phase and idles, diagonal speed, dance interruption, short taps, physics bounds and full-viewport camera verified.";
                        Directory.CreateDirectory("Library/AlisaChecks");
                        File.WriteAllText("Library/AlisaChecks/Gameplay.txt", result);
                        Debug.Log(result);
                        return;
                    }
                }
                next = EditorApplication.timeSinceStartup + .18;
            }
            catch (Exception error)
            {
                Cleanup();
                Directory.CreateDirectory("Library/AlisaChecks");
                File.WriteAllText("Library/AlisaChecks/Gameplay.txt", error.ToString());
                Debug.LogException(error);
            }
        }

        static void Cleanup()
        {
            EditorApplication.update -= Tick;
            if (testKeyboard != null && testKeyboard.added)
            {
                if (previousKeyboard != null && previousKeyboard.added && player != null)
                    player.GetComponent<PlayerInput>().SwitchCurrentControlScheme("Keyboard", previousKeyboard);
                InputSystem.RemoveDevice(testKeyboard);
                if (previousKeyboard != null && previousKeyboard.added) previousKeyboard.MakeCurrent();
            }
            testKeyboard = null;
        }

        static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
