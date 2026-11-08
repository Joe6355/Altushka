"""A constant-volume four-pose reference, not the final character artwork."""
import bpy,math
from mathutils import Vector
from pathlib import Path

R=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.studiolight_rotate_z=.45
scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH'
scene.display.shading.curvature_ridge_factor=1.1
scene.display.shading.curvature_valley_factor=1.0
scene.display.shading.show_object_outline=True
scene.display.shading.object_outline_color=(.025,.025,.03)
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=576;scene.render.resolution_y=344;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.world.color=(.12,.12,.12)
GRAY=(.44,.46,.50,1);DARK=(.11,.12,.14,1);WHITE=(.82,.84,.88,1);SKIN=(.75,.62,.58,1)

def ellipsoid(name,center,scale,color):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=center)
 o=bpy.context.object;o.name=name;o.scale=scale;o.color=color
 for p in o.data.polygons:p.use_smooth=True
 return o

def segment(name,a,b,r1,r2,color):
 a,b=Vector(a),Vector(b);v=b-a
 bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=r1,radius2=r2,depth=v.length,location=(a+b)/2)
 o=bpy.context.object;o.name=name;o.color=color;o.rotation_euler=v.to_track_quat('Z','Y').to_euler()
 for p in o.data.polygons:p.use_smooth=True
 return o

def rings(name,rows,cx,color):
 vertices=[];faces=[];n=24
 for z,rx,ry,dy in rows:
  for j in range(n):
   a=2*math.pi*j/n;vertices.append((cx+rx*math.cos(a),dy+ry*math.sin(a),z))
 for i in range(len(rows)-1):
  for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
 o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);o.color=color
 for p in mesh.polygons:p.use_smooth=True
 return o

def foot(originX,footY,pitch,zlift=0):
 # Shoe pivots around its forefoot. Return the ankle after applying the same
 # rigid transform, so a lifted heel never changes the tibia's bone length.
 angle=math.radians(pitch);c=math.cos(angle);s=math.sin(angle)
 def world(x,y,z):
  dy=y-.145
  return Vector((originX+x,footY+.145+c*dy-s*z,zlift+s*dy+c*z))
 verts=[world(x,y,z) for z in (0,.075) for y in (-.10,.145) for x in (-.063,.063)]
 faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
 mesh=bpy.data.meshes.new('shoe');mesh.from_pydata(verts,[],faces);mesh.update()
 o=bpy.data.objects.new('shoe',mesh);bpy.context.collection.objects.link(o);o.color=DARK
 bevel=o.modifiers.new('soft heel','BEVEL');bevel.width=.018;bevel.segments=2
 o.modifiers.new('normals','WEIGHTED_NORMAL')
 return world(0,0,.075)

def leg(name,hip,ankle):
 h,a=Vector(hip),Vector(ankle);v=a-h;d=v.length;u=v.normalized();l1=.395;l2=.395
 assert d<l1+l2,(name,d)
 t=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-t*t))
 forward=Vector((0,1,0));w=(forward-u*u.dot(forward)).normalized();k=h+u*t+w*height
 # The same bone lengths and girths are used for every pose.
 ellipsoid(name+' hip',h,(.092,.096,.105),GRAY)
 segment(name+' thigh',h,k,.091,.067,GRAY);ellipsoid(name+' knee',k,(.067,.068,.065),GRAY)
 segment(name+' calf',k,a,.064,.038,GRAY)
 ellipsoid(name+' ankle',a,(.039,.043,.050),GRAY)

poses=[
 # pelvisX,hipZ,leftY,leftPitch,leftLift,rightY,rightPitch,rightLift
 (0,.800,.16,0,0,-.16,-28,0),
 (-.035,.780,.08,0,0,-.08,-28,.035),
 (-.045,.800,0,0,0,.005,-12,.085),
 (-.020,.810,-.08,-16,0,.13,8,.018),
]
for i,(px,hz,ly,lp,ll,ry,rp,rl) in enumerate(poses):
 cx=(i-1.5)*.80;dz=hz-.8
 left=foot(cx-.115,ly,lp,ll);right=foot(cx+.115,ry,rp,rl)
 leg('left',(cx+px-.115,0,hz),left);leg('right',(cx+px+.115,0,hz),right)
 torso=rings('body',[(.83+dz,.22,.135,0),(.97+dz,.137,.095,0),(1.12+dz,.205,.13,.025),(1.25+dz,.22,.105,0),(1.31+dz,.105,.075,0)],cx+px,GRAY)
 rings('skirt',[(.965+dz,.145,.10,0),(.89+dz,.21,.15,0),(.745+dz,.265,.185,0)],cx+px,WHITE)
 ellipsoid('head',(cx,0,1.60+dz*.5),(.265,.235,.255),WHITE)
 segment('neck',(cx,0,1.27+dz),(cx,0,1.41+dz*.5),.075,.075,GRAY)
 for side in (-1,1):
  shoulder=(cx+side*.21,0,1.235+dz);elbow=(cx+px+side*.315,-.015,1.075+dz)
  hand=(cx+px+side*.19,-.105,.975+dz)
  segment('upper arm',shoulder,elbow,.055,.045,GRAY);ellipsoid('elbow',elbow,(.047,.047,.047),GRAY)
  segment('forearm',elbow,hand,.043,.038,GRAY);ellipsoid('hand',hand,(.044,.033,.05),SKIN)

bpy.ops.object.camera_add(location=(0,-6,3.5))
cam=bpy.context.object;target=Vector((0,0,.92));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=3.30;scene.camera=cam
# Four equal cells, each36x86logical pixels; a larger proof render is provided
# to the drawing tool while preserving the same orthographic camera.
scene.render.resolution_x=1440;scene.render.resolution_y=860
scene.render.filepath=str(R/'Rear_pose_guide.png');bpy.ops.render.render(write_still=True)
print('Four consistent sagittal-plane poses rendered:',scene.render.filepath)
