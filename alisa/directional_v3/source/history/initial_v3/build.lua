-- Assemble the six replacement directions on the original grid. A/D and the
-- original dance are referenced only for the game preview; they are never saved.
local root=assert(app.params.root)
local out=root..'/alisa/directional_v3'
local pc=app.pixelColor
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function round(n) return math.floor(n+.5) end
local function crop(im,first,last)
 local result=blank()
 for y=first,last do for x=0,35 do result:drawPixel(x,y,im:getPixel(x,y)) end end
 return result
end
local function frameImage(s,i)
 local im=blank();im:drawSprite(s,i);return im
end
local function grounded(im)
 local bottom=-1
 for y=0,85 do for x=0,35 do if pc.rgbaA(im:getPixel(x,y))>0 then bottom=math.max(bottom,y) end end end
 local result=blank();result:drawImage(im,Point(0,85-bottom))
 -- A few generated recovery poses end above the common sole line. After
 -- registration, continue their topmost thigh pixels underneath the hem,
 -- rather than leaving a transparent horizontal cut between body and legs.
 for x=0,35 do
  local first=nil
  for y=55,66 do if pc.rgbaA(result:getPixel(x,y))>0 then first=y;break end end
  if first and first>58 then
   local value=result:getPixel(x,first)
   for y=58,first-1 do result:drawPixel(x,y,value) end
  end
 end
 return result
end
local bob={1,2,1,0,1,2,1,0}
local hips={0,-1,-1,0,1,1,0,0}
local bust={false,false,true,true,false,false,true,true}
local sets={}
for _,name in ipairs({'s','n','sw','nw'}) do
 local src=assert(app.open(out..'/source/Native_'..name..'.aseprite'))
 local base=frameImage(src,9)
 local head=crop(base,0,30)
 head:saveAs(out..'/source/Head_'..name..'.png')
 local torso=crop(base,31,44)
 local alternate=crop(frameImage(src,1),31,40)
 local nativeLegs=(name=='sw' or name=='nw') and assert(app.open(out..'/source/Legs_'..name..'.aseprite')) or nil
 sets[name]={walk={},idle={},layers={},head=head}
 for i=1,12 do
  local idle=i>8;local index=idle and i-8 or i
  local dy=idle and 0 or bob[i]
  local legImage=grounded(idle and crop(base,60,85) or (nativeLegs and frameImage(nativeLegs,i) or crop(frameImage(src,i),60,85)))
  local body=Image(torso)
  if (idle and index==3) or (not idle and bust[i]) then
   -- Two drawn chest poses settle one phase after compression.
   for y=31,40 do for x=0,35 do body:drawPixel(x,y,0) end end
   body:drawImage(alternate,Point(0,0))
  end
  local clothFrame=idle and 9 or ({9,1,1,9,9,5,5,9})[i]
  local cloth=crop(frameImage(src,clothFrame),45,59)
  local values={legImage,cloth,body,head}
  local pos={Point(0,0),Point(idle and 0 or hips[i],dy),Point(0,dy),Point(0,dy)}
  local layers={}
  for k,im in ipairs(values) do layers[k]=blank();layers[k]:drawImage(im,pos[k]) end
  local composite=blank()
  for _,im in ipairs(layers) do composite:drawImage(im,Point(0,0)) end
  sets[name].layers[i]=layers
  if idle then sets[name].idle[index]=composite else sets[name].walk[i]=composite end
 end
 if nativeLegs then nativeLegs:close() end
 src:close()
end
-- Mirroring complete native cels preserves the counterpart's model. Rotate
-- the walk by four cels so the same anatomical leg remains in its half-cycle.
for _,pair in ipairs({{'sw','se'},{'nw','ne'}}) do
 local a,b=pair[1],pair[2];sets[b]={walk={},idle={},layers={}}
 for i=1,12 do
  local from=i<=8 and ((i-1+4)%8+1) or i
  local layers={}
  for k,im in ipairs(sets[a].layers[from]) do layers[k]=Image(im);layers[k]:flip() end
  sets[b].layers[i]=layers
  local im=blank();for _,layer in ipairs(layers) do im:drawImage(layer,Point(0,0)) end
  if i<=8 then sets[b].walk[i]=im else sets[b].idle[i-8]=im end
 end
end
local directions={'s','n','sw','se','nw','ne'}
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='ноги — отдельные фазы'
local layers={sprite.layers[1]}
for _,name in ipairs({'подол и бёдра','кофта и руки','постоянное лицо и волосы'}) do
 local l=sprite:newLayer();l.name=name;layers[#layers+1]=l
end
local board=blank(8*40,6*94)
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
local frame=0
for row,name in ipairs(directions) do
 for i=1,12 do
  frame=frame+1;if frame>1 then sprite:newEmptyFrame(frame) end
  sprite.frames[frame].duration=i<=8 and .12 or .6
  for k,im in ipairs(sets[name].layers[i]) do sprite:newCel(layers[k],frame,im,Point(0,0)) end
  if i<=8 then board:drawImage(sets[name].walk[i],Point((i-1)*40+2,(row-1)*94+4)) end
 end
end
for row,name in ipairs(directions) do
 local offset=(row-1)*12
 local t=sprite:newTag(offset+1,offset+8);t.name='walk_'..name;t.aniDir=AniDir.FORWARD
 t=sprite:newTag(offset+9,offset+12);t.name='idle_'..name;t.aniDir=AniDir.FORWARD
end
sprite:saveAs(out..'/Alisa_directional_v3.aseprite')
app.command.ExportSpriteSheet{ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=8,
 textureFilename=out..'/Alisa_directional_v3_atlas.png',dataFilename=out..'/Alisa_directional_v3.json',
 dataFormat=SpriteSheetDataFormat.JSON_ARRAY,trim=false,trimSprite=false,mergeDuplicates=false,
 ignoreEmpty=false,listLayers=true,listTags=true,listSlices=false}
local f=assert(io.open(out..'/Alisa_directional_v3.json','r'));local doc=json.decode(f:read('*a'));f:close()
local names={s='к камере',n='от камеры',sw='вниз-влево',se='вниз-вправо',nw='вверх-влево',ne='вверх-вправо'}
for _,t in ipairs(doc.meta.frameTags) do
 local walk=t.name:sub(1,4)=='walk';local d=t.name:match('_([a-z]+)$')
 t.pivot={x=18,y=85};t.loop=true;t.rootMotion='in_place'
 t.label=(walk and 'Шаг — ' or 'Стойка — ')..names[d]
 t.cycleMs=walk and 960 or 2400
end
f=assert(io.open(out..'/Alisa_directional_v3.json','w'));f:write(json.encode(doc));f:close()
board:resize(1280,2256);board:saveAs(out..'/Alisa_directional_v3_review.png')
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local function still(im,w,h,x,y)
 local image=blank(w,h);image:drawImage(floor,Point(w==320 and 0 or -100,h==240 and 0 or -90))
 image:drawImage(im,Point(x,y));return image
end
-- Six close views, one character at a time, two loops and a short neutral hold.
local close=Sprite(120,104,ColorMode.RGB);local closeFrame=0
for _,name in ipairs(directions) do
 for i=1,17 do
  closeFrame=closeFrame+1;if closeFrame>1 then close:newEmptyFrame(closeFrame) end
  local im=i<=16 and sets[name].walk[(i-1)%8+1] or sets[name].idle[1]
  close.frames[closeFrame].duration=i<=16 and .12 or .6
  close:newCel(close.layers[1],closeFrame,still(im,120,104,42,10),Point(0,0))
 end
end
close:resize(720,624);close:saveAs(out..'/Alisa_directional_v3_close.gif');close:close()
-- Actual game scale and speed, approved A/D and dance included unchanged.
local side=assert(app.open(root..'/alisa/side_revision/Alisa_side_revision.aseprite'))
local sideIdle=assert(app.open(root..'/alisa/side_walk/Alisa_side.aseprite'))
local dance=assert(app.open(root..'/alisa/motion_next/Alisa_motion_next.aseprite'))
local e,w={walk={},idle={}},{walk={},idle={}}
for i=1,12 do e.walk[i]=frameImage(side,i);w.walk[i]=frameImage(side,(i-1+6)%12+1);w.walk[i]:flip() end
e.idle[1]=frameImage(sideIdle,1);w.idle[1]=Image(e.idle[1]);w.idle[1]:flip();sets.e=e;sets.w=w
local game=Sprite(320,240,ColorMode.RGB);local gameFrame=0
local px,py=185,110
local function append(im,duration)
 gameFrame=gameFrame+1;if gameFrame>1 then game:newEmptyFrame(gameFrame) end
 game.frames[gameFrame].duration=duration
 game:newCel(game.layers[1],gameFrame,still(im,320,240,round(px)-18,round(py)-85),Point(0,0))
end
local paths={{'s',0,1},{'sw',-1,1},{'w',-1,0},{'nw',-1,-1},{'n',0,-1},{'ne',1,-1},{'e',1,0},{'se',1,1}}
for _,path in ipairs(paths) do
 local name,vx,vy=table.unpack(path);local length=math.sqrt(vx*vx+vy*vy)
 for step=0,23 do
  local interval=(name=='e' or name=='w') and 2 or 3
  append(sets[name].walk[math.floor(step/interval)+1],.04)
  px=px+vx/length*37.5*.04;py=py+vy/length*37.5*.04
 end
 append(sets[name].idle[1],.48)
end
for i=62,101 do append(frameImage(dance,i),dance.frames[i].duration) end
game:resize(1280,960);game:saveAs(out..'/Alisa_directional_v3_game.gif')
local poster=Image(game);poster:saveAs(out..'/Alisa_directional_v3_poster.png')
game:close();side:close();sideIdle:close();dance:close();sprite:close()
f=assert(io.open(out..'/source/aseprite_report.txt','w'))
f:write('Aseprite ',tostring(app.version),'\n36x86; 72 cels, 12 tags, 4 layers.\n')
f:write('Walk: 8 x 120ms = 960ms. Idle: 4 x 600ms = 2400ms. Pivot 18,85.\n')
f:write('Six replacement directions; approved E/W and original dance are read-only.\n')
f:close()
