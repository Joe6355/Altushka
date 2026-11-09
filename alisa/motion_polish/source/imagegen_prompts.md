# Новая полировка движения Алисы

Инструмент: встроенный `image_gen.imagegen`, прозрачный фон.

Полный набор промптов и выбранных результатов:

| Ракурс | Промпт | Итог |
| --- | --- | --- |
| Бок вправо | Текст ниже | `Side_generated.png` |
| Спина | `North_prompt.txt` | `North_generated.png` |
| Перед | `South_prompt.txt`, затем `South_neckline_prompt.txt` | `South_generated.png` |
| Задняя правая диагональ | `NorthEast_correct_prompt.txt` | `NorthEast_generated.png` |
| Передняя правая диагональ | `SouthEast_prompt.txt` | `SouthEast_generated.png` |

Первый фронтальный запрос `South_first_prompt.txt` завершился без изображения. Первая задняя диагональ по `NorthEast_prompt.txt` не прошла проверку ракурса; она и фронтальный вариант до исправления выреза сохранены только в `studies/`.

## Side_generated.png

+Use case: identity-preserve, game sprite animation editing.
Input image 1 is the locked character/design reference: Alisa, an ADULT woman, white bob haircut and the distinctive single curl, cyan-blue eye, black fitted long-sleeve keyhole sweater, white pleated miniskirt, charcoal thigh-high stockings with black outlines, black flat shoes, hands resting on hips. Keep her exact recognizable design, slim waist, curvy adult figure, original bust and hip proportions and long legs. Input image 2 supports the same design and small pixel-cluster style from behind; do not change her to a new character.

Produce a professional polished RIGHT-FACING SIDE WALK and IDLE production sprite sheet for this same Alisa. Strict clean pixel art designed for a 36 by 86 logical pixel frame, presented enlarged. One black logical-pixel outline, opaque flat color clusters, about the same 20-color palette as the references, no gradients, no dithering, no painterly textures, no antialiased edge blur. Same slightly elevated RPG camera as the reference, NOT chibi, no shorter/squat body, no new outfit.

Output square sheet with EXACTLY 12 isolated full-body poses in a REGULAR 4-column by 3-row grid. Cells have the same size. True transparent background, no checkerboard painted in, no floor, no shadows, no grid lines, no labels, no text. Every figure is facing screen-right in profile, with one visible blue eye looking right, never at the viewer. Full curl and both shoes inside every cell. Consistent scale and head size, same virtual ground line and waist registration in each cell, plenty of transparent separation so the cells can be sliced. The character's actual body should occupy around 90% of each cell's height, maintaining the 36:86 character frame proportions.

Row 1: four quiet idle poses, identical planted feet and head/face: relaxed breath out; chest subtly expands; breath apex with a one-pixel-equivalent eyelid blink; relaxed breath returns. Small restrained breathing and hair-tip settling, no large vertical jumping.
Row 2 followed by row 3: EIGHT sequential WALK cels, one complete clean loop, 8th transitions naturally into 1st. They must actually differ anatomically, not just translate the same picture.
Cel 1 left-leg forward contact with heel down, other leg trailing. Cel 2 weight acceptance/down, front knee softly bends, rear heel lifts. Cel 3 passing: swing knee bent forwards, foot CLEARLY lifted, stance foot under hips. Cel 4 up/reach: body rises, swing shin extends into next contact. Cel 5 opposite-leg forward contact. Cel 6 opposite down/weight acceptance. Cel 7 opposite passing. Cel 8 opposite up/reach.
Maintain thigh and shin lengths, shoes rotate from heel contact to toe-off, no straight stick legs, no scissor jumps, no giant boot shapes, no sliding the entire body to fake motion, no duplicates of the contact pose in the passing cels. Stance foot travels smoothly backward relative to the body. Clear near and far leg occlusion.
The pelvis subtly rotates, torso counter-rotates and bobs by only 1-2 logical pixels. The sweater has restrained natural secondary motion, while hands stay on the hips. The white skirt pleats and hem lag behind the pelvis with a small coherent sway, and bob/hair curl follow a little later; stable facial pixels and consistent hair highlights in all cels. The result should feel hand-animated, balanced, fluid, and game-ready, closely matching the input silhouette. Preserve clothing coverage and identity exactly.
