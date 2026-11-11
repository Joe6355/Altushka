using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AlisaGame.Editor
{
    internal static class AlisaGameSetup
    {
        internal const string ScenePath = "Assets/Scenes/Gameplay.unity";
        internal const string PrefabPath = "Assets/Alisa/Prefabs/Alisa.prefab";
        internal const string ControllerPath = "Assets/Alisa/Animations/Alisa.controller";
        internal const string InputPath = "Assets/Alisa/Input/AlisaControls.inputactions";
        const string OldScenePath = "Assets/Scenes/AlisaPreview.unity";
        internal static readonly Vector2[] Directions = {
            Vector2.right, new Vector2(1,1), Vector2.up, new Vector2(-1,1),
            Vector2.left, new Vector2(-1,-1), Vector2.down, new Vector2(1,-1)
        };
        static readonly string[] Suffixes = { "e", "ne", "n", "nw", "w", "sw", "s", "se" };

        internal static string ClipKey(int direction, bool walking)
        {
            if (direction == 5 || direction == 7)
                return "BlenderDiagonals/" + (walking ? "walk_" : "idle_") + Suffixes[direction];
            if (direction == 0 || direction == 4)
                return walking ? "SideRevision/walk_side_right" : "Side/idle_side_right";
            return "DirectionalV3/" + (walking ? "walk_" : "idle_") + Suffixes[direction];
        }

        internal static bool Build(AlisaAnimationLibrary library, Material material, Sprite footShadow, float diagonalRate)
        {
            var existing = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (File.Exists(ScenePath) && existing != null && existing.GetComponent<AlisaPlayerController>() != null)
            {
                if (diagonalRate > 0) ConnectFrontDiagonals(library, existing, diagonalRate);
                return false;
            }
            var controller = BuildController(library);
            var controls = BuildInput();
            var prefab = BuildPrefab(library, controller, controls, material, footShadow);
            if (diagonalRate > 0) ConnectFrontDiagonals(library, prefab, diagonalRate);
            if (!File.Exists(ScenePath))
            {
                EditorSceneManager.SaveOpenScenes();
                if (File.Exists(OldScenePath))
                {
                    string error = AssetDatabase.MoveAsset(OldScenePath, ScenePath);
                    if (!string.IsNullOrEmpty(error)) throw new InvalidOperationException(error);
                }
                MigrateScene(prefab, material);
            }
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) }
                .Concat(EditorBuildSettings.scenes.Where(s => s.path != ScenePath && s.path != OldScenePath && File.Exists(s.path))).ToArray();
            return true;
        }

        static void ConnectFrontDiagonals(AlisaAnimationLibrary library, GameObject prefab, float rate)
        {
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            var states = controller.layers[0].stateMachine.states;
            var updates = new List<(BlendTree tree, ChildMotion[] children)>();
            foreach (bool walking in new[] { false, true })
            {
                string stateName = walking ? "Walk" : "Idle";
                if (!(states.Single(s => s.state.name == stateName).state.motion is BlendTree tree))
                    throw new InvalidOperationException(stateName + " directional blend tree is missing.");
                var children = tree.children;
                bool changed = false;
                foreach (int direction in new[] { 5, 7 })
                {
                    int index = Array.FindIndex(children, child => child.position == Directions[direction]);
                    if (index < 0) throw new InvalidOperationException(stateName + " front diagonal is missing.");
                    string key = ClipKey(direction, walking);
                    var entry = library.Find(key);
                    if (entry == null) throw new InvalidOperationException("Missing clip: " + key);
                    float timeScale = walking ? rate : 1f;
                    if (children[index].motion == entry.clip && children[index].timeScale == timeScale && children[index].cycleOffset == 0)
                        continue;
                    children[index].motion = entry.clip;
                    children[index].timeScale = timeScale;
                    children[index].cycleOffset = 0; // The mirrored cels already include the half-cycle offset.
                    changed = true;
                }
                if (changed) updates.Add((tree, children));
            }
            foreach (var (tree, children) in updates)
            {
                tree.children = children;
                EditorUtility.SetDirty(tree);
            }

            var player = prefab.GetComponent<AlisaPlayerController>();
            Vector2 start = new SerializedObject(player).FindProperty("startingFacing").vector2Value;
            int initialDirection = Array.IndexOf(Directions, start);
            if (initialDirection != 5 && initialDirection != 7) return;
            Sprite idle = library.Find(ClipKey(initialDirection, false)).frames[0];
            if (player.visual.sprite == idle) return;
            var contents = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                contents.GetComponent<AlisaPlayerController>().visual.sprite = idle;
                PrefabUtility.SaveAsPrefabAsset(contents, PrefabPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(contents); }
        }

        static AnimatorController BuildController(AlisaAnimationLibrary library)
        {
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (controller == null) controller = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            // Migrate the generated clip browser once. Subsequent imports preserve gameplay edits.
            if (controller.parameters.Any(p => p.name == "Speed") && !controller.parameters.Any(p => p.name == "AnimationIndex"))
                return controller;
            var root = controller.layers[0].stateMachine;
            foreach (var transition in root.anyStateTransitions) root.RemoveAnyStateTransition(transition);
            foreach (var transition in root.entryTransitions) root.RemoveEntryTransition(transition);
            foreach (var child in root.states) root.RemoveState(child.state);
            foreach (var child in root.stateMachines) root.RemoveStateMachine(child.stateMachine);
            foreach (var subasset in AssetDatabase.LoadAllAssetsAtPath(ControllerPath))
                if (subasset != controller && subasset != root) UnityEngine.Object.DestroyImmediate(subasset, true);
            controller.parameters = Array.Empty<AnimatorControllerParameter>();
            controller.AddParameter(new AnimatorControllerParameter { name = "MoveX", type = AnimatorControllerParameterType.Float });
            controller.AddParameter(new AnimatorControllerParameter { name = "MoveY", type = AnimatorControllerParameterType.Float, defaultFloat = -1 });
            controller.AddParameter("Speed", AnimatorControllerParameterType.Float);
            controller.AddParameter("Dancing", AnimatorControllerParameterType.Bool);
            var idle = root.AddState("Idle", new Vector3(240, 80));
            var walk = root.AddState("Walk", new Vector3(550, 80));
            var dance = root.AddState("Dance", new Vector3(400, 250));
            idle.motion = BuildDirections(controller, library, false);
            walk.motion = BuildDirections(controller, library, true);
            dance.motion = library.Find("Front/dance_original").clip;
            foreach (var state in new[] { idle, walk, dance }) state.writeDefaultValues = false;
            root.defaultState = idle;
            root.entryPosition = new Vector3(40, 90);
            root.anyStatePosition = new Vector3(40, 250);
            root.exitPosition = new Vector3(740, 250);
            var start = Transition(idle, walk); start.AddCondition(AnimatorConditionMode.Greater, .01f, "Speed"); start.AddCondition(AnimatorConditionMode.IfNot, 0, "Dancing");
            var stop = Transition(walk, idle); stop.AddCondition(AnimatorConditionMode.Less, .01f, "Speed");
            foreach (var state in new[] { idle, walk }) Transition(state, dance).AddCondition(AnimatorConditionMode.If, 0, "Dancing");
            var resume = Transition(dance, walk); resume.AddCondition(AnimatorConditionMode.IfNot, 0, "Dancing"); resume.AddCondition(AnimatorConditionMode.Greater, .01f, "Speed");
            var rest = Transition(dance, idle); rest.AddCondition(AnimatorConditionMode.IfNot, 0, "Dancing"); rest.AddCondition(AnimatorConditionMode.Less, .01f, "Speed");
            EditorUtility.SetDirty(controller);
            return controller;
        }

        static BlendTree BuildDirections(AnimatorController controller, AlisaAnimationLibrary library, bool walking)
        {
            var tree = new BlendTree {
                name = walking ? "Walk Directions" : "Idle Directions",
                blendType = BlendTreeType.SimpleDirectional2D, blendParameter = "MoveX", blendParameterY = "MoveY",
                useAutomaticThresholds = false
            };
            AssetDatabase.AddObjectToAsset(tree, controller);
            tree.children = Enumerable.Range(0, 8).Select(i => new ChildMotion {
                motion = DirectionalClip(library, i, walking), position = Directions[i], timeScale = 1,
                cycleOffset = walking && i == 4 ? .5f : 0f
            }).ToArray();
            return tree;
        }

        static AnimationClip DirectionalClip(AlisaAnimationLibrary library, int direction, bool walking)
        {
            var entry = library.Find(ClipKey(direction, walking));
            if (entry == null && (direction == 5 || direction == 7))
                entry = library.Find("StepContact/" + (walking ? "walk_" : "idle_") + Suffixes[direction]);
            return entry.clip;
        }

        static AnimatorStateTransition Transition(AnimatorState from, AnimatorState to)
        {
            var transition = from.AddTransition(to);
            transition.hasExitTime = false;
            transition.duration = 0;
            transition.hasFixedDuration = true;
            transition.canTransitionToSelf = false;
            return transition;
        }

        static InputActionAsset BuildInput()
        {
            if (!File.Exists(InputPath))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(InputPath));
                var asset = ScriptableObject.CreateInstance<InputActionAsset>();
                asset.name = "AlisaControls";
                var gameplay = asset.AddActionMap("Gameplay");
                var move = gameplay.AddAction("Move", InputActionType.Value, expectedControlLayout: "Vector2");
                move.AddCompositeBinding("2DVector")
                    .With("Up", "<Keyboard>/w", groups: "Keyboard").With("Down", "<Keyboard>/s", groups: "Keyboard")
                    .With("Left", "<Keyboard>/a", groups: "Keyboard").With("Right", "<Keyboard>/d", groups: "Keyboard");
                move.AddCompositeBinding("2DVector")
                    .With("Up", "<Keyboard>/upArrow", groups: "Keyboard").With("Down", "<Keyboard>/downArrow", groups: "Keyboard")
                    .With("Left", "<Keyboard>/leftArrow", groups: "Keyboard").With("Right", "<Keyboard>/rightArrow", groups: "Keyboard");
                move.AddBinding("<Gamepad>/leftStick", groups: "Gamepad");
                move.AddBinding("<Gamepad>/dpad", groups: "Gamepad");
                var dance = gameplay.AddAction("Dance", InputActionType.Button);
                dance.AddBinding("<Keyboard>/space", groups: "Keyboard");
                dance.AddBinding("<Gamepad>/buttonSouth", groups: "Gamepad");
                asset.AddControlScheme("Keyboard").WithRequiredDevice("<Keyboard>");
                asset.AddControlScheme("Gamepad").WithRequiredDevice("<Gamepad>");
                File.WriteAllText(InputPath, asset.ToJson());
                UnityEngine.Object.DestroyImmediate(asset);
                AssetDatabase.ImportAsset(InputPath, ImportAssetOptions.ForceSynchronousImport);
            }
            var controls = AssetDatabase.LoadAssetAtPath<InputActionAsset>(InputPath);
            EditorBuildSettings.AddConfigObject("com.unity.input.settings.actions", controls, true);
            return controls;
        }

        static GameObject BuildPrefab(AlisaAnimationLibrary library, AnimatorController controller, InputActionAsset controls, Material material, Sprite footShadow)
        {
            bool exists = File.Exists(PrefabPath);
            var root = exists ? PrefabUtility.LoadPrefabContents(PrefabPath) : new GameObject("Alisa");
            try
            {
                GameObjectUtility.RemoveMonoBehavioursWithMissingScript(root);
                foreach (var old in root.GetComponents<MonoBehaviour>().Where(b => b != null && b.GetType().Name == "AlisaActor")) UnityEngine.Object.DestroyImmediate(old);
                root.tag = "Player";
                var animator = GetOrAdd<Animator>(root);
                animator.runtimeAnimatorController = controller;
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                var visual = GetChild(root.transform, "Visual");
                var renderer = GetOrAdd<SpriteRenderer>(visual.gameObject);
                renderer.sprite = library.Find("DirectionalV3/idle_s").frames[0];
                renderer.sharedMaterial = material;
                renderer.sortingOrder = 0;
                var shadow = GetOrAdd<SpriteRenderer>(GetChild(root.transform, "Shadow").gameObject);
                shadow.sprite = footShadow; shadow.sharedMaterial = material; shadow.sortingOrder = -1;
                var body = GetOrAdd<Rigidbody2D>(root);
                body.bodyType = RigidbodyType2D.Dynamic;
                body.gravityScale = 0;
                body.constraints = RigidbodyConstraints2D.FreezeRotation;
                body.interpolation = RigidbodyInterpolation2D.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
                var feet = GetOrAdd<CapsuleCollider2D>(root);
                feet.direction = CapsuleDirection2D.Horizontal;
                feet.size = new Vector2(.8f, .4f);
                feet.offset = new Vector2(0, .2f);
                const string physicsPath = "Assets/Alisa/Materials/PlayerFriction.physicsMaterial2D";
                var physics = AssetDatabase.LoadAssetAtPath<PhysicsMaterial2D>(physicsPath);
                if (physics == null) { physics = new PhysicsMaterial2D("PlayerFriction") { friction = 0, bounciness = 0 }; AssetDatabase.CreateAsset(physics, physicsPath); }
                feet.sharedMaterial = physics;
                var player = GetOrAdd<AlisaPlayerController>(root);
                player.visual = renderer; player.shadow = shadow;
                var input = GetOrAdd<PlayerInput>(root);
                input.actions = controls;
                input.defaultActionMap = "Gameplay";
                input.defaultControlScheme = "Keyboard";
                input.neverAutoSwitchControlSchemes = false;
                input.notificationBehavior = PlayerNotifications.SendMessages;
                return PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally
            {
                if (exists) PrefabUtility.UnloadPrefabContents(root);
                else UnityEngine.Object.DestroyImmediate(root);
            }
        }

        static void MigrateScene(GameObject prefab, Material material)
        {
            var scene = SceneManager.GetSceneByPath(ScenePath);
            if (!scene.isLoaded) scene = File.Exists(ScenePath) ? EditorSceneManager.OpenScene(ScenePath) : EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
            var roots = scene.GetRootGameObjects();
            foreach (var old in roots.Where(o => o.name == "Animation Preview")) UnityEngine.Object.DestroyImmediate(old);
            var world = Root(scene, "World");
            var actors = Root(scene, "Actors");
            var camera = roots.Where(o => o != null).SelectMany(o => o.GetComponentsInChildren<Camera>(true)).FirstOrDefault();
            if (camera == null) camera = Root(scene, "Main Camera").AddComponent<Camera>();
            camera.name = "Main Camera"; camera.tag = "MainCamera";
            camera.transform.SetParent(null); camera.transform.position = new Vector3(0, 0, -10);
            camera.orthographic = true; camera.orthographicSize = 7.5f;
            camera.rect = new Rect(0, 0, 1, 1);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color32(31, 34, 41, 255);
            camera.allowHDR = false; camera.allowMSAA = false;
            GetOrAdd<AudioListener>(camera.gameObject);
            var cameraData = camera.GetUniversalAdditionalCameraData();
            cameraData.renderPostProcessing = false;
            cameraData.antialiasing = AntialiasingMode.None;
            var pixels = GetOrAdd<PixelPerfectCamera>(camera.gameObject);
            pixels.assetsPPU = 16; pixels.refResolutionX = 320; pixels.refResolutionY = 240;
            pixels.cropFrame = PixelPerfectCamera.CropFrame.None;
            pixels.gridSnapping = PixelPerfectCamera.GridSnapping.UpscaleRenderTexture;
            var pixelSettings = new SerializedObject(pixels);
            pixelSettings.FindProperty("m_FilterMode").enumValueIndex = (int)PixelPerfectCamera.PixelPerfectFilterMode.Point;
            pixelSettings.ApplyModifiedPropertiesWithoutUndo();
            var floor = roots.Where(o => o != null).SelectMany(o => o.GetComponentsInChildren<SpriteRenderer>(true)).FirstOrDefault(s => s.name.StartsWith("Courtyard"));
            if (floor == null) floor = new GameObject("Courtyard").AddComponent<SpriteRenderer>();
            floor.name = "Courtyard"; floor.transform.SetParent(world.transform, false); floor.transform.localPosition = Vector3.zero;
            floor.sprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Alisa/Art/Environment/Alisa_scene_background.png");
            floor.sharedMaterial = material; floor.sortingOrder = -10000;
            var character = roots.Where(o => o != null).SelectMany(o => o.GetComponentsInChildren<Animator>(true)).FirstOrDefault(a => a.runtimeAnimatorController == prefab.GetComponent<Animator>().runtimeAnimatorController);
            var player = character != null ? character.gameObject : (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            player.name = "Alisa"; player.transform.SetParent(actors.transform, true); player.transform.position = new Vector3(0, -2.5f, 0);
            var bounds = GetChild(world.transform, "Bounds");
            Wall(bounds, "North", new Vector2(0, 2.65f), new Vector2(18.9f, .5f));
            Wall(bounds, "South", new Vector2(0, -6.85f), new Vector2(18.9f, .5f));
            Wall(bounds, "West", new Vector2(-9.2f, -2.1f), new Vector2(.5f, 10.3f));
            Wall(bounds, "East", new Vector2(9.2f, -2.1f), new Vector2(.5f, 10.3f));
            world.transform.SetSiblingIndex(0); actors.transform.SetSiblingIndex(1); camera.transform.SetSiblingIndex(2);
            EditorSceneManager.SaveScene(scene, ScenePath);
            Selection.activeGameObject = player;
        }

        static void Wall(Transform parent, string name, Vector2 center, Vector2 size)
        {
            var child = GetChild(parent, name); child.localPosition = center;
            GetOrAdd<BoxCollider2D>(child.gameObject).size = size;
        }
        static GameObject Root(Scene scene, string name)
        {
            var existing = scene.GetRootGameObjects().FirstOrDefault(o => o.name == name);
            if (existing != null) return existing;
            var result = new GameObject(name); SceneManager.MoveGameObjectToScene(result, scene); return result;
        }
        static Transform GetChild(Transform parent, string name)
        {
            var child = parent.Find(name);
            if (child != null) return child;
            child = new GameObject(name).transform; child.SetParent(parent, false); return child;
        }
        static T GetOrAdd<T>(GameObject target) where T : Component
        {
            var component = target.GetComponent<T>(); return component != null ? component : target.AddComponent<T>();
        }
    }
}
