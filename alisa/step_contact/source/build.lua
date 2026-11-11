-- A complete front-diagonal step, edited on the existing native Alisa model.
-- The source character, accepted profile and original dance are read-only.
local root=assert(app.params.root)
local out=root..'/alisa/step_contact'
local pc=app.pixelColor
local function rgb(r,g,b) return pc.rgba(r,g,b,255) end
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function round(n) return math.floor(n+.5) end
local ink=rgb(0,0,0)
-- Contact, loading, midstance, passing, heel rise, toe-off, recovery,
-- knee lead, swing through, extension, heel approach, next contact.
-- During stance the shoe moves +2.121,-2.121 px/cel relative to the actor.
-- During recovery the KNEE leads to screen-left; the ankle trails behind it.
local contours={
 {{18,55},{24,55},{24,61},{23,65},{21,69},{19,73},{18,77},{17,81},{18,82},{18,84},{17,85},{11,85},{10,84},{10,83},{12,82},{13,82},{14,78},{14,75},{15,71},{15,68},{16,64},{17,60}},
 {{18,56},{24,56},{25,62},{24,67},{23,71},{21,75},{19,79},{19,80},{20,81},{20,82},{19,83},{12,83},{12,82},{13,81},{15,80},{15,78},{16,74},{17,70},{18,66},{17,62}},
 {{18,56},{24,56},{26,61},{25,66},{24,70},{22,74},{21,77},{21,78},{22,79},{22,80},{21,81},{14,81},{14,80},{15,79},{17,78},{17,75},{18,72},{18,69},{18,65},{17,62}},
 {{18,55},{24,55},{26,60},{26,65},{25,69},{24,72},{23,75},{23,76},{24,77},{24,78},{23,79},{16,79},{16,78},{17,77},{19,76},{19,73},{20,70},{20,67},{19,63},{17,60}},
 {{18,55},{24,55},{27,60},{28,64},{27,68},{26,71},{25,73},{25,74},{26,75},{26,76},{25,77},{18,77},{18,76},{19,75},{21,74},{21,72},{22,69},{22,66},{20,63},{17,60}},
 {{18,55},{24,55},{27,59},{28,63},{28,66},{27,69},{26,71},{27,72},{27,73},{25,74},{21,74},{20,73},{21,71},{23,71},{23,69},{23,66},{22,63},{19,61},{17,59}},
 {{18,55},{24,55},{25,59},{24,63},{24,65},{23,67},{25,69},{28,70},{29,71},{29,72},{27,73},{22,73},{21,72},{22,70},{24,70},{21,68},{19,67},{18,65},{18,62},{17,59}},
 {{18,56},{24,56},{24,60},{22,63},{21,66},{22,68},{24,71},{25,73},{25,75},{23,76},{18,76},{17,75},{18,73},{21,73},{20,71},{17,69},{15,67},{15,64},{16,61},{17,59}},
 {{18,56},{24,56},{23,60},{20,63},{19,66},{19,68},{20,71},{21,75},{22,77},{22,78},{20,79},{15,79},{14,78},{15,76},{18,76},{17,73},{15,70},{13,68},{13,65},{15,61},{17,59}},
 {{18,55},{24,55},{23,60},{20,64},{19,67},{19,70},{19,74},{18,78},{20,79},{20,81},{18,82},{12,82},{11,81},{12,79},{14,78},{14,75},{14,71},{13,68},{14,64},{16,60}},
 {{18,55},{24,55},{23,61},{21,65},{20,68},{19,72},{18,77},{17,80},{18,81},{19,82},{19,83},{17,84},{11,84},{10,83},{11,81},{13,80},{13,77},{14,72},{14,69},{15,65},{16,61}},
 {{18,55},{24,55},{24,61},{22,66},{21,70},{19,75},{17,80},{17,81},{18,82},{18,84},{16,85},{11,85},{10,84},{11,82},{13,81},{13,78},{14,73},{14,69},{16,65},{17,61}}
}
local bob={0,1,1,0,0,0,0,1,1,0,0,0}
local hips={0,1,1,1,0,0,0,-1,-1,-1,0,0}
local hem={0,0,1,1,1,0,0,0,-1,-1,-1,0}
local function pixel(im,x,y,c)
 if x>=0 and x<im.width and y>=0 and y<im.height then im:drawPixel(x,y,c) end
end
local function line(im,a,b,c)
 local x,y=a[1],a[2];local dx,dy=math.abs(b[1]-x),-math.abs(b[2]-y)
 local sx,sy=x<b[1] and 1 or -1,y<b[2] and 1 or -1;local err=dx+dy
 while true do
  pixel(im,x,y,c);if x==b[1] and y==b[2] then break end
  local e=err*2;if e>=dy then err=err+dy;x=x+sx end;if e<=dx then err=err+dx;y=y+sy end
 end
end
local function leg(i,far)
 local points=contours[i];local im=blank();local sole=0
 for _,p in ipairs(points) do sole=math.max(sole,p[2]) end
 for y=0,85 do for x=0,35 do
  local inside=false;local previous=#points
  for k,p in ipairs(points) do
   local q=points[previous]
   if (p[2]>y)~=(q[2]>y) and x<(q[1]-p[1])*(y-p[2])/(q[2]-p[2])+p[1] then inside=not inside end
   previous=k
  end
  if inside then im:drawPixel(x,y,rgb(55,55,60)) end
 end end
 for k,p in ipairs(points) do line(im,p,points[k%#points+1],ink) end
 for y=0,85 do
  local first=36
  for x=0,35 do if pc.rgbaA(im:getPixel(x,y))>0 then first=math.min(first,x) end end
  for x=0,35 do
   local v=im:getPixel(x,y)
   if pc.rgbaA(v)>0 and v~=ink then
    local c=x<=first+1 and (far and rgb(24,24,29) or rgb(34,34,38)) or (far and rgb(34,34,38) or rgb(55,55,60))
    if y<60+bob[i] then c=far and rgb(247,186,188) or rgb(253,243,233) end
    if y>=sole-3 then c=far and rgb(24,24,29) or rgb(34,34,38) end
    im:drawPixel(x,y,c)
   end
  end
 end
 return im
end
local head=Image{fromFile=out..'/source/Head_sw.png'}
local torso=Image{fromFile=out..'/source/Torso_sw.png'}
local skirt=Image{fromFile=out..'/source/Skirt_sw.png'}
local function poseUpper(im,i,cloth)
 local result=blank()
 for y=0,85 do for x=0,35 do
  local dx=0
  if cloth then
   local amount=math.max(0,math.min(1,(y-46)/10))
   dx=round(hips[i]+(hem[i]-hips[i])*amount)
  elseif y>=39 then dx=y<43 and round(hips[i]*.5) or hips[i] end
  pixel(result,x+dx,y+bob[i],im:getPixel(x,y))
 end end
 return result
end
local old=assert(app.open(root..'/alisa/directional_v3/Alisa_directional_v3.aseprite'))
local function layerImage(layer,frame)
 local im=blank();local cel=assert(layer:cel(frame));im:drawImage(cel.image,cel.position);return im
end
local legPath=out..'/source/Legs_sw.aseprite'
local exists=io.open(legPath,'rb')
if exists then exists:close() end
if not exists or app.params.redraw=='true' then
 local source=Sprite(36,86,ColorMode.RGB);source.layers[1].name='дальняя нога'
 local near=source:newLayer();near.name='ближняя нога'
 for i=1,12 do
  if i>1 then source:newEmptyFrame(i) end;source.frames[i].duration=.08
  source:newCel(source.layers[1],i,leg((i+5)%12+1,true),Point(-6,-1))
  source:newCel(near,i,leg(i,false),Point(0,0))
 end
 source:saveAs(legPath);source:close()
end
local legSource=assert(app.open(legPath))
local values,composites={},{}
for i=1,16 do
 local v={}
 if i<=12 then
  local h=blank();h:drawImage(head,Point(0,bob[i]))
  v={layerImage(legSource.layers[1],i),layerImage(legSource.layers[2],i),poseUpper(skirt,i,true),poseUpper(torso,i,false),h}
 else
  -- Reuse the current idle verbatim; no change of face, outfit or stance.
  local frame=32+i
  v={blank(),layerImage(old.layers[1],frame),layerImage(old.layers[2],frame),layerImage(old.layers[3],frame),layerImage(old.layers[4],frame)}
 end
 values[i]=v
 local im=blank();for _,part in ipairs(v) do im:drawImage(part,Point(0,0)) end;composites[i]=im
end
for i=1,16 do
 local from=i<=12 and (i-1+6)%12+1 or i;local v={}
 for k,im in ipairs(values[from]) do v[k]=Image(im);v[k]:flip() end
 values[16+i]=v
 local im=blank();for _,part in ipairs(v) do im:drawImage(part,Point(0,0)) end;composites[16+i]=im
end
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='дальняя нога';local layers={sprite.layers[1]}
for _,name in ipairs({'ближняя нога','подол','корпус и руки','исходная голова'}) do local l=sprite:newLayer();l.name=name;layers[#layers+1]=l end
for i=1,32 do
 if i>1 then sprite:newEmptyFrame(i) end
 sprite.frames[i].duration=(i-1)%16<12 and .08 or .6
 for k,im in ipairs(values[i]) do sprite:newCel(layers[k],i,im,Point(0,0)) end
end
for _,t in ipairs({{'walk_sw',1,12},{'idle_sw',13,16},{'walk_se',17,28},{'idle_se',29,32}}) do
 local tag=sprite:newTag(t[2],t[3]);tag.name=t[1];tag.aniDir=AniDir.FORWARD
end
sprite:saveAs(out..'/Alisa_step_contact.aseprite')
app.command.ExportSpriteSheet{ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=8,
 textureFilename=out..'/Alisa_step_contact_atlas.png',dataFilename=out..'/Alisa_step_contact.json',
 dataFormat=SpriteSheetDataFormat.JSON_ARRAY,trim=false,trimSprite=false,mergeDuplicates=false,
 ignoreEmpty=false,listLayers=true,listTags=true,listSlices=false}
local f=assert(io.open(out..'/Alisa_step_contact.json','r'));local doc=json.decode(f:read('*a'));f:close()
for _,t in ipairs(doc.meta.frameTags) do
 t.pivot={x=18,y=85};t.loop=true;t.rootMotion='in_place'
 t.label=(t.name:sub(1,4)=='walk' and 'Шаг с опорой — ' or 'Прежняя стойка — ')..(t.name:sub(-2)=='sw' and 'вниз-влево' or 'вниз-вправо')
end
f=assert(io.open(out..'/Alisa_step_contact.json','w'));f:write(json.encode(doc));f:close()
local trace={}
for i=1,5 do
 local q=round(i*37.5/math.sqrt(2)*.08);local x,y=10+q,85-q
 assert(pc.rgbaA(values[i+1][2]:getPixel(x,y))>0,'Planted toe missing: '..(i+1))
 trace[i]={frame=i,rootX=-q,rootY=q,toeX=x,toeY=y,worldX=x-q,worldY=y+q}
 assert(trace[i].worldX==10 and trace[i].worldY==85,'Stance toe slides')
end
f=assert(io.open(out..'/source/stance_trace.json','w'));f:write(json.encode(trace));f:close()
local review=blank(480,188)
for it in review:pixels() do it(rgb(105,99,112)) end
for i=1,12 do review:drawImage(composites[i],Point((i-1)*40+2,4));review:drawImage(composites[i+16],Point((i-1)*40+2,98)) end
review:resize(1920,752);review:saveAs(out..'/Alisa_step_contact_review.png')
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local close=Sprite(120,104,ColorMode.RGB);local frame=0
for _,offset in ipairs({0,16}) do for i=1,49 do
 frame=frame+1;if frame>1 then close:newEmptyFrame(frame) end
 close.frames[frame].duration=i<=48 and .08 or .6
 local im=blank(120,104);im:drawImage(floor,Point(-100,-90));im:drawImage(composites[offset+(i<=48 and (i-1)%12+1 or 13)],Point(42,10))
 close:newCel(close.layers[1],frame,im,Point(0,0))
end end
close:resize(720,624);close:saveAs(out..'/Alisa_step_contact_close.gif');close:close()
local game=Sprite(320,240,ColorMode.RGB);local px,py,frame=185,100,0
local function append(im,duration,vx,vy)
 frame=frame+1;if frame>1 then game:newEmptyFrame(frame) end;game.frames[frame].duration=duration
 local image=Image(floor);image:drawImage(im,Point(round(px)-18,round(py)-85))
 game:newCel(game.layers[1],frame,image,Point(0,0))
 px=px+vx*duration;py=py+vy*duration
end
local speed=37.5/math.sqrt(2)
for _,offset in ipairs({0,16}) do
 for i=1,24 do append(composites[offset+(i-1)%12+1],.08,offset==0 and -speed or speed,speed) end
 append(composites[offset+13],.48,0,0)
end
local dance=assert(app.open(root..'/alisa/motion_next/Alisa_motion_next.aseprite'))
for i=62,101 do local im=blank();im:drawSprite(dance,i);append(im,dance.frames[i].duration,0,0) end
game:resize(1280,960);game:saveAs(out..'/Alisa_step_contact_game.gif');game:close();dance:close();legSource:close();old:close();sprite:close()
