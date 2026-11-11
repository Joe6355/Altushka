"""Render the calibrated front diagonals and their matching idle from Alisa.blend."""

import json
from math import cos, pi, sin, sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_model import OUTPUT, ROOT, smoothstep
from gait import LOOP, STRIDE, leg_points, place_bone, rotate_relative, solve_knee
from render_frames import point, render

OUT = OUTPUT / "game"
WORK = ROOT / ".tools" / "alisa_blender_game"
CROP_LEFT = 24
WALK_CELS = 20
IDLE_CELS = 6
GAME_SPEED = 37.5
REFERENCE_FRAME = 1
LEAD_MARGIN = .365


def ground_projection(scene):
    """Project the sole onto the same screen plane as the character's game movement."""
    camera_up = scene.camera.matrix_world.to_quaternion() @ Vector((0, 1, 0))
    start = point(scene, (0, 0, 0))
    end = point(scene, (0, -STRIDE, 0))
    travel_x = end[0] - start[0]
    travel_y = end[1] - start[1]
    shear = (travel_x - travel_y) * scene.camera.data.ortho_scale / (86 * STRIDE)
    return camera_up, shear, travel_x


def add_ground_projection(camera_up, shear):
    # The foot projection follows the floor; the deformation fades out at the thighs.
    group = bpy.data.node_groups.new("Game floor projection", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = group.nodes, group.links
    incoming = nodes.new("NodeGroupInput")
    outgoing = nodes.new("NodeGroupOutput")
    position = nodes.new("GeometryNodeInputPosition")
    axes = nodes.new("ShaderNodeSeparateXYZ")
    links.new(position.outputs["Position"], axes.inputs[0])
    fade = nodes.new("ShaderNodeMapRange")
    fade.interpolation_type = "SMOOTHSTEP"
    fade.inputs["From Min"].default_value = .145
    fade.inputs["From Max"].default_value = .765
    fade.inputs["To Min"].default_value = 1
    fade.inputs["To Max"].default_value = 0
    links.new(axes.outputs["Z"], fade.inputs["Value"])
    depth = nodes.new("ShaderNodeMath")
    depth.operation = "ADD"
    depth.inputs[1].default_value = LEAD_MARGIN
    links.new(axes.outputs["Y"], depth.inputs[0])
    amount = nodes.new("ShaderNodeMath")
    amount.operation = "MULTIPLY"
    links.new(depth.outputs[0], amount.inputs[0])
    links.new(fade.outputs["Result"], amount.inputs[1])
    offset = nodes.new("ShaderNodeVectorMath")
    offset.operation = "SCALE"
    offset.inputs[0].default_value = camera_up * shear
    links.new(amount.outputs[0], offset.inputs["Scale"])
    displaced = nodes.new("GeometryNodeSetPosition")
    links.new(incoming.outputs["Geometry"], displaced.inputs["Geometry"])
    links.new(offset.outputs["Vector"], displaced.inputs["Offset"])
    links.new(displaced.outputs["Geometry"], outgoing.inputs["Geometry"])
    for obj in bpy.context.scene.objects:
        if obj.name.startswith(("Black shoe.", "Thigh and stocking.")):
            obj.modifiers.new("Game floor projection", "NODES").node_group = group


def verify_stance(scene, rig, camera_up, shear, travel):
    error = 0.0
    # A fixed point of each flat sole is tested in world position across its stance.
    for side, sign, first in (("L", 1, 8), ("R", -1, 38)):
        positions = []
        for frame in range(first, first + 20):
            scene.frame_set(frame)
            foot = rig.pose.bones[f"Foot.{side}"]
            sole = foot.matrix @ foot.bone.matrix_local.inverted() @ Vector((sign*.105, .005, .013))
            projected = point(scene, sole + camera_up * (shear * (sole.y + LEAD_MARGIN)))
            shift = (frame - 1) / LOOP * travel
            positions.append(Vector((projected[0] + shift, projected[1] + shift)))
        error = max(error, max((p - positions[0]).length for p in positions))
    assert error < .08, error
    return error


def idle_reference(scene, rig):
    scene.frame_set(REFERENCE_FRAME)
    reference = {bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones}
    rig.animation_data.action = None
    for name in ("White pleated skirt", "Sweater and hands"):
        keys = bpy.data.objects[name].data.shape_keys
        keys.animation_data.action = None
    return reference


def set_idle(rig, reference, phase, facing):
    for bone in rig.pose.bones:
        bone.matrix_basis = reference[bone.name]
    pelvis = rig.pose.bones["Pelvis"]
    wave = 2*pi*phase
    displacement = Vector((-.004+.006*sin(wave), .008, -.021+.004*(1-cos(wave))))
    pelvis.location = pelvis.bone.matrix_local.to_quaternion().inverted() @ displacement
    rotate_relative(pelvis, Quaternion((0,0,1),-.072) @ Quaternion((0,1,0),-.029))
    rotate_relative(rig.pose.bones["Spine"], Quaternion((0,0,1),.092) @ Quaternion((1,0,0),-.043))
    rotate_relative(rig.pose.bones["Chest"], Quaternion((1,0,0),.009*sin(wave)))
    rotate_relative(rig.pose.bones["Curl"], Quaternion((0,1,0),.042*sin(wave-.45)))
    bpy.context.view_layer.update()
    head = rig.pose.bones["Head"]
    head.matrix = Matrix.Translation(head.head) @ facing.to_matrix().to_4x4()
    support = {}
    for side, sign in (("L", 1), ("R", -1)):
        rest_hip, rest_knee, rest_ankle, _ = map(Vector, leg_points(sign))
        hip = pelvis.matrix @ pelvis.bone.matrix_local.inverted() @ rest_hip
        ankle = Vector((sign*.089, -.058 if sign > 0 else .068, .089))
        knee, ankle, stretch = solve_knee(hip, ankle, (rest_knee-rest_hip).length,
                                         (rest_ankle-rest_knee).length, Vector((0,-1,0)))
        assert stretch < .001, stretch
        thigh = rig.pose.bones[f"Thigh.{side}"]
        shin = rig.pose.bones[f"Shin.{side}"]
        foot = rig.pose.bones[f"Foot.{side}"]
        place_bone(thigh, hip, (rest_knee-rest_hip).rotation_difference(knee-hip))
        bpy.context.view_layer.update()
        place_bone(shin, knee, (rest_ankle-rest_knee).rotation_difference(ankle-knee))
        bpy.context.view_layer.update()
        place_bone(foot, ankle, Quaternion((0,0,1),sign*.072))
        support[foot.name] = ankle
    cloth = bpy.data.objects["White pleated skirt"].data.shape_keys.key_blocks
    for name, weight in (("Swing left",.11+.08*sin(wave)), ("Swing right",0),
                         ("Lag forward",.07+.04*cos(wave)), ("Lag back",0)):
        cloth[name].value = weight
    # Keep the small correction at contact, where the relaxed stance also clears the cloth.
    bpy.data.objects["Sweater and hands"].data.shape_keys.key_blocks["Fabric follow-through"].value = .10+.10*(1-cos(wave))
    bpy.context.view_layer.update()
    assert all((rig.pose.bones[name].head-ankle).length<.0002 for name,ankle in support.items())


def snap_face(scene, head, anchor):
    x,y = point(scene, head.head)
    dx = round(x-anchor[0]) + anchor[0]-x
    dy = round(y-anchor[1]) + anchor[1]-y
    scale = scene.camera.data.ortho_scale / 86
    transform = head.matrix.copy()
    transform.translation += scene.camera.matrix_world.to_quaternion() @ Vector((dx*scale,-dy*scale,0))
    head.matrix = transform
    bpy.context.view_layer.update()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    rig = bpy.data.objects["Alisa · Rig"]
    camera_up, shear, travel = ground_projection(scene)
    error = verify_stance(scene, rig, camera_up, shear, travel)
    pivot = point(scene, camera_up * (shear * LEAD_MARGIN))
    add_ground_projection(camera_up, shear)
    scene.render.resolution_x = scene.render.resolution_y = 344
    scene.eevee.taa_render_samples = 8
    scene.frame_set(REFERENCE_FRAME)
    head = rig.pose.bones["Head"]
    anchor = point(scene, head.head)
    facing = head.matrix.to_quaternion()

    for i in range(WALK_CELS):
        scene.frame_set(REFERENCE_FRAME + i*LOOP//WALK_CELS)
        head.location = (0,0,0)
        bpy.context.view_layer.update()
        snap_face(scene, head, anchor)
        render(scene, WORK/f"walk_{i:02}.png")
    head.location = (0,0,0)
    reference = idle_reference(scene,rig)
    for i in range(IDLE_CELS):
        set_idle(rig,reference,i/IDLE_CELS,facing)
        snap_face(scene, head, anchor)
        render(scene, WORK/f"idle_{i:02}.png")
    playback = GAME_SPEED / sqrt(2) / travel
    report = dict(walkCels=WALK_CELS, idleCels=IDLE_CELS,
                  pivot=[pivot[0]-CROP_LEFT,pivot[1]], travel=travel,
                  playback=playback, stanceErrorPixels=error)
    (WORK/"render.json").write_text(json.dumps(report,indent=2), encoding="utf-8")
    print("Game front-diagonal renders:",report,flush=True)


if __name__ == "__main__":
    main()
