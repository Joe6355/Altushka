using System;
using UnityEngine;

namespace AlisaGame
{
    [CreateAssetMenu(menuName = "Alisa/Animation Library")]
    public sealed class AlisaAnimationLibrary : ScriptableObject
    {
        public const int NativeWidth = 36;
        public const int NativeHeight = 86;
        public const int PixelsPerUnit = 16;

        public string defaultKey = "Polished/idle_s";
        public Entry[] entries = Array.Empty<Entry>();

        [Serializable]
        public sealed class Entry
        {
            public int id;
            public string key;
            public string label;
            public string group;
            [TextArea] public string note;
            public bool loop;
            public bool historical;
            public AnimationClip clip;
            public Sprite[] frames;
            public int[] durationsMs;

            public float Duration => clip != null ? clip.length : 0f;

            public float FrameTime(int index)
            {
                int milliseconds = 0;
                for (int i = 0; i < Mathf.Clamp(index, 0, durationsMs.Length); i++)
                    milliseconds += durationsMs[i];
                return milliseconds / 1000f;
            }

            public int FrameAt(float time)
            {
                if (durationsMs == null || durationsMs.Length == 0) return 0;
                float cursor = loop && Duration > 0 ? Mathf.Repeat(time, Duration) : Mathf.Max(0, time);
                for (int i = 0; i < durationsMs.Length - 1; i++)
                {
                    cursor -= durationsMs[i] / 1000f;
                    if (cursor < -0.00001f) return i;
                }
                return durationsMs.Length - 1;
            }
        }

        public Entry Find(string key) => Array.Find(entries, entry => entry.key == key);
    }
}
