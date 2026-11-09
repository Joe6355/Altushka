using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEditor.U2D.Sprites;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AlisaGame.Editor
{
    /// <summary>Builds versioned Unity assets from the unmodified native atlases.</summary>
    public static class AlisaProjectBuilder
    {
        const string BasePath = "Assets/Alisa";
        const string ArtPath = BasePath + "/Art";
        const string ManifestPath = ArtPath + "/AlisaSources.json";
        const string LibraryPath = BasePath + "/Animations/AlisaLibrary.asset";
        const string ControllerPath = BasePath + "/Animations/Alisa.controller";
        const string PrefabPath = BasePath + "/Prefabs/Alisa.prefab";
        public const string ScenePath = AlisaGameSetup.ScenePath;

        // These DTOs are populated by JsonUtility, rather than C# assignments.
#pragma warning disable CS0649
        [Serializable] sealed class Manifest
        {
            public int nativeWidth, nativeHeight, pixelsPerUnit;
            public string defaultKey;
            public Atlas[] atlases;
            public SourceClip[] clips;
        }
        [Serializable] sealed class Atlas
        {
            public string key, assetPath, source, sha256;
            public int width, height;
            public Frame[] frames;
        }
        [Serializable] sealed class Frame
        {
            public int x, y, w, h, pivotX, pivotY;
        }
        [Serializable] sealed class SourceClip
        {
            public int id;
            public string key, label, group, atlasKey, note;
            public int[] frames, durationsMs;
            public bool loop, historical;
        }
#pragma warning restore CS0649

        [MenuItem("Alisa/Обновить клипы из атласов")]
        public static void Build()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Stop Play mode before rebuilding animation assets.");
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            Require(manifest.nativeWidth == 36 && manifest.nativeHeight == 86 && manifest.pixelsPerUnit == 16,
                "The native source grid must remain 36x86 at 16 PPU.");
            Directory.CreateDirectory(BasePath + "/Animations/Clips");
            Directory.CreateDirectory(BasePath + "/Prefabs");
            Directory.CreateDirectory(BasePath + "/Materials");
            Directory.CreateDirectory("Assets/Scenes");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            var sprites = new Dictionary<string, Sprite[]>();
            foreach (var atlas in manifest.atlases) sprites.Add(atlas.key, ImportAtlas(atlas));
            var library = AssetDatabase.LoadAssetAtPath<AlisaAnimationLibrary>(LibraryPath);
            if (library == null)
            {
                library = ScriptableObject.CreateInstance<AlisaAnimationLibrary>();
                AssetDatabase.CreateAsset(library, LibraryPath);
            }
            library.defaultKey = manifest.defaultKey;
            library.entries = manifest.clips.Select(source => BuildClip(source, sprites[source.atlasKey])).ToArray();
            EditorUtility.SetDirty(library);
            var material = BuildMaterial();
            if (AlisaGameSetup.Build(library, material, CreateShadow()))
            {
                EditorSettings.defaultBehaviorMode = EditorBehaviorMode.Mode2D;
                EditorSettings.serializationMode = SerializationMode.ForceText;
                PlayerSettings.companyName = "DudinSergey";
                PlayerSettings.productName = "Alisa 2D";
                PlayerSettings.runInBackground = true;
                PlayerSettings.defaultScreenWidth = 1440;
                PlayerSettings.defaultScreenHeight = 900;
                PlayerSettings.resizableWindow = true;
                QualitySettings.antiAliasing = 0;
                QualitySettings.vSyncCount = 1;
                QualitySettings.pixelLightCount = 0;
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log($"ALISA_BUILD_OK: {library.entries.Length} Animator clips; native 36x86; scene {ScenePath}");
        }

        public static void BuildAndVerify()
        {
            Build();
            Verify();
        }

        static Sprite[] ImportAtlas(Atlas atlas)
        {
            ConfigureTexture(atlas.assetPath, SpriteImportMode.Multiple);
            var importer = (TextureImporter)AssetImporter.GetAtPath(atlas.assetPath);
            var factories = new SpriteDataProviderFactories();
            factories.Init();
            var provider = factories.GetSpriteEditorDataProviderFromObject(importer);
            Require(provider != null, "Sprite data provider unavailable: " + atlas.assetPath);
            provider.InitSpriteEditorDataProvider();
            var previous = provider.GetSpriteRects().ToDictionary(rect => rect.name, rect => rect.spriteID);
            var rects = new SpriteRect[atlas.frames.Length];
            for (int i = 0; i < rects.Length; i++)
            {
                var frame = atlas.frames[i];
                string name = SpriteName(atlas.key, i);
                rects[i] = new SpriteRect
                {
                    name = name,
                    spriteID = previous.TryGetValue(name, out var guid) ? guid : StableGuid(name),
                    rect = new Rect(frame.x, atlas.height - frame.y - frame.h, frame.w, frame.h),
                    alignment = SpriteAlignment.Custom,
                    pivot = new Vector2(frame.pivotX / (float)frame.w, (frame.h - frame.pivotY) / (float)frame.h),
                    border = Vector4.zero
                };
            }
            provider.SetSpriteRects(rects);
            var names = provider.GetDataProvider<ISpriteNameFileIdDataProvider>();
            names?.SetNameFileIdPairs(rects.Select(rect => new SpriteNameFileIdPair(rect.name, rect.spriteID)));
            provider.Apply();
            importer.SaveAndReimport();
            var imported = AssetDatabase.LoadAllAssetsAtPath(atlas.assetPath).OfType<Sprite>().ToDictionary(sprite => sprite.name);
            Require(imported.Count == rects.Length, "Imported sprite count differs: " + atlas.key);
            return Enumerable.Range(0, rects.Length).Select(i => imported[SpriteName(atlas.key, i)]).ToArray();
        }

        static void ConfigureTexture(string path, SpriteImportMode mode)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            Require(importer != null, "Texture importer missing: " + path);
            importer.textureType = TextureImporterType.Sprite;
            importer.spriteImportMode = mode;
            importer.spritePixelsPerUnit = 16;
            importer.filterMode = FilterMode.Point;
            importer.mipmapEnabled = false;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.crunchedCompression = false;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.maxTextureSize = 8192;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false;
            importer.sRGBTexture = true;
            importer.isReadable = true;
            var settings = new TextureImporterSettings();
            importer.ReadTextureSettings(settings);
            settings.spriteMeshType = SpriteMeshType.FullRect;
            settings.spriteGenerateFallbackPhysicsShape = false;
            importer.SetTextureSettings(settings);
            importer.SaveAndReimport();
        }

        static AlisaAnimationLibrary.Entry BuildClip(SourceClip source, Sprite[] sprites)
        {
            string path = BasePath + "/Animations/Clips/" + SafeName(source.key) + ".anim";
            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
            if (clip == null)
            {
                clip = new AnimationClip();
                AssetDatabase.CreateAsset(clip, path);
            }
            clip.name = SafeName(source.key);
            clip.frameRate = 100f; // Source delays are integer multiples of 10 ms.
            clip.legacy = false;
            clip.wrapMode = source.loop ? WrapMode.Loop : WrapMode.Once;
            bool needsHoldKey = source.durationsMs[source.durationsMs.Length - 1] > 10;
            var keys = new ObjectReferenceKeyframe[source.frames.Length + (needsHoldKey ? 1 : 0)];
            int timeMs = 0;
            for (int i = 0; i < source.frames.Length; i++)
            {
                keys[i] = new ObjectReferenceKeyframe { time = timeMs / 1000f, value = sprites[source.frames[i]] };
                timeMs += source.durationsMs[i];
            }
            // Unity extends a sprite curve by one sample beyond its final key.
            // Hold the final cel until T - one sample; looping then wraps at exactly T.
            if (needsHoldKey) keys[keys.Length - 1] = new ObjectReferenceKeyframe
            {
                time = (timeMs - 10) / 1000f,
                value = sprites[source.frames[source.frames.Length - 1]]
            };
            AnimationUtility.SetObjectReferenceCurve(clip, EditorCurveBinding.PPtrCurve("Visual", typeof(SpriteRenderer), "m_Sprite"), keys);
            var settings = AnimationUtility.GetAnimationClipSettings(clip);
            settings.loopTime = source.loop;
            settings.loopBlend = false;
            settings.startTime = 0;
            settings.stopTime = timeMs / 1000f;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
            EditorUtility.SetDirty(clip);
            return new AlisaAnimationLibrary.Entry
            {
                id = source.id, key = source.key, label = source.label, group = source.group,
                note = source.note, historical = source.historical, loop = source.loop,
                clip = clip, frames = source.frames.Select(index => sprites[index]).ToArray(),
                durationsMs = source.durationsMs
            };
        }

        static Material BuildMaterial()
        {
            const string path = BasePath + "/Materials/AlisaSpriteUnlit.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material != null) return material;
            Shader shader = Shader.Find("Universal Render Pipeline/2D/Sprite-Unlit-Default");
            Require(shader != null, "The Universal 2D template / URP 2D shader must be installed first.");
            material = new Material(shader) { name = "AlisaSpriteUnlit" };
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        static Sprite CreateShadow()
        {
            const string path = ArtPath + "/Environment/FootShadow.png";
            if (!File.Exists(path))
            {
                var texture = new Texture2D(22, 6, TextureFormat.RGBA32, false);
                for (int y = 0; y < 6; y++)
                    for (int x = 0; x < 22; x++)
                    {
                        float u = (x + 0.5f - 11) / 11;
                        float v = (y + 0.5f - 3) / 3;
                        texture.SetPixel(x, y, u * u + v * v < 1 ? new Color(0, 0, 0, 0.35f) : Color.clear);
                    }
                texture.Apply();
                File.WriteAllBytes(path, texture.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(texture);
            }
            ConfigureTexture(path, SpriteImportMode.Single);
            return AssetDatabase.LoadAssetAtPath<Sprite>(path);
        }

        [MenuItem("Alisa/Открыть игровую сцену")]
        public static void OpenGame() => EditorSceneManager.OpenScene(ScenePath);

        [MenuItem("Alisa/Проверить импорт и Animator")]
        public static void Verify()
        {
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
            var library = AssetDatabase.LoadAssetAtPath<AlisaAnimationLibrary>(LibraryPath);
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            Require(library != null && controller != null && prefab != null && File.Exists(ScenePath), "Missing generated Unity assets.");
            Require(library.entries.Length == manifest.clips.Length, "Clip count mismatch.");
            Require(library.entries.Select(entry => entry.id).Distinct().Count() == library.entries.Length, "Duplicate clip IDs.");
            int framesChecked = 0;
            foreach (var atlas in manifest.atlases)
            {
                using (var hash = SHA256.Create())
                {
                    string actual = BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(atlas.assetPath))).Replace("-", "").ToLowerInvariant();
                    Require(actual == atlas.sha256, "Source pixels changed: " + atlas.assetPath);
                }
                var importer = (TextureImporter)AssetImporter.GetAtPath(atlas.assetPath);
                Require(importer.filterMode == FilterMode.Point && !importer.mipmapEnabled && importer.textureCompression == TextureImporterCompression.Uncompressed,
                    "Pixel import settings changed: " + atlas.assetPath);
                var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(atlas.assetPath);
                Require(texture.width == atlas.width && texture.height == atlas.height, "Atlas rescaled: " + atlas.key);
                var importedSprites = AssetDatabase.LoadAllAssetsAtPath(atlas.assetPath).OfType<Sprite>().ToDictionary(sprite => sprite.name);
                for (int i = 0; i < atlas.frames.Length; i++)
                {
                    var sprite = importedSprites[SpriteName(atlas.key, i)];
                    var frame = atlas.frames[i];
                    Require(sprite.rect.width == 36 && sprite.rect.height == 86 && sprite.pixelsPerUnit == 16, "Native sprite dimensions changed.");
                    Require(sprite.rect.x == frame.x && sprite.rect.y == atlas.height - frame.y - frame.h, "Slice coordinates changed.");
                    Require(Vector2.Distance(sprite.pivot, new Vector2(frame.pivotX, frame.h - frame.pivotY)) < 0.0001f, "Foot pivot changed: " + sprite.name);
                    framesChecked++;
                }
            }

            // Sample every source clip in an isolated transient Animator. Archive clips
            // remain ordinary .anim assets without adding debug states to the game graph.
            var testScene = EditorSceneManager.NewPreviewScene();
            var instance = new GameObject("Import verification");
            SceneManager.MoveGameObjectToScene(instance, testScene);
            var animator = instance.AddComponent<Animator>();
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            var visual = new GameObject("Visual").AddComponent<SpriteRenderer>();
            visual.transform.SetParent(instance.transform, false);
            var machine = new AnimatorStateMachine { name = "Base Layer" };
            var state = new AnimatorState { name = "Source" };
            machine.states = new[] { new ChildAnimatorState { state = state } };
            machine.defaultState = state;
            var sampling = new AnimatorController { layers = new[] {
                new AnimatorControllerLayer { name = "Base Layer", defaultWeight = 1f, stateMachine = machine }
            } };
            animator.runtimeAnimatorController = sampling;
            try
            {
                foreach (var entry in library.entries)
                {
                    var source = manifest.clips.Single(item => item.key == entry.key);
                    float expectedLength = source.durationsMs.Sum() / 1000f;
                    Require(Mathf.Abs(entry.clip.length - expectedLength) < 0.0001f,
                        $"Clip duration mismatch: {entry.key}, expected {expectedLength}, actual {entry.clip.length}");
                    Require(AnimationUtility.GetAnimationClipSettings(entry.clip).loopTime == entry.loop, "Loop flag mismatch.");
                    var curves = AnimationUtility.GetObjectReferenceCurveBindings(entry.clip);
                    Require(curves.Length == 1 && curves[0].path == "Visual" && curves[0].propertyName == "m_Sprite", "Sprite curve missing.");
                    var keys = AnimationUtility.GetObjectReferenceCurve(entry.clip, curves[0]);
                    int expectedKeys = entry.frames.Length + (entry.durationsMs[entry.durationsMs.Length - 1] > 10 ? 1 : 0);
                    Require(keys.Length == expectedKeys, "Cel count mismatch.");
                    for (int i = 0; i < entry.frames.Length; i++)
                        Require(keys[i].value == entry.frames[i] && Mathf.Abs(keys[i].time - entry.FrameTime(i)) < 0.0001f,
                            "Source cel timing changed: " + entry.key);
                    state.motion = entry.clip;
                    animator.Rebind();
                    animator.speed = 0;
                    animator.Update(0);
                    for (int i = 0; i < entry.frames.Length; i++)
                    {
                        float time = entry.FrameTime(i) + entry.durationsMs[i] / 2000f;
                        animator.Play("Base Layer.Source", 0, time / entry.Duration);
                        animator.Update(0);
                        Require(visual.sprite == entry.frames[i], "Animator sampled the wrong sprite: " + entry.key + " frame " + i);
                    }
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
                UnityEngine.Object.DestroyImmediate(sampling);
                UnityEngine.Object.DestroyImmediate(machine);
                UnityEngine.Object.DestroyImmediate(state);
                EditorSceneManager.ClosePreviewScene(testScene);
            }
            AlisaGameplayCheck.VerifyStructure();
            Debug.Log($"ALISA_VERIFY_OK: {library.entries.Length} clips, {framesChecked} native sprites sampled; timing, pivots and source hashes verified; gameplay scene connected.");
        }

        static string SpriteName(string atlas, int index) => atlas + "_" + index.ToString("D3");

        static string SafeName(string key) => key.Replace("/", "__");
        static GUID StableGuid(string name)
        {
            using (var md5 = MD5.Create())
                return new GUID(BitConverter.ToString(md5.ComputeHash(System.Text.Encoding.UTF8.GetBytes("alisa-sprite:" + name))).Replace("-", "").ToLowerInvariant());
        }
        static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
