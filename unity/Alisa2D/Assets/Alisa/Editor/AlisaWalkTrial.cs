using UnityEditor;

namespace AlisaGame.Editor
{
    internal static class AlisaWalkTrial
    {
        [MenuItem("Alisa/Применить проверочную походку")]
        static void Apply() => AlisaProjectBuilder.BuildAndVerify();
    }
}
