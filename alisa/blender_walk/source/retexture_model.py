"""Fit the dance art to the model at the game camera's front-quarter view."""

import json
from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_model import OUTPUT, ROOT, body_rings, material, mesh, set_camera, smoothstep
from gait import FPS, LOOP, STRIDE, add_walk
from render_frames import check_walk, point, render


REVISION = OUTPUT/"revision"
WORK = ROOT/".tools"/"alisa_blender_revision"
ATLAS = ROOT/"recolor"/"blue_eyes"/"Altushka_blue_atlas.png"
SOURCE_FRAME = 9
REFERENCE_POSE = 1
PIXEL_SHIFT = (2,0)
SQUARE_CROP_X = 24
SHOE_LENGTH = .87


def source_image():
    image = bpy.data.images.load(str(ATLAS),check_existing=True)
    image.name = "Original Alisa dance atlas"
    image.pack()
    w,h = image.size
    pixels = np.empty(w*h*4,dtype=np.float32)
    image.pixels.foreach_get(pixels)
    cel = pixels.reshape(h,w,4)[::-1,:]
    cel = cel[:86,SOURCE_FRAME*36:(SOURCE_FRAME+1)*36][:,::-1]
    y,x = np.indices(cel.shape[:2])
    opaque = cel[...,3] > .5
    head = opaque & ((y<27)|((y==27)&(x>=15))|((y==28)&(x>=19)))
    shirt = opaque & ~head & (y>=25)&(y<46)
    # The first white pixels of the skirt share rows with the lowered wrists.
    rgb = cel[...,:3]
    dress = (y>=40)&(x>=11)&(rgb.min(axis=-1)>.49)&(rgb.max(axis=-1)-rgb.min(axis=-1)<.125)
    shirt &= ~dress & ~((y>=44)&(x<20))
    return image,head,shirt


def texture_material(image):
    mat = bpy.data.materials.new("Alisa · palette from dance")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"
    tex.extension = "CLIP"
    tex.location.x = -320
    shader = nodes.new("ShaderNodeEmission")
    shader.location.x = 0
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location.x = 210
    links.new(tex.outputs["Color"],shader.inputs["Color"])
    links.new(shader.outputs[0],output.inputs["Surface"])
    return mat


def head_weights(x,y):
    curl = (1-smoothstep(4,10,y))*.83
    rear_lock = (1-smoothstep(7,12,x))*smoothstep(16,28,y)*.50
    front_lock = smoothstep(23,27,x)*smoothstep(22,30,y)*.49
    return (("Head",1-curl-rear_lock-front_lock),("Curl",curl),
            ("Hair.R",rear_lock),("Hair.L",front_lock))


def shirt_weights(x,y):
    wrist = (1-smoothstep(8,13,x))*smoothstep(35,41,y)*.74
    pelvis = smoothstep(39,46,y)*(1-wrist)*.78
    spine = smoothstep(34,42,y)*(1-pelvis-wrist)*.62
    return (("Chest",1-pelvis-spine-wrist),("Spine",spine),
            ("Pelvis",pelvis),("Forearm.R",wrist))


def pixel_surface(name, mask, coll, rig, camera, center, materials, weights_at, depth):
    """Build a closed, curved mesh with UVs registered to the original cel."""
    cells = [(int(x),int(y)) for y,x in zip(*np.nonzero(mask))]
    tiles = set(cells)
    offsets = ((0,0),(1,0),(1,1),(0,1))
    points = sorted({(x+dx,y+dy) for x,y in cells for dx,dy in offsets})
    corners = {p:i for i,p in enumerate(points)}
    boundary = np.array([p for p in points if any((p[0]-dx,p[1]-dy) not in tiles for dx,dy in offsets)])
    distance = np.sqrt(((np.array(points)[:,None,:]-boundary[None,:,:])**2).sum(axis=2).min(axis=1))
    radius = max(1.0,np.percentile(distance,97))
    t = np.minimum(1.0,distance/radius)
    relief = np.sqrt(1-(1-t)**2)
    camera_basis = camera.matrix_world.to_quaternion()
    right = camera_basis@Vector((1,0,0))
    up = camera_basis@Vector((0,1,0))
    view = camera_basis@Vector((0,0,1))
    ppu = 86/camera.data.ortho_scale
    origin = camera.location-view*(camera.location-center).dot(view)
    delta = {b.name:b.matrix@b.bone.matrix_local.inverted() for b in rig.pose.bones}
    vertices = []
    weights = []
    for side,amount in ((1,depth[0]),(-1,depth[1])):
        for i,(x,y) in enumerate(points):
            target = (origin
                      + right*((x+PIXEL_SHIFT[0]+SQUARE_CROP_X-43)/ppu)
                      + up*((43-y-PIXEL_SHIFT[1])/ppu)
                      + view*(side*(.007+amount*float(relief[i]))))
            assignment = tuple((bone,w) for bone,w in weights_at(x,y) if w>1e-6)
            assert abs(sum(w for _,w in assignment)-1)<1e-5
            transform = Matrix([[0.0]*4 for _ in range(4)])
            for bone,w in assignment:
                transform += delta[bone]*w
            vertices.append(transform.inverted()@target)
            weights.append(assignment)

    n = len(points)
    front = []
    back = []
    sides = []
    checks = ((0,-1),(1,0),(0,1),(-1,0))
    for x,y in cells:
        face = tuple(corners[(x+dx,y+dy)] for dx,dy in offsets)
        front.append(tuple(reversed(face)))
        back.append(tuple(i+n for i in face))
        for edge,(dx,dy) in enumerate(checks):
            if (x+dx,y+dy) in tiles:
                continue
            first,second = face[edge],face[(edge+1)%4]
            sides.append((first,second,second+n,first+n))
    faces = front+back+sides
    obj = mesh(name,vertices,faces,materials,coll,[0]*len(front)+[1]*(len(back)+len(sides)))
    obj.parent = rig
    deform = obj.modifiers.new("Skin","ARMATURE")
    deform.object = rig
    groups = {name:obj.vertex_groups.new(name=name) for name in {bone for row in weights for bone,_ in row}}
    for index,assignment in enumerate(weights):
        for bone,weight in assignment:
            groups[bone].add([index],weight,"REPLACE")
    uv_layer = obj.data.uv_layers.new(name="Dance atlas")
    atlas_width,atlas_height = materials[0].node_tree.nodes.get("Image Texture").image.size
    for i in range(len(front)):
        poly = obj.data.polygons[i]
        for loop in poly.loop_indices:
            vertex = obj.data.loops[loop].vertex_index
            x,y = points[vertex]
            uv_layer.data[loop].uv = (((SOURCE_FRAME+1)*36-x)/atlas_width,1-y/atlas_height)
    return obj,up


def soften_lower_body(rig,skirt):
    for side in ("L","R"):
        shoe = bpy.data.objects[f"Black shoe.{side}"]
        center = rig.data.bones[f"Foot.{side}"].head_local
        for v in shoe.data.vertices:
            v.co.x = center.x+(v.co.x-center.x)*.92
            v.co.y = center.y+(v.co.y-center.y)*SHOE_LENGTH
            v.co.z -= max(0,v.co.z-.056)*.19
    # Set the waistband against the actual lower edge of the dance top.
    basis = skirt.data.shape_keys.reference_key.data
    offsets = [.034+.047*smoothstep(.739,.974,v.co.z) for v in basis]
    for v,offset in zip(skirt.data.vertices,offsets):
        v.co.z += offset
    for key in skirt.data.shape_keys.key_blocks:
        for v,offset in zip(key.data,offsets):
            v.co.z += offset
    for v in bpy.data.objects["Skirt waistband"].data.vertices:
        v.co.z += .081
    colors = {
        "Charcoal stockings":("18181d","242429","313137","3d3d43"),
        "Stocking cuff":("15151a","1e1e24","29292d","35353a"),
        "Black leather":("15151a","1c1c22","2b2b30","38383d"),
        "White pleats":("9798a5","b7b9c5","d3d5e0","edeef4","fffdfa"),
    }
    for name,palette in colors.items():
        old = bpy.data.materials[name]
        stops = (0,.37,.58,.75,.91) if len(palette)==5 else (0,.40,.60,.82)
        new = material(name+" · native",palette,light=(-.52,-.44,.72),stops=stops)
        old.user_remap(new)
        if name == "White pleats":
            shade_pleats(skirt,new)


def shade_pleats(skirt,mat):
    fold = skirt.data.attributes.new("Fold shade","FLOAT","POINT")
    for i,value in enumerate(fold.data):
        row,col = divmod(i,144)
        angle = 2*pi*col/144
        groove = max(0,sin(7*angle+.24*row)+.22*cos(3*angle))
        value.value = .018+.226*groove**1.28
    tree = mat.node_tree
    ramp = next(node for node in tree.nodes if node.type=="VALTORGB")
    light = ramp.inputs[0].links[0].from_socket
    attr = tree.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = fold.name
    attr.location = (-350,-180)
    subtract = tree.nodes.new("ShaderNodeMath")
    subtract.operation = "SUBTRACT"
    subtract.location = (-100,-145)
    tree.links.new(light,subtract.inputs[0])
    tree.links.new(attr.outputs["Fac"],subtract.inputs[1])
    tree.links.new(subtract.outputs[0],ramp.inputs[0])


def stabilize_gaze(scene,rig):
    head = rig.pose.bones["Head"]
    scene.frame_set(REFERENCE_POSE)
    facing = head.matrix.to_quaternion()
    previous = None
    for frame in range(1,LOOP+2):
        scene.frame_set(frame)
        head.matrix = Matrix.Translation(head.head)@facing.to_matrix().to_4x4()
        head.location = (0,0,0)
        rotation = head.rotation_quaternion.copy()
        if previous is not None:
            rotation.make_compatible(previous)
        head.rotation_quaternion = rotation
        head.keyframe_insert("rotation_quaternion",frame=frame,group="Head")
        previous = rotation


def remove_previous_upper():
    for name in ("Alisa · Face","Alisa · Hair"):
        for obj in list(bpy.data.collections[name].objects):
            bpy.data.objects.remove(obj,do_unlink=True)
    costume = bpy.data.collections["Alisa · Outfit"]
    for obj in list(costume.objects):
        if obj.name.startswith(("Fitted black","Keyhole","Ribbed collar","Sleeve.","Cuff.","Hand.","Thumb.")):
            bpy.data.objects.remove(obj,do_unlink=True)
    return costume


def rebuild():
    scene = bpy.context.scene
    camera = scene.camera
    rig = bpy.data.objects["Alisa · Rig"]
    skirt = bpy.data.objects["White pleated skirt"]
    scene.render.resolution_x = scene.render.resolution_y = 688
    set_camera(camera,-39,elevation=14,scale=2.20,target_z=1.042)
    rig.animation_data_clear()
    skirt.data.shape_keys.animation_data_clear()
    for key in list(skirt.data.shape_keys.key_blocks):
        if key.name.startswith("Leg clearance"):
            skirt.shape_key_remove(key)
        else:
            key.value = 0
    soften_lower_body(rig,skirt)
    costume = remove_previous_upper()
    scene.timeline_markers.clear()
    cloth = tuple(skirt.data.shape_keys.key_blocks[name] for name in
                  ("Swing left","Swing right","Lag forward","Lag back"))
    add_walk(scene,rig,(skirt,cloth,144),[],shoe_length=SHOE_LENGTH,
             contact_path=WORK/"contacts.json")
    stabilize_gaze(scene,rig)
    scene.frame_set(REFERENCE_POSE)
    bpy.context.view_layer.update()
    image,head_mask,shirt_mask = source_image()
    paint = texture_material(image)
    head_delta = rig.pose.bones["Head"].matrix@rig.data.bones["Head"].matrix_local.inverted()
    chest_delta = rig.pose.bones["Chest"].matrix@rig.data.bones["Chest"].matrix_local.inverted()
    hair_back = bpy.data.materials["Silver hair"]
    knit_back = bpy.data.materials["Black knit"]
    body_rings("Sweater waist", [
        (1.008,.145,.103,.104,.008),(1.028,.152,.107,.109,.008),
        (1.055,.147,.102,.107,.009),(1.080,.136,.096,.098,.010),
    ],[knit_back],costume,rig,"Pelvis",sides=48)
    pixel_surface("Head and bob",head_mask,bpy.data.collections["Alisa · Hair"],rig,camera,
                  head_delta@Vector((0,.022,1.58)),[paint,hair_back],head_weights,(.176,.234))
    sweater,up = pixel_surface("Sweater and hands",shirt_mask,costume,rig,camera,
                              chest_delta@Vector((0,-.012,1.14)),[paint,knit_back],
                              shirt_weights,(.153,.153))
    sweater.shape_key_add(name="Basis",from_mix=False)
    bounce = sweater.shape_key_add(name="Fabric follow-through",from_mix=False)
    for v in bounce.data:
        weight = (1-smoothstep(.01,.118,abs(v.co.z-1.14))) * smoothstep(.06,.16,-v.co.y)
        v.co += up*(.018*weight)
    for frame in range(1,LOOP+2):
        # The original pose is the low point; the neckline and fabric move together.
        bounce.value = .48*(1-cos(4*pi*(frame-1)/LOOP))
        bounce.keyframe_insert("value",frame=frame)
    rig["Game texture view"] = "Front quarter, 39 degrees"
    rig["Source art"] = "Altushka_blue_atlas.png, frame 10 (mirrored)"
    bpy.data.collections.remove(bpy.data.collections["Alisa · Face"])
    bpy.data.collections["Alisa · Hair"].name = "Alisa · Head"
    scene.frame_set(REFERENCE_POSE)
    scene.render.filepath = "//Alisa_render"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    REVISION.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(REVISION/"Alisa.blend"),compress=True)


def render_game(test_only):
    scene = bpy.context.scene
    checks = check_walk(scene,WORK)
    pivot = point(scene,(0,0,0))
    end = point(scene,(0,-STRIDE,0))
    poses = list(range(1,LOOP+1,4))
    scene.render.resolution_x = scene.render.resolution_y = 344
    scene.eevee.taa_render_samples = 8
    scene.frame_set(REFERENCE_POSE)
    head = bpy.data.objects["Alisa · Rig"].pose.bones["Head"]
    anchor = point(scene,head.head)
    view = scene.camera.matrix_world.to_quaternion()
    units = scene.camera.data.ortho_scale/86
    for i,frame in enumerate(poses[:1] if test_only else poses):
        scene.frame_set(frame)
        head.location = (0,0,0)
        bpy.context.view_layer.update()
        x,y = point(scene,head.head)
        dx = round(x-anchor[0])+anchor[0]-x
        dy = round(y-anchor[1])+anchor[1]-y
        # A steady forward gaze sits on whole pixels in the exported sprites.
        transform = head.matrix.copy()
        transform.translation += view@Vector((dx*units,-dy*units,0))
        head.matrix = transform
        bpy.context.view_layer.update()
        render(scene,WORK/f"cel_{i:02}.png")
    if test_only:
        return
    report = {"fps":FPS,"frames":poses,"pivotSquare":pivot,
              "travel":[b-a for a,b in zip(pivot,end)],"checks":checks}
    (WORK/"render.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Verified revised walk",checks,flush=True)


if __name__ == "__main__":
    flags = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    WORK.mkdir(parents=True,exist_ok=True)
    if "--render" not in flags:
        rebuild()
    render_game("--test" in flags)
