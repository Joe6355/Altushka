"""Build the Blender source for the 36 × 86 Alisa sprite study."""

from math import atan2, cos, pi, sin, sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent
ROOT = OUTPUT.parents[1]
RENDER = ROOT / ".tools" / "alisa_blender"
sys.path.insert(0, str(SOURCE))
from gait import add_walk, leg_points

TAU = 2 * pi


def smoothstep(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def curve_point(points, position):
    """Sample a continuous path through its sculpting stations."""
    index = min(int(position), len(points) - 2)
    fraction = position - index
    a, b, c, d = (points[max(0, min(index + delta, len(points) - 1))] for delta in (-1, 0, 1, 2))
    return tuple(
        y + 0.5 * fraction * (
            z - x + fraction * (2*x - 5*y + 4*z - w + fraction * (3*y - x - 3*z + w))
        )
        for x, y, z, w in zip(a, b, c, d)
    )


def linear_rgb(hex_color):
    rgb = (int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
    return tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055)**2.4 for c in rgb)


def material(name, colors, light=(.47, -.58, .67), stops=(0.0, .43, .64, .84)):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear_rgb(colors[-2] if len(colors) > 1 else colors[0]), 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location.x = 640
    shader = nodes.new("ShaderNodeEmission")
    shader.location.x = 390
    links.new(shader.outputs[0], output.inputs["Surface"])
    shader.inputs["Color"].default_value = (*linear_rgb(colors[0]), 1)
    if len(colors) > 1:
        geo = nodes.new("ShaderNodeNewGeometry")
        geo.location.x = -560
        dot = nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = Vector(light).normalized()
        dot.location.x = -340
        links.new(geo.outputs["Normal"], dot.inputs[0])
        bias = nodes.new("ShaderNodeMath")
        bias.operation = "MULTIPLY_ADD"
        bias.inputs[1].default_value = .5
        bias.inputs[2].default_value = .5
        bias.location.x = -130
        links.new(dot.outputs["Value"], bias.inputs[0])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location.x = 80
        ramp.color_ramp.interpolation = "CONSTANT"
        elements = ramp.color_ramp.elements
        elements.remove(elements[1])
        for index, (stop, color) in enumerate(zip(stops, colors)):
            element = elements.new(stop) if index else elements[0]
            element.color = (*linear_rgb(color), 1)
        links.new(bias.outputs[0], ramp.inputs[0])
        links.new(ramp.outputs["Color"], shader.inputs["Color"])
    return mat


def collection(name):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def mesh(name, vertices, faces, materials, coll, face_material=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    for mat in materials:
        data.materials.append(mat)
    for poly in data.polygons:
        poly.use_smooth = True
        if face_material is not None:
            poly.material_index = face_material[poly.index]
    return obj


def link_rig(obj, rig, weights):
    obj.parent = rig
    deform = obj.modifiers.new("Skin", "ARMATURE")
    deform.object = rig
    deform.use_deform_preserve_volume = True
    if isinstance(weights, str):
        group = obj.vertex_groups.new(name=weights)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        return obj
    groups = {}
    for vert in obj.data.vertices:
        for name, weight in weights(vert.co):
            if weight < 1e-5:
                continue
            if name not in groups:
                groups[name] = obj.vertex_groups.new(name=name)
            groups[name].add([vert.index], weight, "REPLACE")
    return obj


def ring_faces(rows, count, reverse=False, caps=True):
    faces = [
        (r*count+i, r*count+(i+1)%count, (r+1)*count+(i+1)%count, (r+1)*count+i)
        for r in range(rows - 1)
        for i in range(count)
    ]
    if caps:
        faces.extend([tuple(reversed(range(count))), tuple(range((rows-1)*count, rows*count))])
    return [face[::-1] for face in faces] if reverse else faces


def body_rings(name, profile, mats, coll, rig, weights, *, center_x=0.0, detail=None,
               row_material=None, sides=64, subdivisions=4):
    vertices = []
    layers = []
    for step in range((len(profile) - 1) * subdivisions + 1):
        z, width, front, back, center_y = curve_point(profile, step / subdivisions)
        layers.append(z)
        for i in range(sides):
            angle = TAU * i / sides
            x = width * sin(angle)
            depth = front if cos(angle) >= 0 else back
            y = center_y - depth * cos(angle)
            if detail:
                y += detail(x, z, angle)
            vertices.append((center_x + x, y, z))
    indices = None
    if row_material:
        indices = [row_material((a+b)/2) for a, b in zip(layers, layers[1:]) for _ in range(sides)]
        indices.extend((row_material(layers[0]), row_material(layers[-1])))
    obj = mesh(name, vertices, ring_faces(len(layers), sides), mats, coll, indices)
    return link_rig(obj, rig, weights)


def sweep(name, stations, mat, coll, rig, weights, *, outside=(0, -1, 0), count=20, steps=6):
    vertices = []
    end = len(stations) - 1
    for k in range(end * steps + 1):
        t = k / steps
        x, y, z, width, depth = curve_point(stations, t)
        tangent = Vector(curve_point(stations, min(end, t+.015))[:3])
        tangent -= Vector(curve_point(stations, max(0, t-.015))[:3])
        tangent.normalize()
        lateral = tangent.cross(Vector(outside)).normalized()
        normal = lateral.cross(tangent)
        for i in range(count):
            angle = TAU*i/count
            vertices.append(Vector((x, y, z)) + lateral * (max(.001, width)*sin(angle))
                            + normal * (max(.001, depth)*cos(angle)))
    obj = mesh(name, vertices, ring_faces(end * steps + 1, count), [mat], coll)
    return link_rig(obj, rig, weights)


def make_rig(coll):
    data = bpy.data.armatures.new("Alisa · Skeleton")
    rig = bpy.data.objects.new("Alisa · Rig", data)
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None, deform=True):
        result = data.edit_bones.new(name)
        result.head, result.tail = head, tail
        result.use_deform = deform
        if parent:
            result.parent = data.edit_bones[parent]
        return result

    bone("Root", (0, 0, 0), (0, 0, .19), deform=False)
    bone("Pelvis", (0, 0, .895), (0, 0, 1.006), "Root")
    bone("Spine", (0, 0, 1.006), (0, 0, 1.139), "Pelvis")
    bone("Chest", (0, 0, 1.139), (0, 0, 1.287), "Spine")
    bone("Head", (0, 0, 1.287), (0, 0, 1.68), "Chest")
    bone("Curl", (-.064, -.014, 1.865), (-.079, -.015, 2.048), "Head")
    for side, sign in (("L", 1), ("R", -1)):
        hip, knee, ankle, toe = leg_points(sign)
        bone(f"Thigh.{side}", hip, knee, "Pelvis")
        bone(f"Shin.{side}", knee, ankle, f"Thigh.{side}")
        bone(f"Foot.{side}", ankle, toe, f"Shin.{side}")
        shoulder, elbow, wrist, palm = arm_points(sign)
        bone(f"UpperArm.{side}", shoulder, elbow, "Chest")
        bone(f"Forearm.{side}", elbow, wrist, f"UpperArm.{side}")
        bone(f"Hand.{side}", wrist, palm, f"Forearm.{side}")
        bone(f"Hair.{side}", (sign*.249, .043, 1.697), (sign*.291, .039, 1.335), "Head")
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
    rig.show_in_front = True
    data.display_type = "OCTAHEDRAL"
    rig.hide_set(True)
    return rig


def arm_points(sign):
    return tuple((x*sign, y, z) for x, y, z in (
        (.177, -.021, 1.229), (.307, -.006, 1.072),
        (.210, -.110, .994), (.172, -.145, .965),
    ))


FACE = [
    (1.282, .030, .055, .058, -.021),
    (1.308, .104, .135, .102, -.029),
    (1.348, .163, .173, .144, -.021),
    (1.400, .209, .207, .179, -.005),
    (1.462, .240, .224, .212, .002),
    (1.534, .248, .224, .220, .005),
    (1.610, .243, .204, .214, .010),
    (1.685, .215, .169, .192, .015),
    (1.757, .148, .113, .139, .020),
    (1.802, .014, .015, .016, .020),
]


def face_relief(x, z, angle):
    nose = .033 * (1-smoothstep(.008, .061, abs(x))) * (1-smoothstep(.003, .065, abs(z-1.443)))
    cheek = .016 * (1-smoothstep(.02, .115, abs(abs(x)-.143))) * (1-smoothstep(.01, .086, abs(z-1.453)))
    flatten = .020 * sin(angle)**2 * max(0.0, cos(angle))**1.5
    return -(nose + cheek) * max(0.0, cos(angle))**4 - flatten


def surface(profile, detail, x, z):
    for i, station in enumerate(profile[1:]):
        if z <= station[0]:
            break
    lo, hi = float(i), float(i+1)
    for _ in range(15):
        t = (lo+hi)/2
        if curve_point(profile, t)[0] < z:
            lo = t
        else:
            hi = t
    _, width, depth, _, center = curve_point(profile, (lo+hi)/2)
    s = max(-.999, min(.999, x / width))
    c = sqrt(1 - s*s)
    return center - depth*c + detail(x, z, atan2(s, c))


def decal(name, points, mat, coll, rig, bone, profile, relief, offset):
    """Lay a detail on the curved surface with a little clearance."""
    mid = (sum(x for x, _ in points)/len(points), sum(z for _, z in points)/len(points))
    divisions = 5
    verts, faces = [], []
    for n, first in enumerate(points):
        second = points[(n+1) % len(points)]
        origin = len(verts)
        for row in range(divisions+1):
            t = row/divisions
            for col in range(row+1):
                u = col/divisions
                x = mid[0]*(1-t) + first[0]*(t-u) + second[0]*u
                z = mid[1]*(1-t) + first[1]*(t-u) + second[1]*u
                verts.append((x, surface(profile, relief, x, z)-offset, z))
        for row in range(divisions):
            here = origin + row*(row+1)//2
            after = here + row+1
            for col in range(row+1):
                faces.append((here+col, after+col, after+col+1))
                if col < row:
                    faces.append((here+col, after+col+1, here+col+1))
    return link_rig(mesh(name, verts, faces, [mat], coll), rig, bone)


def oval(x, z, width, height, n=28):
    return [(x + width*cos(TAU*i/n), z + height*sin(TAU*i/n)) for i in range(n)]


def contour(points, subdivisions=4):
    # Closed paths are smooth around the join as well as at their middle stations.
    padded = [points[-1], *points, points[0], points[1]]
    return [curve_point(padded, 1+i/subdivisions) for i in range(len(points)*subdivisions)]


def build_face(coll, rig, mats):
    body_rings("Face", FACE, [mats["skin"]], coll, rig, "Head", detail=face_relief)

    def feature(name, points, material_name, depth):
        return decal(name, points, mats[material_name], coll, rig, "Head", FACE, face_relief, depth)

    for side, sign in (("L", 1), ("R", -1)):
        def eye(name, points, material_name, depth):
            return feature(f"{name}.{side}", [(sign*x, z) for x, z in points], material_name, depth)

        eye("Eye socket", contour([(.041,1.534), (.063,1.560), (.118,1.578), (.176,1.575),
                                  (.220,1.555), (.196,1.522), (.150,1.501), (.097,1.504)]), "lash", .0038)
        eye("Sclera", contour([(.052,1.534), (.080,1.551), (.125,1.559), (.173,1.559),
                              (.204,1.548), (.185,1.523), (.144,1.506), (.102,1.510)]), "sclera", .0055)
        eye("Iris", contour([(.094,1.552), (.140,1.558), (.170,1.552), (.171,1.529),
                            (.156,1.511), (.127,1.508), (.104,1.520)]), "iris", .0074)
        eye("Iris shadow", contour([(.094,1.552), (.137,1.558), (.170,1.552), (.168,1.533),
                                   (.131,1.537), (.100,1.537)]), "iris_dark", .0084)
        eye("Pupil", oval(.135,1.537,.015,.018,18), "pupil", .0092)
        eye("Iris light", contour([(.108,1.521), (.131,1.516), (.158,1.520),
                                   (.151,1.513), (.127,1.511)]), "iris_light", .010)
        eye("Eye sparkle", oval(.119,1.547,.010,.009,16), "sparkle", .011)
        eye("Upper lash", contour([(.040,1.541), (.068,1.568), (.119,1.580), (.180,1.575),
                                  (.225,1.562), (.208,1.545), (.163,1.548), (.095,1.546)]), "lash", .012)
        eye("Cheek", contour([(.136,1.484), (.181,1.489), (.203,1.479), (.179,1.467),
                             (.143,1.471)]), "blush", .0028)
        eye("Brow", contour([(.056,1.601), (.103,1.618), (.150,1.618), (.196,1.605),
                            (.162,1.607), (.101,1.606)]), "brow", .003)

    feature("Nose shade", contour([(-.025,1.441), (-.006,1.431), (.017,1.435), (.023,1.441),
                                  (.003,1.436)]), "blush", .002)
    feature("Mouth", contour([(-.031,1.392), (-.013,1.401), (.004,1.399), (.022,1.402),
                             (.038,1.397), (.014,1.388), (-.009,1.389)]), "lip", .0038)
    feature("Lower lip", oval(.010,1.383,.015,.0038,16), "blush", .003)


def build_hair(coll, rig, mats):
    count, rows = 120, 31
    vertices = []
    for row in range(rows):
        t = row/(rows-1)
        for i in range(count):
            angle = TAU*i/count
            away = abs(atan2(sin(angle), cos(angle)))
            edge = 1.64 + .84*smoothstep(.53,1.42,away) + .17*smoothstep(1.45,2.75,away)
            edge += .052*sin(8*angle+.4) + .034*sin(13*angle)
            phi = .012 + t*(edge-.012)
            radius = sin(phi) if phi <= pi/2 else 1-.17*((phi-pi/2)/1.12)**2
            strand = .0052*(.15+.85*t) * (sin(8*angle+1.7*t)+.34*cos(13*angle+.8*t))
            x = (.321*radius+strand)*sin(angle) - .013*(1-t)
            y = .040 - (.278*radius+strand)*cos(angle)
            z = 1.627 + .273*cos(phi) + .010*sin(angle+.8)*t*t
            vertices.append((x,y,z))
    cap = mesh("Bob · cap", vertices, ring_faces(rows,count,reverse=True), [mats["hair"]], coll)
    link_rig(cap, rig, "Head")

    locks = [
        ("Swept fringe", "hair_top", [
            (.080,-.109,1.856,.016,.010), (.039,-.209,1.805,.096,.032),
            (-.057,-.252,1.736,.118,.043), (-.138,-.247,1.665,.097,.035),
            (-.205,-.218,1.591,.064,.028), (-.223,-.199,1.553,.006,.008),
        ]),
        ("Left tip", "hair", [
            (-.056,-.174,1.820,.019,.009), (-.131,-.241,1.755,.068,.021),
            (-.191,-.244,1.679,.064,.028), (-.251,-.201,1.577,.045,.029),
            (-.264,-.176,1.500,.006,.006),
        ]),
        ("Right fringe", "hair_top", [
            (.064,-.143,1.856,.010,.008), (.130,-.208,1.794,.072,.032),
            (.169,-.242,1.716,.071,.032), (.194,-.212,1.635,.063,.030),
            (.213,-.172,1.547,.013,.009),
        ]),
        ("Side sweep", "hair", [
            (.127,-.125,1.829,.017,.008), (.211,-.161,1.772,.079,.037),
            (.263,-.150,1.685,.063,.035), (.285,-.121,1.585,.043,.027),
            (.279,-.131,1.519,.004,.008),
        ]),
    ]
    for name, material_name, stations in locks:
        sweep(name, stations, mats[material_name], coll, rig, "Head")

    for side, sign in (("L", 1), ("R", -1)):
        def hair_weight(co):
            weight = 1-smoothstep(1.40,1.70,co.z)
            return (("Head",1-weight), (f"Hair.{side}",weight))

        for index, station in enumerate((
            [(.235,-.068,1.763,.028,.018), (.292,-.118,1.673,.070,.042),
             (.304,-.119,1.550,.062,.043), (.280,-.130,1.439,.052,.035),
             (.234,-.150,1.349,.028,.019), (.231,-.165,1.330,.004,.004)],
            [(.238,.054,1.776,.022,.017), (.301,.082,1.669,.081,.050),
             (.319,.063,1.542,.066,.045), (.296,.052,1.422,.061,.038),
             (.248,.032,1.334,.015,.009), (.250,.021,1.322,.003,.003)],
            [(.157,.202,1.762,.015,.013), (.240,.240,1.666,.073,.039),
             (.259,.250,1.553,.070,.035), (.221,.248,1.431,.061,.032),
             (.190,.233,1.359,.017,.011), (.190,.219,1.341,.003,.003)],
        )):
            swept = [(sign*x, y, z+(.008 if sign<0 else 0), w, d) for x,y,z,w,d in station]
            outward = ((.84*sign,-.54,0), (.97,.24,0), (.58*sign,.78,0))[index]
            if index == 1:
                outward = (outward[0]*sign, outward[1], 0)
            sweep(f"Bob lock {index+1}.{side}", swept, mats["hair"] if index != 1 else mats["hair_side"],
                  coll, rig, hair_weight, outside=outward)

    sweep("Curl", [
        (-.064,-.014,1.862,.028,.022), (-.092,-.012,1.934,.023,.021),
        (-.103,-.020,2.011,.026,.023), (-.075,-.024,2.056,.031,.024),
        (-.024,-.022,2.063,.026,.021), (.007,-.015,2.032,.019,.016),
        (.004,-.010,2.000,.005,.006),
    ], mats["hair_top"], coll, rig, "Curl", steps=8)


SWEATER = [
    (.967,.153,.118,.117,.008), (.986,.162,.121,.122,.008),
    (1.024,.154,.116,.123,.007), (1.073,.161,.126,.128,.007),
    (1.121,.181,.146,.133,.005), (1.170,.200,.167,.137,.008),
    (1.218,.218,.156,.134,.011), (1.250,.206,.136,.115,.014),
    (1.274,.164,.107,.102,.014), (1.299,.083,.076,.077,.010),
]


def chest_relief(x, z, angle):
    if cos(angle) <= 0:
        return 0.0
    width = 1-smoothstep(.028,.154,abs(abs(x)-.083))
    height = 1-smoothstep(.014,.107,abs(z-1.167))
    return -(.076*width*height)*cos(angle)**.7


def build_clothes(coll, rig, mats):
    def sweater_weight(co):
        chest = smoothstep(1.065,1.175,co.z)
        pelvis = 1-smoothstep(.980,1.070,co.z)
        return (("Chest",chest), ("Pelvis",pelvis), ("Spine",1-chest-pelvis))

    sweater = body_rings("Fitted black sweater", SWEATER, [mats["knit"],mats["cuff"]], coll, rig,
                         sweater_weight, detail=chest_relief, row_material=lambda z: int(z<.991))

    def knit_motion(obj):
        obj.shape_key_add(name="Basis")
        rebound = obj.shape_key_add(name="Knit follow-through")
        for p in rebound.data:
            mask = (1-smoothstep(.02,.101,abs(p.co.z-1.165))) * smoothstep(.10,.185,-p.co.y)
            p.co.z += .022*mask
            p.co.y -= .008*mask
        return rebound

    rebound = [knit_motion(sweater)]
    body_rings("Neck", [
        (1.229,.069,.070,.069,.005), (1.293,.070,.065,.065,.003),
        (1.332,.075,.066,.064,-.012), (1.360,.072,.065,.059,-.017),
    ], [mats["skin"]], coll, rig, "Head", sides=40)
    body_rings("Ribbed collar", [
        (1.256,.081,.078,.078,.007), (1.278,.080,.077,.078,.006),
        (1.318,.078,.075,.076,.004), (1.330,.074,.074,.074,.003),
    ], [mats["cuff"]], coll, rig, "Chest", sides=64,
        detail=lambda x,z,a:.0018*cos(30*a)*cos(a))
    opening = [(-.012,1.230),(-.048,1.209),(-.052,1.173),(-.028,1.138),
               (-.004,1.124),(.030,1.141),(.051,1.178),(.039,1.210),(.013,1.226)]
    trims = (
        ("Keyhole · welt", [(x*1.15,(z-1.175)*1.10+1.175) for x,z in opening], "welt", .006),
        ("Keyhole", opening, "skin_detail", .009),
        ("Keyhole · soft shade", [(-.001,1.218),(.013,1.192),(.009,1.163),(-.006,1.137),
                                  (-.011,1.167),(-.010,1.191)], "blush", .0105),
    )
    for name,points,mat,offset in trims:
        obj = decal(name,contour(points),mats[mat],coll,rig,sweater_weight,SWEATER,chest_relief,offset)
        rebound.append(knit_motion(obj))
    return rebound


def build_arms(coll, rig, mats):
    for side, sign in (("L",1),("R",-1)):
        stations = [
            (.153,-.010,1.248,.039,.038), (.190,-.025,1.221,.068,.066),
            (.225,-.019,1.183,.062,.058), (.267,-.002,1.128,.054,.052),
            (.302,-.005,1.074,.051,.051), (.280,-.040,1.041,.048,.045),
            (.243,-.079,1.016,.041,.043), (.207,-.113,.992,.038,.038),
        ]

        def arm_weight(co):
            bend = 1-smoothstep(1.050,1.108,co.z)
            return ((f"UpperArm.{side}",1-bend),(f"Forearm.{side}",bend))

        def mirror(items):
            return [(sign*x,y,z,w,d) for x,y,z,w,d in items]

        sweep(f"Sleeve.{side}",mirror(stations),mats["knit"],coll,rig,arm_weight)
        sweep(f"Cuff.{side}",mirror([
            (.237,-.085,1.017,.043,.043),(.226,-.095,1.007,.044,.044),
            (.205,-.114,.991,.039,.038),(.201,-.118,.986,.036,.036),
        ]),mats["cuff"],coll,rig,f"Forearm.{side}")
        sweep(f"Hand.{side}",mirror([
            (.211,-.110,.993,.027,.026),(.196,-.127,.980,.035,.025),
            (.170,-.150,.965,.041,.026),(.146,-.157,.954,.024,.018),
            (.135,-.156,.953,.007,.007),
        ]),mats["skin"],coll,rig,f"Hand.{side}")
        sweep(f"Thumb.{side}",mirror([
            (.198,-.130,.980,.019,.020),(.189,-.151,.993,.017,.016),
            (.174,-.158,1.002,.010,.011),(.167,-.155,1.001,.005,.005),
        ]),mats["skin"],coll,rig,f"Hand.{side}",count=14)


def build_skirt(coll, rig, mats):
    vertices = []
    count = 144
    profile = [
        (0.00,.982,.147,.118,0.0), (.04,.976,.153,.123,0.0),
        (.16,.956,.170,.138,.16), (.29,.936,.191,.153,.36),
        (.50,.895,.213,.174,.57), (.74,.832,.243,.199,.83),
        (.96,.763,.265,.216,1.0), (1.00,.746,.266,.220,1.0),
        (1.00,.740,.263,.215,1.0), (1.00,.745,.250,.201,.95),
        (.94,.772,.249,.196,.92), (.67,.850,.219,.181,.73),
    ]
    for u,z,w,d,pleat in profile:
        for i in range(count):
            a = TAU*i/count
            fold = .012*sin(12*a+1.25*u) + .005*sin(24*a+2.5*u)
            edge = (.009*cos(12*a+1.2) + .005*cos(3*a-.4))*u*u
            vertices.append(((w+fold*pleat)*sin(a), .010-(d+fold*pleat)*cos(a), z+edge))
    face_mats = [int(row in (6,7)) + 2*int(row>=8) for row in range(len(profile)-1) for _ in range(count)]
    skirt = mesh("White pleated skirt", vertices, ring_faces(len(profile),count,reverse=True,caps=False),
                 [mats["skirt"],mats["hem"],mats["lining"]],coll,face_mats)
    link_rig(skirt, rig, "Pelvis")
    skirt.shape_key_add(name="Basis")
    flutter = []
    for label, direction in (("Swing left",1), ("Swing right",-1), ("Lag forward",1), ("Lag back",-1)):
        key = skirt.shape_key_add(name=label)
        flutter.append(key)
        for i,p in enumerate(key.data):
            u = profile[i//count][0]
            a = TAU*(i%count)/count
            if label.startswith("Swing"):
                p.co.x += direction*.035*u**2
                p.co.y += direction*.010*u**2*sin(2*a)
                p.co.z += direction*.023*u**2*sin(a-.15)
            else:
                p.co.y -= direction*.041*u**2
                p.co.z += direction*.029*u**2*cos(a+.24)
                p.co.x += .010*u**2*sin(2*a)*direction
    body_rings("Skirt waistband", [
        (.940,.165,.132,.134,.010), (.946,.167,.133,.135,.010),
        (.972,.156,.122,.124,.010), (.982,.151,.120,.122,.010),
    ], [mats["hem"]], coll, rig, "Pelvis", sides=72)
    body_rings("Underskirt", [
        (.769,.156,.110,.110,.015), (.806,.191,.129,.140,.018),
        (.876,.185,.126,.132,.018), (.923,.159,.123,.128,.016),
    ], [mats["knit"]], coll, rig, "Pelvis", sides=48)
    return skirt,flutter,count


def build_legs(coll, rig, mats):
    for side, sign in (("L",1),("R",-1)):
        hip, knee, ankle, _ = leg_points(sign)
        thigh = mats["stocking"]
        # A continuous surface from the top of the thigh to inside the shoe.
        profile = [
            (.088,.046,.057,.050,.001),(.133,.052,.052,.056,.006),
            (.192,.053,.049,.053,.012),(.265,.065,.060,.064,.020),
            (.337,.069,.066,.064,.024),(.408,.064,.058,.059,.011),
            (.474,.067,.066,.067,-.023),(.533,.072,.071,.070,-.018),
            (.608,.083,.078,.076,-.008),(.649,.090,.085,.084,-.001),
            (.666,.093,.087,.086,.001),(.682,.095,.089,.088,.002),
            (.754,.106,.095,.093,.010),(.833,.110,.103,.101,.015),
            (.884,.092,.091,.089,.016),(.912,.070,.075,.070,.015),
            (.926,.056,.062,.061,.014),
        ]

        def leg_weight(co):
            thigh_weight = smoothstep(.409,.549,co.z)
            foot_weight = 1-smoothstep(.098,.167,co.z)
            pelvis_weight = smoothstep(.847,.925,co.z)
            return (("Pelvis",pelvis_weight),(f"Thigh.{side}",thigh_weight-pelvis_weight),
                    (f"Shin.{side}",1-thigh_weight-foot_weight),(f"Foot.{side}",foot_weight))

        body_rings(f"Thigh and stocking.{side}",profile,[thigh,mats["stocking_band"],mats["skin"]],
                   coll,rig,leg_weight,center_x=hip[0],sides=48,subdivisions=3,
                   row_material=lambda z: 0 if z<.666 else (1 if z<.682 else 2))
        shoe_profile = [
            (-.205,.020,.051,.031),(-.197,.049,.069,.021),(-.177,.070,.083,.014),
            (-.138,.076,.089,.013),(-.081,.073,.109,.013),(-.023,.063,.142,.015),
            (.024,.061,.139,.015),(.066,.060,.112,.014),(.088,.050,.087,.016),
            (.096,.024,.064,.027),
        ]
        shoe_verts = []
        shoe_indices = []
        sides = 48
        rows = 3*(len(shoe_profile)-1)+1
        for row in range(rows):
            y,w,top,bottom = curve_point(shoe_profile,row/3)
            for i in range(sides):
                a = TAU*i/sides
                c = cos(a)
                z = bottom + (top-bottom)*(.5+.5*(1 if c>=0 else -1)*abs(c)**.54)
                shoe_verts.append((ankle[0]+w*sin(a),y,z))
                if row < rows-1:
                    shoe_indices.append(int(c<-.68))
        shoe_indices.extend((0,0))
        shoe = mesh(f"Black shoe.{side}",shoe_verts,ring_faces(rows,sides),
                    [mats["shoe"],mats["welt"]],coll,shoe_indices)
        link_rig(shoe,rig,f"Foot.{side}")


def set_camera(camera, azimuth, elevation=17.5, scale=2.20, target_z=1.015):
    azimuth, elevation = azimuth*pi/180, elevation*pi/180
    look_at = Vector((0,-.018,target_z))
    camera.location = look_at + 5.8*Vector((sin(azimuth)*cos(elevation),
                                          -cos(azimuth)*cos(elevation),sin(elevation)))
    camera.rotation_euler = (look_at-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.ortho_scale = scale


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    coll_rig = collection("Alisa · Rig")
    face = collection("Alisa · Face")
    hair = collection("Alisa · Hair")
    costume = collection("Alisa · Outfit")
    stage = collection("Cameras")
    palette = {
        "skin":("Skin",("c58699","f0a8af","f9c7bd","ffe6dc","fff0e6")),
        "skin_detail":("Warm skin",("be7886","e79aa5","f5b6b0","ffd4c4")),
        "blush":("Rose",("e59aa7",)),
        "lip":("Lip",("ad596e",)),
        "brow":("Brow",("797586",)),
        "lash":("Ink lash",("292332",)),
        "sclera":("Eye white",("fff4f2",)),
        "iris":("Blue iris",("278db6",)),
        "iris_dark":("Blue iris shade",("286189",)),
        "iris_light":("Cyan iris",("67d9e8",)),
        "pupil":("Pupil",("17334e",)),
        "sparkle":("Eye light",("fffef9",)),
        "hair":("Silver hair",("7c7b91","a6a5bb","c7c9da","e6e7f0","f8f7fa")),
        "hair_top":("Silver hair · light strands",("8b899f","b1b0c6","d5d6e3","eff0f6","fdfbfc")),
        "hair_side":("Silver hair · side locks",("77768d","a1a0b6","bec0d2","dfe1eb","f4f2f6")),
        "knit":("Black knit",("15141b","23222c","30303b","41404d")),
        "cuff":("Black knit · ribbing",("101017","1c1b24","292832","363541")),
        "welt":("Black seam",("15131c",)),
        "skirt":("White pleats",("858399","acadc0","d1d3e0","ececf2","fffdfa")),
        "lining":("Skirt lining",("66647c","9290a6","adacc0","d1d0dc")),
        "hem":("White hem",("9694ab","b5b6ca","dedee8","fcfafd")),
        "stocking":("Charcoal stockings",("181820","272731","363642","494854")),
        "stocking_band":("Stocking cuff",("14141d","21202a","2a2a34","3b3b46")),
        "shoe":("Black leather",("17161e","22212c","302f3b","42414e","595869")),
    }
    mats = {}
    for key,(name,colors) in palette.items():
        stops = (0.0,.36,.54,.72,.89) if len(colors)==5 else (0.0,.41,.61,.82)
        if key == "skin":
            stops = (0.0,.32,.48,.63,.86)
        mats[key] = material(name,colors,stops=stops)
    rig = make_rig(coll_rig)
    build_face(face,rig,mats)
    build_hair(hair,rig,mats)
    rebound = build_clothes(costume,rig,mats)
    build_arms(costume,rig,mats)
    skirt = build_skirt(costume,rig,mats)
    build_legs(costume,rig,mats)
    add_walk(scene,rig,skirt,rebound)

    data = bpy.data.cameras.new("Game orthographic")
    data.type = "ORTHO"
    data.lens = 50
    camera = bpy.data.objects.new("Game orthographic",data)
    stage.objects.link(camera)
    scene.camera = camera
    set_camera(camera, -39)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 688
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.filter_size = 1.0
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (.24,.24,.24)
    scene.eevee.taa_render_samples = 12
    scene.frame_set(12)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.color_type = "MATERIAL"
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    RENDER.mkdir(parents=True,exist_ok=True)
    scene.render.filepath = "//Alisa_render"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/"Alisa.blend"), compress=True)
    scene.render.filepath = str(RENDER/"quarter_test.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
