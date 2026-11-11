"""Animate one complete walk with heel contact, support, toe-off and recovery."""

from math import cos, pi, sin, sqrt
from pathlib import Path
import json

import bpy
from mathutils import Matrix, Quaternion, Vector


FPS = 60
LOOP = 60
STRIDE = .96
RELEASE = .60
TAU = 2*pi


def leg_points(sign):
    return tuple((sign*.105,y,z) for y,z in (
        (.010,.895),(-.025,.477),(.005,.089),(-.162,.047),
    ))


def eased(t):
    t = min(1.0,max(0.0,t))
    return t*t*(3-2*t)


def roll_quaternion(pitch, yaw):
    return Quaternion((0,0,1),yaw) @ Quaternion((1,0,0),pitch)


def support_foot(step, sign, shoe_length=1.0):
    ground_y = -.283 + STRIDE*step
    yaw = .066*sign
    ankle = Vector((sign*.079,ground_y,.089))
    if step < .105:
        angle = -.235*(1-eased(step/.105))
        pivot = Vector((0,.069*shoe_length,-.074))
    elif step > .463:
        angle = .565*eased((step-.463)/(RELEASE-.463))
        pivot = Vector((0,-.166*shoe_length,-.074))
    else:
        return ankle,roll_quaternion(0,yaw),ankle+Vector((0,0,-.075))
    flat = roll_quaternion(0,yaw)
    rotation = roll_quaternion(angle,yaw)
    anchor = ankle+flat@pivot
    return anchor-rotation@pivot,rotation,anchor


def cubic(t, start, end, start_tangent, end_tangent):
    return ((2*t**3-3*t**2+1)*start + (-2*t**3+3*t**2)*end
            + (t**3-2*t**2+t)*start_tangent + (t**3-t**2)*end_tangent)


def foot_at(step, sign, shoe_length=1.0):
    if step <= RELEASE:
        return support_foot(step,sign,shoe_length)
    t = (step-RELEASE)/(1-RELEASE)
    back,_,_ = support_foot(RELEASE,sign,shoe_length)
    front,_,_ = support_foot(0.0,sign,shoe_length)
    position = Vector((
        cubic(t,back.x,front.x,0,0)+sign*.022*sin(pi*t)**2,
        cubic(t,back.y,front.y,STRIDE*(1-RELEASE),STRIDE*(1-RELEASE)),
        cubic(t,back.z,front.z,0,0)+.105*sin(pi*t)**2*(1+.34*cos(pi*t)),
    ))
    pitch = cubic(t,.565,-.235,0,0)-.153*sin(pi*t)**2
    yaw = .066*sign-.058*sign*sin(pi*t)**2
    return position,roll_quaternion(pitch,yaw),None


def solve_knee(hip, ankle, femur, shin, forward):
    ray = ankle-hip
    distance = min(ray.length,femur+shin-.0001)
    error = ray.length-distance
    direction = ray.normalized()
    ankle = hip+direction*distance
    knee_axis = (forward-direction*forward.dot(direction)).normalized()
    projected = (femur*femur-shin*shin+distance*distance)/(2*distance)
    offset = sqrt(max(0.0,femur*femur-projected*projected))
    return hip+direction*projected+knee_axis*offset,ankle,error


def rotate_relative(bone, rotation):
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_quaternion = rest.inverted()@rotation@rest


def place_bone(bone, head, swing):
    rotation = swing@bone.bone.matrix_local.to_quaternion()
    bone.matrix = Matrix.Translation(head)@rotation.to_matrix().to_4x4()


def skirt_clearance(obj, cloth, sides, sample, pelvis, frame, weights):
    """Keep the pleats outside the raised thighs during the pass and toe-off."""
    if (frame-1)%2:
        return
    key = obj.shape_key_add(name=f"Leg clearance {frame:02}", from_mix=False)
    basis = obj.data.shape_keys.reference_key.data
    inv = pelvis.bone.matrix_local@pelvis.matrix.inverted()
    segments = []
    for side in ("L","R"):
        hip = inv@Vector(sample[side]["hip"])
        knee = inv@Vector(sample[side]["knee"])
        segment = knee-hip
        segments.append((hip,segment.normalized(),segment.length))
    displacements = []
    rays = []
    for i,p in enumerate(basis):
        posed = p.co.copy()
        for shape,weight in zip(cloth,weights):
            if weight > 0:
                posed += weight*(shape.data[i].co-p.co)
        radial = Vector((posed.x,posed.y-.010,0))
        radius = radial.length
        ray = radial.normalized()
        rays.append(ray)
        need = radius
        if posed.z < .949:
            origin = Vector((0,.010,posed.z))
            thigh_radius = .096+.015*eased((posed.z-.748)/.101)-.028*eased((posed.z-.855)/.070)
            thigh_radius += .009 if i//sides < 8 else .004
            for hip,axis,length in segments:
                offset = origin-hip
                direction_dot = ray.dot(axis)
                origin_dot = offset.dot(axis)
                a = 1-direction_dot*direction_dot
                b = ray.dot(offset)-direction_dot*origin_dot
                c = offset.length_squared-origin_dot*origin_dot-thigh_radius**2
                disc = b*b-a*c
                if disc <= 0 or a < 1e-6:
                    continue
                edge = (-b+sqrt(disc))/a
                along = origin_dot+edge*direction_dot
                if -.037 < along < length:
                    need = max(need,edge)
        displacements.append(max(0,need-radius)*eased((.949-posed.z)/.049))
    for i,p in enumerate(key.data):
        row,angle = divmod(i,sides)
        falloff = ((0,1),(-1,.99),(1,.99),(-2,.94),(2,.94),(-3,.83),(3,.83),(-4,.72),(4,.72))
        shift = max(displacements[row*sides+(angle+step)%sides]*weight for step,weight in falloff)
        p.co += rays[i]*shift
    for at,value in ((frame-2,0),(frame,1),(frame+2,0)):
        key.value = value
        key.keyframe_insert("value",frame=at)


def set_loop_keys(action, rig):
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = LOOP+1
    action.use_cyclic = True
    channel = action.layers[0].strips[0].channelbag(rig.animation_data.action_slot)
    for fcurve in channel.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "LINEAR"
        fcurve.modifiers.new("CYCLES")


def add_walk(scene,rig,skirt,rebound,*,shoe_length=1.0,contact_path=None):
    scene.render.fps = FPS
    scene.frame_start,scene.frame_end = 1,LOOP
    pelvis = rig.pose.bones["Pelvis"]
    skirt_obj,cloth,skirt_sides = skirt
    rest_pelvis = pelvis.bone.matrix_local.to_quaternion()
    capture = []
    last_quat = {}
    for frame in range(1,LOOP+2):
        scene.frame_set(frame)
        phase = ((frame-1)%LOOP)/LOOP
        wave = TAU*phase
        dip = 2*wave-.22
        pelvis.location = rest_pelvis.inverted()@Vector((
            .032*sin(wave-.20),
            .011*sin(dip+.52),
            -.033-.021*cos(dip),
        ))
        yaw = Quaternion((0,0,1),-.112*cos(wave-.02))
        bank = Quaternion((0,1,0),-.091*sin(wave+.33))
        pitch = Quaternion((1,0,0),.035*sin(dip+.25))
        rotate_relative(pelvis,yaw@bank@pitch)
        rotate_relative(rig.pose.bones["Spine"],
                        Quaternion((0,1,0),.060*sin(wave+.23))
                        @Quaternion((0,0,1),.151*cos(wave-.12))
                        @Quaternion((1,0,0),-.052+.025*sin(dip-.35)))
        rotate_relative(rig.pose.bones["Chest"],
                        Quaternion((1,0,0),.018*sin(dip-.52))
                        @Quaternion((0,1,0),.012*cos(wave)))
        rotate_relative(rig.pose.bones["Head"],
                        Quaternion((0,0,1),-.030*cos(wave-.25))
                        @Quaternion((0,1,0),.026*sin(wave-.14))
                        @Quaternion((1,0,0),.024-.022*sin(dip-.66)))
        rotate_relative(rig.pose.bones["Curl"],
                        Quaternion((0,1,0),.105*sin(wave-.81))
                        @Quaternion((1,0,0),.078*sin(dip-.91)))
        bpy.context.view_layer.update()
        sample = {}
        for side,sign,delay in (("L",1,0),("R",-1,.5)):
            rest_hip,rest_knee,rest_ankle,_ = map(Vector,leg_points(sign))
            thigh = rig.pose.bones[f"Thigh.{side}"]
            shin = rig.pose.bones[f"Shin.{side}"]
            foot = rig.pose.bones[f"Foot.{side}"]
            step = (phase+delay)%1
            ankle,rotation,anchor = foot_at(step,sign,shoe_length)
            hip = pelvis.matrix @ pelvis.bone.matrix_local.inverted() @ rest_hip
            knee,ankle,extension = solve_knee(hip,ankle,(rest_knee-rest_hip).length,
                                             (rest_ankle-rest_knee).length,yaw@Vector((sign*.10,-1,0)))
            place_bone(thigh,hip,(rest_knee-rest_hip).rotation_difference(knee-hip))
            bpy.context.view_layer.update()
            place_bone(shin,knee,(rest_ankle-rest_knee).rotation_difference(ankle-knee))
            bpy.context.view_layer.update()
            place_bone(foot,ankle,rotation)
            rotate_relative(rig.pose.bones[f"Hair.{side}"],
                            Quaternion((0,1,0),.067*sin(wave-.69+sign*.34))
                            @Quaternion((1,0,0),.052*sin(dip-.86+sign*.38)))
            rotate_relative(rig.pose.bones[f"UpperArm.{side}"],
                            Quaternion((1,0,0),sign*.041*cos(wave-.6))
                            @Quaternion((0,0,1),.035*sin(wave-.35)))
            rotate_relative(rig.pose.bones[f"Forearm.{side}"],
                            Quaternion((1,0,0),-sign*.054*cos(wave-.6)))
            sample[side] = {
                "hip": list(hip), "ankle": list(ankle), "knee": list(knee), "step": step,
                "anchor": list(anchor) if anchor is not None else None,
                "extension": extension,
            }
        capture.append(sample)
        for bone in rig.pose.bones:
            quat = bone.rotation_quaternion.copy()
            if bone.name in last_quat and quat.dot(last_quat[bone.name])<0:
                quat.negate()
            bone.rotation_quaternion = quat
            last_quat[bone.name] = quat
            bone.keyframe_insert("rotation_quaternion",frame=frame,group=bone.name)
            if bone.name.startswith(("Pelvis","Thigh","Shin","Foot")):
                bone.keyframe_insert("location",frame=frame,group=bone.name)
        hip_swing = sin(wave-.88)
        hem_swing = sin(dip-.93)
        weights = tuple(max(0.0,value) for value in (hip_swing,-hip_swing,hem_swing,-hem_swing))
        for key,value in zip(cloth,weights):
            key.value = value
            key.keyframe_insert("value",frame=frame)
        for key in rebound:
            key.value = .5+.48*sin(dip-.98)
            key.keyframe_insert("value",frame=frame)
        skirt_clearance(skirt_obj,cloth,skirt_sides,sample,pelvis,frame,weights)

    action = rig.animation_data.action
    action.name = "Alisa | Walk in place"
    set_loop_keys(action,rig)
    keys = skirt_obj.data.shape_keys
    skirt_action = keys.animation_data.action
    skirt_action.name = "Alisa | Skirt follow-through"
    slot = skirt_action.layers[0].strips[0].channelbag(keys.animation_data.action_slot)
    for fcurve in slot.fcurves:
        if "Leg clearance" in fcurve.data_path:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"
    rig["Stride per cycle"] = STRIDE
    rig["Loop frames"] = LOOP
    rig["Motion"] = "Walking, hands on hips"
    for label,frame in (("Contact L",1),("Support L",14),("Contact R",31),("Support R",44)):
        scene.timeline_markers.new(label,frame=frame)
    if contact_path is None:
        contact_path = Path(__file__).resolve().parents[3]/".tools"/"alisa_blender"/"contacts.json"
    contact_path.parent.mkdir(parents=True,exist_ok=True)
    contact_path.write_text(json.dumps(capture,indent=2),encoding="utf-8")
