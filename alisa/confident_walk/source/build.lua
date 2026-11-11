-- Native Aseprite animation of the original 36x86 Alisa, not a new character.
local root=assert(app.params.root)
local out=root..'/alisa/confident_walk'
local file=assert(io.open(out..'/source/poses.json','r'))
local plan=json.decode(file:read('*a'));file:close()
local source=assert(app.open(root..'/recolor/blue_eyes/Altushka_blue.aseprite'))
local pc=app.pixelColor
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function round(v) return math.floor(v+.5) end
local function pixel(im,x,y,value)
  if x>=0 and y>=0 and x<im.width and y<im.height then im:drawPixel(x,y,value) end
end
local master=blank();master:drawSprite(source,6)
local head,body,skirt=blank(),blank(),blank()
local skirtSpans={
 [43]={18,18},[44]={9,18},[45]={9,19},[46]={9,20},[47]={5,21},
 [48]={3,22},[49]={1,22},[50]={0,23},[51]={0,23},[52]={1,23},
 [53]={0,24},[54]={0,24},[55]={1,25},[56]={3,25},[57]={4,24},[58]={4,13}}
for y=0,85 do for x=0,35 do
  local color=master:getPixel(x,y)
  local span=skirtSpans[y]
  if span and x>=span[1] and x<=span[2] then skirt:drawPixel(x,y,color)
  elseif y<=30 then head:drawPixel(x,y,color)
  elseif y<=46 then body:drawPixel(x,y,color) end
end end

local function legSource(far)
  local im=blank()
  for y=54,81 do for x=0,35 do
    local belongs=(far and x<=14) or (not far and x>=16)
    local color=master:getPixel(x,y)
    if y>=59 and belongs then im:drawPixel(x,y,color)
    elseif y==58 and not far and belongs then im:drawPixel(x,y,color) end
  end end
  -- Hidden thigh texture, exposed only between the skirt and stocking top.
  local left,right=far and 7 or 16,far and 13 or 23
  for y=53,58 do for x=left,right do
    local value=pc.rgba(253,243,233,255)
    if x==left or x==right then value=pc.rgba(0,0,0,255)
    elseif x==left+1 then value=pc.rgba(248,191,190,255) end
    if y<58 or far then im:drawPixel(x,y,value) end
  end end
  return im
end
local textures={legSource(true),legSource(false)}
local srcJoints={{{10.0,55},{9.0,69},{6.2,81}},{{19.6,55},{24.0,69},{28.1,81}}}
local function add(a,b) return {a[1]+b[1],a[2]+b[2]} end
local function normal(a,b)
  local dx,dy=b[1]-a[1],b[2]-a[2];local length=math.sqrt(dx*dx+dy*dy)
  return {dy/length,-dx/length}
end
local function cross(a,b) return a[1]*b[2]-a[2]*b[1] end
local function sub(a,b) return {a[1]-b[1],a[2]-b[2]} end
local function times(a,t) return {a[1]*t,a[2]*t} end
local function side(p,n,width) return add(p,times(n,width)) end
local function triangle(target,texture,dst,src)
  local ab,ac=sub(dst[2],dst[1]),sub(dst[3],dst[1])
  local det=cross(ab,ac)
  if math.abs(det)<.01 then return end
  local minX,maxX=35,0;local minY,maxY=85,0
  for _,p in ipairs(dst) do minX=math.min(minX,math.floor(p[1]-1));maxX=math.max(maxX,math.ceil(p[1]+1));minY=math.min(minY,math.floor(p[2]-1));maxY=math.max(maxY,math.ceil(p[2]+1)) end
  for y=math.max(0,minY),math.min(85,maxY) do for x=math.max(0,minX),math.min(35,maxX) do
    local ap={x-dst[1][1],y-dst[1][2]}
    local u,v=cross(ap,ac)/det,cross(ab,ap)/det
    if u>=-.001 and v>=-.001 and u+v<=1.001 then
      local sx=round(src[1][1]+u*(src[2][1]-src[1][1])+v*(src[3][1]-src[1][1]))
      local sy=round(src[1][2]+u*(src[2][2]-src[1][2])+v*(src[3][2]-src[1][2]))
      if sx>=0 and sx<36 and sy>=0 and sy<86 then
        local value=texture:getPixel(sx,sy)
        if pc.rgbaA(value)>0 then target:drawPixel(x,y,value) end
      end
    end
  end end
end
local function quad(target,texture,dst,src)
  triangle(target,texture,{dst[1],dst[2],dst[3]},{src[1],src[2],src[3]})
  triangle(target,texture,{dst[1],dst[3],dst[4]},{src[1],src[3],src[4]})
end
local function filledPolygon(im,points,value)
  for y=0,85 do for x=0,35 do
    local inside=false;local last=#points
    for i,p in ipairs(points) do
      local q=points[last]
      if (p[2]>y)~=(q[2]>y) and x<(q[1]-p[1])*(y-p[2])/(q[2]-p[2])+p[1] then inside=not inside end
      last=i
    end
    if inside then im:drawPixel(x,y,value) end
  end end
end
local function cleanContour(im,index)
  local original=Image(im)
  local ink=pc.rgba(0,0,0,255)
  local fill=pc.rgba(index==1 and 43 or 55,index==1 and 43 or 55,index==1 and 48 or 60,255)
  local shade=pc.rgba(index==1 and 24 or 36,index==1 and 24 or 36,index==1 and 29 or 42,255)
  local function opaque(x,y)
    return x>=0 and y>=0 and x<36 and y<86 and pc.rgbaA(original:getPixel(x,y))>0
  end
  -- Remove sampling holes and restore a continuous, one-pixel contour. This
  -- preserves the textured silhouette rather than drawing cylindrical bones.
  for y=50,85 do for x=1,34 do
    if not opaque(x,y) and opaque(x-1,y) and opaque(x+1,y) then
      im:drawPixel(x,y,fill)
    end
  end end
  original=Image(im)
  for y=50,85 do for x=0,35 do
    local value=original:getPixel(x,y)
    if pc.rgbaA(value)>0 then
      if not opaque(x-1,y) or not opaque(x+1,y) or not opaque(x,y-1) or not opaque(x,y+1) then
        im:drawPixel(x,y,ink)
      elseif pc.rgbaR(value)<15 and pc.rgbaG(value)<15 and pc.rgbaB(value)<15 then
        im:drawPixel(x,y,shade)
      end
    end
  end end
end
local function stockingSilhouette(texture,dst,index)
  local centers,widths={}, {3.6,3.9,3.8,3.3,2.9,3.1,3.2,2.8,2.5}
  -- A shared tangent through the knee avoids two rigid, disconnected tubes.
  local function catmull(a,b,c,d,t)
    local value={}
    for axis=1,2 do
      value[axis]=.5*((2*b[axis])+(-a[axis]+c[axis])*t+
        (2*a[axis]-5*b[axis]+4*c[axis]-d[axis])*t*t+
        (-a[axis]+3*b[axis]-3*c[axis]+d[axis])*t*t*t)
    end
    return value
  end
  local before=sub(times(dst[1],2),dst[2])
  local after=sub(times(dst[3],2),dst[2])
  for i=0,4 do centers[#centers+1]=catmull(before,dst[1],dst[2],dst[3],i/4) end
  for i=1,4 do centers[#centers+1]=catmull(dst[1],dst[2],dst[3],after,i/4) end
  local outline,left,right={},{},{}
  for i,p in ipairs(centers) do
    local n=normal(centers[math.max(1,i-1)],centers[math.min(#centers,i+1)])
    left[i]=side(p,n,-widths[i]);right[i]=side(p,n,widths[i])
  end
  for _,p in ipairs(left) do outline[#outline+1]=p end
  for i=#right,1,-1 do outline[#outline+1]=right[i] end
  local im=blank();filledPolygon(im,outline,pc.rgba(55,55,60,255))
  for y=0,85 do for x=0,35 do
    if pc.rgbaA(im:getPixel(x,y))>0 then
      local value=texture:getPixel(x,y)
      if pc.rgbaA(value)==0 or (pc.rgbaR(value)<15 and pc.rgbaG(value)<15) then
        value=pc.rgba(index==1 and 43 or 55,index==1 and 43 or 55,index==1 and 48 or 60,255)
      end
      im:drawPixel(x,y,value)
    end
  end end
  return im
end
local function leg(index,pose)
  local im=blank();local src=srcJoints[index]
  local dst={pose.hip,pose.knee,pose.ankle}
  local sn1,sn2=normal(src[1],src[2]),normal(src[2],src[3])
  local dn1,dn2=normal(dst[1],dst[2]),normal(dst[2],dst[3])
  local snk,dnk=add(sn1,sn2),add(dn1,dn2)
  snk=times(snk,1/math.sqrt(snk[1]^2+snk[2]^2));dnk=times(dnk,1/math.sqrt(dnk[1]^2+dnk[2]^2))
  local function edge(points,normals)
    return {{side(points[1],normals[1],-6),side(points[1],normals[1],6),side(points[2],normals[2],6),side(points[2],normals[2],-6)},
            {side(points[2],normals[2],-6),side(points[2],normals[2],6),side(points[3],normals[3],6),side(points[3],normals[3],-6)}}
  end
  local s,d=edge(src,{sn1,snk,sn2}),edge(dst,{dn1,dnk,dn2})
  quad(im,textures[index],d[1],s[1]);quad(im,textures[index],d[2],s[2])
  im=stockingSilhouette(im,dst,index)
  -- A small flat sole faces forward on both feet. It is articulated separately
  -- so a raised heel does not turn the whole lower leg into a hinged boot.
  local shoe=Image(8,5,ColorMode.RGB)
  local spans={{3,7},{3,7},{1,7},{0,7},{0,6}}
  for row,span in ipairs(spans) do for x=span[1],span[2] do
    shoe:drawPixel(x,row-1,pc.rgba(36,36,42,255))
  end end
  local angle=-pose.roll;local ca,sa=math.cos(angle),math.sin(angle)
  for y=0,85 do for x=0,35 do
    local dx,dy=x-dst[3][1],y-dst[3][2]
    local u,v=ca*dx+sa*dy,-sa*dx+ca*dy
    local sx,sy=round(u+5),round(v+1)
    if sy>=0 and sy<5 and sx>=0 and sx<8 then
      local value=shoe:getPixel(sx,sy)
      if pc.rgbaA(value)>0 then im:drawPixel(x,y,value) end
    end
  end end
  cleanContour(im,index)
  return im
end
local function torso(p)
  local im=blank()
  for y=29,49 do for x=0,35 do
    local t=math.max(0,math.min(1,(y-30)/16))
    local dx=3+p.sway*(-.3+1.3*t)
    local chest=math.max(0,math.min(1,(y-30)/2,(42-y)/4))
    local dy=round(p.bob)+round(.7*math.sin(2*p.phase-.9))*chest
    local sx,sy=round(x-dx),round(y-dy)
    if sx>=0 and sx<36 and sy>=0 and sy<86 then im:drawPixel(x,y,body:getPixel(sx,sy)) end
  end end
  return im
end
local function cloth(p)
  local im=blank()
  for y=40,62 do for x=0,35 do
    local t=math.max(0,math.min(1,(y-44)/14))
    local strength=p.idle and .2 or 1
    local dx=3+p.sway+strength*1.6*math.sin(p.phase-.65)*t
    local dy=p.bob+strength*(.6*math.sin(p.phase-.35)*(x-16)/13*t+.55*math.sin(2*p.phase-.8)*t)
    local sx,sy=round(x-dx),round(y-dy)
    if sx>=0 and sx<36 and sy>=0 and sy<86 then im:drawPixel(x,y,skirt:getPixel(sx,sy)) end
  end end
  return im
end
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='дальняя нога'
local layers={sprite.layers[1]}
for _,name in ipairs({'ближняя нога','кофта и руки','юбка','исходное лицо и волосы'}) do
 local layer=sprite:newLayer();layer.name=name;layers[#layers+1]=layer
end
local cels={}
for frame,p in ipairs(plan.poses) do
  if frame>1 then sprite:newEmptyFrame(frame) end
  sprite.frames[frame].duration=.06
  local values={leg(1,p.legs[1]),leg(2,p.legs[2]),torso(p),cloth(p),head}
  local hx,hy=3+round(-p.sway*.3),round(p.bob)
  for i,image in ipairs(values) do sprite:newCel(layers[i],frame,image,i==5 and Point(hx,hy) or Point(0,0)) end
  local composite=blank();composite:drawSprite(sprite,frame);cels[frame]=composite
  assert(layers[5]:cel(frame).image:isEqual(head),'Original head pixels changed')
  for it in composite:pixels() do
    local alpha=pc.rgbaA(it());assert(alpha==0 or alpha==255,'Fractional alpha')
  end
end
local idleCels={}
for index=1,8 do
  local frame=20+index;sprite:newEmptyFrame(frame);sprite.frames[frame].duration=.3
  local p={phase=(index-1)/8*math.pi,sway=0,bob=0,idle=true}
  local far={hip={15.1,54},knee={14.6,67},ankle={13.8,79.6},roll=0}
  local near={hip={21.6,54},knee={22.1,67},ankle={23.8,80.6},roll=0}
  local values={leg(1,far),leg(2,near),torso(p),cloth(p),head}
  for i,image in ipairs(values) do sprite:newCel(layers[i],frame,image,i==5 and Point(3,0) or Point(0,0)) end
  local composite=blank();composite:drawSprite(sprite,frame);idleCels[index]=composite
end
-- Create tags after appending frames: Aseprite otherwise extends a tag ending
-- at the insertion point to include the newly appended idle cels.
local tag=sprite:newTag(1,20);tag.name='walk_sw_reference';tag.aniDir=AniDir.FORWARD
tag=sprite:newTag(21,28);tag.name='idle_sw_reference';tag.aniDir=AniDir.FORWARD
sprite:saveAs(out..'/Alisa_confident_walk.aseprite')
app.command.ExportSpriteSheet{ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=10,
 textureFilename=out..'/Alisa_confident_walk_atlas.png',dataFilename=out..'/Alisa_confident_walk.json',
 dataFormat=SpriteSheetDataFormat.JSON_ARRAY,trim=false,trimSprite=false,mergeDuplicates=false,
 ignoreEmpty=false,listLayers=true,listTags=true,listSlices=false}
file=assert(io.open(out..'/Alisa_confident_walk.json','r'))
local metadata=json.decode(file:read('*a'));file:close()
local info=metadata.meta.frameTags[1]
info.pivot={x=18,y=85};info.loop=true;info.rootMotion='in_place'
info.label='Плавная походка — передняя левая диагональ, проверочный цикл'
info.velocityPxPerSecond={x=plan.rootVelocity[1],y=-plan.rootVelocity[2]}
info=metadata.meta.frameTags[2];info.pivot={x=18,y=85};info.loop=true;info.rootMotion='in_place'
info.label='Стойка к проверочной походке — передняя левая диагональ'
file=assert(io.open(out..'/Alisa_confident_walk.json','w'));file:write(json.encode(metadata));file:close()
local sheet=blank(400,188)
for it in sheet:pixels() do it(pc.rgba(105,99,112,255)) end
for i,im in ipairs(cels) do sheet:drawImage(im,Point((i-1)%10*40+2,math.floor((i-1)/10)*94+4)) end
sheet:resize(2000,940);sheet:saveAs(out..'/Alisa_confident_walk_review.png')
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local close=Sprite(120,104,ColorMode.RGB)
for frame,im in ipairs(cels) do
  if frame>1 then close:newEmptyFrame(frame) end
  close.frames[frame].duration=.06
  local image=blank(120,104);image:drawImage(floor,Point(-100,-90));image:drawImage(im,Point(42,10))
  close:newCel(close.layers[1],frame,image,Point(0,0))
end
close:resize(720,624);close:saveAs(out..'/Alisa_confident_walk_close.gif');close:close()
local idlePreview=Sprite(120,104,ColorMode.RGB)
for frame,im in ipairs(idleCels) do
  if frame>1 then idlePreview:newEmptyFrame(frame) end
  idlePreview.frames[frame].duration=.3
  local image=blank(120,104);image:drawImage(floor,Point(-100,-90));image:drawImage(im,Point(42,10))
  idlePreview:newCel(idlePreview.layers[1],frame,image,Point(0,0))
end
idlePreview:resize(720,624);idlePreview:saveAs(out..'/Alisa_confident_idle.gif');idlePreview:close()
local movement=Sprite(320,240,ColorMode.RGB)
for frame=1,100 do
  if frame>1 then movement:newEmptyFrame(frame) end
  movement.frames[frame].duration=.06
  local image=Image(floor);local f=frame-1
  image:drawImage(cels[f%20+1],Point(225+round(plan.rootVelocity[1]*f*.06),60+round(plan.rootVelocity[2]*f*.06)))
  movement:newCel(movement.layers[1],frame,image,Point(0,0))
end
movement:resize(1280,960);movement:saveAs(out..'/Alisa_confident_walk_game.gif');movement:close()
sprite:close();source:close()
