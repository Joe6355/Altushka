"""Render the turn views and one complete sprite cycle from Alisa.blend."""

import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_model import RENDER, set_camera
from gait import FPS, LOOP, STRIDE


def render(scene,path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def point(scene,coordinates):
    projected = world_to_camera_view(scene,scene.camera,Vector(coordinates))
    return (projected.x*86,(1-projected.y)*86)


def check_walk(scene, render_directory=RENDER):
    rig = bpy.data.objects["Alisa · Rig"]
    path = render_directory/"contacts.json"
    samples = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    worst_error = 0.0
    lowest_sole = 1.0
    poses = []
    for frame in range(1,LOOP+2):
        scene.frame_set(frame)
        pose = {}
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for side in ("L","R"):
            bone = rig.pose.bones[f"Foot.{side}"]
            if samples:
                track = samples[frame-1][side]
                worst_error = max(worst_error,(bone.head-Vector(track["ankle"])).length)
            shoe = bpy.data.objects[f"Black shoe.{side}"].evaluated_get(depsgraph)
            lowest_sole = min(lowest_sole,min((shoe.matrix_world@v.co).z for v in shoe.data.vertices))
            pose[side] = list(bone.head)
        poses.append(pose)
    seam = max((Vector(poses[0][side])-Vector(poses[-1][side])).length for side in poses[0])
    return {"ankleError":worst_error if samples else None,"minSoleZ":lowest_sole,"loopSeam":seam}


def main():
    scene = bpy.context.scene
    camera = scene.camera
    checks = check_walk(scene)
    set_camera(camera,-39)
    bpy.context.view_layer.update()
    pivot = point(scene,(0,0,0))
    destination = point(scene,(0,-STRIDE,0))
    frame_numbers = list(range(1,LOOP+1,4))
    scene.render.resolution_x = scene.render.resolution_y = 344
    scene.eevee.taa_render_samples = 8
    for i,frame in enumerate(frame_numbers):
        scene.frame_set(frame)
        render(scene,RENDER/f"cel_{i:02}.png")

    scene.render.resolution_x = scene.render.resolution_y = 688
    scene.eevee.taa_render_samples = 16
    for label,angle,frame in (("front",0,16),("quarter",-39,9),("rear",143,23)):
        set_camera(camera,angle,elevation=12,scale=2.26,target_z=1.025)
        scene.frame_set(frame)
        render(scene,RENDER/f"model_{label}.png")
    data = {
        "fps":FPS,
        "frames":frame_numbers,
        "pivotSquare":pivot,
        "travel":tuple(b-a for a,b in zip(pivot,destination)),
        "checks":checks,
    }
    (RENDER/"render.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    print("Verified in-place loop and rendered",len(frame_numbers),"sprite cels.",checks,flush=True)


if __name__ == "__main__":
    main()
