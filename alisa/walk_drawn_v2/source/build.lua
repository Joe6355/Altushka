-- Convert the drawn poses to the original grid in Aseprite. No leg meshes,
-- image morphs, stretched dance fragments or motion interpolation are used.
local root=assert(app.params.root)
local out=root..'/alisa/walk_drawn_v2'
local pc=app.pixelColor
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function rgb(r,g,b) return pc.rgba(r,g,b,255) end
local function round(n) return math.floor(n+.5) end
local input=Image{fromFile=out..'/source/walk_guided_generated.png'}
local original=assert(app.open(root..'/recolor/blue_eyes/Altushka_blue.aseprite'))
local master=blank();master:drawSprite(original,1)
master:saveAs(out..'/source/Original_face_master.png')
local head=blank()
for y=0,30 do for x=0,35 do head:drawPixel(x,y,master:getPixel(x,y)) end end
local function nativeEdit(name)
 local edit=assert(app.open(out..'/source/'..name..'.aseprite'))
 local image=blank();image:drawSprite(edit,1);edit:close();return image
end
local passingLegs=nativeEdit('Pose04_legs')
local firstContact=nativeEdit('Pose01_far')
local lastSupport=nativeEdit('Pose08_near')
local palette={
 {0,0,0},{24,24,29},{34,34,38},{43,43,48},{55,55,60},{70,70,78},
 {154,154,161},{190,190,200},{210,210,215},{212,214,223},{232,232,239},
 {241,242,246},{242,242,245},{255,255,255},{253,243,233},{248,191,190},
 {247,186,188},{229,145,158},{212,112,135}}
local function nativeColor(value,y)
 local r,g,b=pc.rgbaR(value),pc.rgbaG(value),pc.rgbaB(value)
 local l=(r+g+b)/3
 if math.max(r,g,b)-math.min(r,g,b)<30 and l<130 then
  if l<32 then return rgb(0,0,0) end
  if y<46 then
   if l<52 then return rgb(24,24,29) elseif l<80 then return rgb(34,34,38) else return rgb(43,43,48) end
  elseif y>=58 then
   if l<53 then return rgb(24,24,29) elseif l<72 then return rgb(43,43,48) else return rgb(55,55,60) end
  end
 end
 local best,distance=palette[1],math.huge
 for _,p in ipairs(palette) do
  local d=(r-p[1])^2+(g-p[2])^2+(b-p[3])^2
  if d<distance then best,distance=p,d end
 end
 return rgb(best[1],best[2],best[3])
end
-- Neck registration compensates a 32px column displacement in the generated
-- sheet. The original head, torso, skirt and leg proportions define the grid.
local neck={185,185,153,152,184,184,153,152}
local sway={-1,-1,0,1,1,1,0,-1}
local bob={1,1,0,0,1,1,0,0}
local order={1,2,3,4,5,6,7,8}
local durations={.12,.12,.12,.12,.12,.12,.12,.12}
local function sourceY(y)
 if y<=46 then return 169+(y-31)*(248-169)/15 end
 if y<=58 then return 248+(y-46)*(318-248)/12 end
 return 318+(y-58)*(481-318)/27
end
local function pose(frame,idle,index)
 local legs,torso,cloth=blank(),blank(),blank()
 local dy=idle and 0 or bob[frame]
 local hip=idle and 0 or sway[frame]
 local chest=idle and ((index==2 or index==3) and 1 or 0) or 0
 local ox,oy=(frame-1)%4*384,math.floor((frame-1)/4)*512
 for y=29,85 do for x=0,35 do
  local bodyY=y-(y<58 and dy or 0)
  if bodyY>=31 then
   local influence=math.max(0,math.min(1,(bodyY-31)/15))
   local shift=bodyY<58 and hip*influence or 0
   local sy=sourceY(bodyY)
   if idle and bodyY>=32 and bodyY<=41 then sy=sy-chest*5.3 end
   local sx=neck[frame]+(x-17-shift)*5.7
   sx,sy=round(sx)+ox,round(sy)+oy
   if sx>=ox and sx<ox+384 and sy>=oy+168 and sy<oy+512 then
    local value=input:getPixel(sx,sy)
    if pc.rgbaA(value)>=210 then
     local layer=bodyY>=58 and legs or (bodyY>=45 and cloth or torso)
     layer:drawPixel(x,y,nativeColor(value,bodyY))
    end
   end
  end
 end end
 if (frame==1 or frame==4 or frame==8) and not idle then
  -- Keep the drawn hem/thigh pixels at the join with the native leg edit.
  local corrected=frame==4 and Image(passingLegs) or Image(legs)
  if frame~=4 then
   for y=58,85 do for x=0,35 do
    if (frame==1 and x<=19) or (frame==8 and x>=19) then corrected:drawPixel(x,y,0) end
   end end
   corrected:drawImage(frame==1 and firstContact or lastSupport,Point(0,0))
  end
  for y=58,60 do for x=0,35 do
   local value=legs:getPixel(x,y)
   if pc.rgbaA(value)>0 and math.max(pc.rgbaR(value),pc.rgbaG(value),pc.rgbaB(value))>130 then
    corrected:drawPixel(x,y,value)
   end
  end end
  legs=corrected
 end
 return {legs,torso,cloth,head},dy
end
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='отрисованные ноги'
local layers={sprite.layers[1]}
for _,name in ipairs({'кофта и руки','юбка','исходное лицо и волосы'}) do
 local layer=sprite:newLayer();layer.name=name;layers[#layers+1]=layer
end
local cels,idleCels,rightCels,rightIdleCels={},{},{},{}
for frame=1,12 do
 if frame>1 then sprite:newEmptyFrame(frame) end
 local idle=frame>8
 local values,dy=pose(idle and 5 or order[frame],idle,frame-8)
 sprite.frames[frame].duration=idle and .6 or durations[frame]
 for i,image in ipairs(values) do sprite:newCel(layers[i],frame,image,i==4 and Point(0,dy) or Point(0,0)) end
 assert(layers[4]:cel(frame).image:isEqual(head),'Original head changed')
 local composite=blank();composite:drawSprite(sprite,frame)
 for it in composite:pixels() do local a=pc.rgbaA(it());assert(a==0 or a==255,'Fractional alpha') end
 if idle then idleCels[#idleCels+1]=composite else cels[#cels+1]=composite end
end
-- Mirror complete native cels into ordinary animation assets. Rotate the walk
-- by half a cycle so the same anatomical leading leg survives a turn.
for index=1,12 do
 local frame=12+index
 local from=index<=8 and ((index-1+4)%8+1) or index
 sprite:newEmptyFrame(frame)
 sprite.frames[frame].duration=sprite.frames[from].duration
 for _,layer in ipairs(layers) do
  local cel=assert(layer:cel(from))
  local image=blank();image:drawImage(cel.image,cel.position);image:flip()
  sprite:newCel(layer,frame,image,Point(0,0))
 end
 local composite=blank();composite:drawSprite(sprite,frame)
 if index<=8 then rightCels[index]=composite else rightIdleCels[index-8]=composite end
end
local tag=sprite:newTag(1,8);tag.name='walk_sw';tag.aniDir=AniDir.FORWARD
tag=sprite:newTag(9,12);tag.name='idle_sw';tag.aniDir=AniDir.FORWARD
tag=sprite:newTag(13,20);tag.name='walk_se';tag.aniDir=AniDir.FORWARD
tag=sprite:newTag(21,24);tag.name='idle_se';tag.aniDir=AniDir.FORWARD
sprite:saveAs(out..'/Alisa_walk_drawn.aseprite')
app.command.ExportSpriteSheet{ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=8,
 textureFilename=out..'/Alisa_walk_drawn_atlas.png',dataFilename=out..'/Alisa_walk_drawn.json',
 dataFormat=SpriteSheetDataFormat.JSON_ARRAY,trim=false,trimSprite=false,mergeDuplicates=false,
 ignoreEmpty=false,listLayers=true,listTags=true,listSlices=false}
local file=assert(io.open(out..'/Alisa_walk_drawn.json','r'))
local data=json.decode(file:read('*a'));file:close()
for i,t in ipairs(data.meta.frameTags) do
 t.pivot={x=18,y=85};t.loop=true;t.rootMotion='in_place'
 local side=i<=2 and 'влево' or 'вправо'
 t.label=(i%2==1 and 'Полный шаг, 8 фаз — диагональ ' or 'Стойка — диагональ ')..side
end
file=assert(io.open(out..'/Alisa_walk_drawn.json','w'));file:write(json.encode(data));file:close()
local board=blank(8*40,188)
for it in board:pixels() do it(rgb(105,99,112)) end
for i,im in ipairs(cels) do board:drawImage(im,Point((i-1)*40+2,4)) end
for i,im in ipairs(rightCels) do board:drawImage(im,Point((i-1)*40+2,98)) end
board:resize(1920,1128);board:saveAs(out..'/Alisa_walk_drawn_review.png')
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local close=Sprite(120,104,ColorMode.RGB)
for i,im in ipairs(cels) do
 if i>1 then close:newEmptyFrame(i) end
 close.frames[i].duration=durations[i]
 local image=blank(120,104);image:drawImage(floor,Point(-100,-90));image:drawImage(im,Point(42,10))
 close:newCel(close.layers[1],i,image,Point(0,0))
end
close:resize(720,624);close:saveAs(out..'/Alisa_walk_drawn_close.gif');close:close()
local move=Sprite(320,240,ColorMode.RGB)
local rx,ry,frame=160,108,0
local speed=37.5/math.sqrt(2)
local function gameFrame(im,pivot,duration,vx,vy)
 frame=frame+1
 if frame>1 then move:newEmptyFrame(frame) end
 move.frames[frame].duration=duration
 local image=Image(floor)
 image:drawImage(im,Point(round(rx)-pivot,round(ry)-85))
 move:newCel(move.layers[1],frame,image,Point(0,0))
 rx,ry=rx+vx*duration,ry+vy*duration
end
for step=1,16 do gameFrame(cels[(step-1)%8+1],18,.12,-speed,speed) end
gameFrame(idleCels[1],18,.48,0,0)
for step=1,16 do gameFrame(rightCels[(step-1)%8+1],18,.12,speed,speed) end
gameFrame(rightIdleCels[1],18,.48,0,0)
move:resize(1280,960);move:saveAs(out..'/Alisa_walk_drawn_game.gif');move:close()
local idlePreview=Sprite(120,104,ColorMode.RGB)
for i,im in ipairs(idleCels) do
 if i>1 then idlePreview:newEmptyFrame(i) end
 idlePreview.frames[i].duration=.6
 local image=blank(120,104);image:drawImage(floor,Point(-100,-90));image:drawImage(im,Point(42,10))
 idlePreview:newCel(idlePreview.layers[1],i,image,Point(0,0))
end
idlePreview:resize(720,624);idlePreview:saveAs(out..'/Alisa_walk_drawn_idle.gif');idlePreview:close()
sprite:close();original:close()
