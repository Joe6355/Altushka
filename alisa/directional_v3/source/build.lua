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
local function clothWhite(v)
 local r,g,b=pc.rgbaR(v),pc.rgbaG(v),pc.rgbaB(v)
 return pc.rgbaA(v)>0 and math.min(r,g,b)>=140 and math.max(r,g,b)-math.min(r,g,b)<16
end
local function clothing(base)
 local torso,skirt=blank(),blank()
 -- Hands remain with the sleeves, rather than being cut off at row 44 and
 -- carried around by the skirt. Pink thighs/stocking tops are not garment.
 for y=31,48 do for x=0,35 do
  local v=base:getPixel(x,y)
  if y<45 or not clothWhite(v) then torso:drawPixel(x,y,v) end
 end end
 for y=45,57 do for x=0,35 do
  local v=base:getPixel(x,y)
  if clothWhite(v) then skirt:drawPixel(x,y,v) end
 end end
 local white=Image(skirt)
 for y=45,58 do for x=1,34 do
  if pc.rgbaA(white:getPixel(x,y))==0 then
   local adjacent=false
   for _,p in ipairs({{-1,0},{1,0},{0,-1},{0,1}}) do
    local yy=y+p[2]
    if yy>=45 and yy<=57 and pc.rgbaA(white:getPixel(x+p[1],yy))>0 then adjacent=true end
   end
   if adjacent then
    local original=base:getPixel(x,y)
    if pc.rgbaA(original)>0 and math.max(pc.rgbaR(original),pc.rgbaG(original),pc.rgbaB(original))<130 then
     skirt:drawPixel(x,y,original)
    elseif y>=53 and pc.rgbaA(white:getPixel(x,y-1))>0 then
     skirt:drawPixel(x,y,pc.rgba(24,24,29,255))
    end
   end
  end
 end end
 return torso,skirt
end
local function shiftBody(im,dx)
 local result=blank()
 for y=31,48 do for x=0,35 do
  local shift=y<39 and 0 or (y<43 and round(dx*.5) or dx)
  if x+shift>=0 and x+shift<36 then result:drawPixel(x+shift,y,im:getPixel(x,y)) end
 end end
 return result
end
local function shiftCloth(im,hip,hem)
 local result=blank()
 for y=45,58 do for x=0,35 do
  local t=math.max(0,math.min(1,(y-46)/10))
  local dx=round(hip+(hem-hip)*t)
  if x+dx>=0 and x+dx<36 then result:drawPixel(x+dx,y,im:getPixel(x,y)) end
 end end
 return result
end
local bob={0,1,1,1,0,0,0,1,1,1,0,0}
local hips={0,-1,-1,-1,0,0,0,1,1,1,0,0}
local hem={0,0,-1,-1,-1,0,0,0,1,1,1,0}
local sets={}
for _,name in ipairs({'s','n','sw','nw'}) do
 local src=assert(app.open(out..'/source/Native_'..name..'.aseprite'))
 local base=frameImage(src,9)
 local head=crop(base,0,30)
 head:saveAs(out..'/source/Head_'..name..'.png')
 local torso,skirt=clothing(base)
 local breathing=clothing(frameImage(src,1))
 skirt:saveAs(out..'/source/Skirt_'..name..'.png')
 torso:saveAs(out..'/source/Torso_'..name..'.png')
 local nativeLegs=assert(app.open(out..'/source/Legs_'..name..'.aseprite'))
 sets[name]={walk={},idle={},layers={},head=head}
 for i=1,16 do
  local idle=i>12;local index=idle and i-12 or i
  local dy=idle and 0 or bob[i]
  local legImage=frameImage(nativeLegs,idle and 13 or i)
  local body=shiftBody(torso,idle and 0 or hips[i])
  if idle and (index==2 or index==3) then
   -- Preserve the silhouette and front opening during the quiet idle. Only
   -- existing interior sweater shades settle between its two drawn poses.
   for y=33,41 do for x=1,34 do
    local a,b=body:getPixel(x,y),breathing:getPixel(x,y)
    local function dark(v) return pc.rgbaA(v)>0 and math.max(pc.rgbaR(v),pc.rgbaG(v),pc.rgbaB(v))<100 end
    if dark(a) and dark(b) and dark(body:getPixel(x-1,y)) and dark(body:getPixel(x+1,y)) then body:drawPixel(x,y,b) end
   end end
  end
  local cloth=shiftCloth(skirt,idle and 0 or hips[i],idle and 0 or hem[i])
  local values={legImage,cloth,body,head}
  local pos={Point(0,0),Point(0,dy),Point(0,dy),Point(0,dy)}
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
-- the walk by six cels so the same anatomical leg remains in its half-cycle.
for _,pair in ipairs({{'sw','se'},{'nw','ne'}}) do
 local a,b=pair[1],pair[2];sets[b]={walk={},idle={},layers={}}
 for i=1,16 do
  local from=i<=12 and ((i-1+6)%12+1) or i
  local layers={}
  for k,im in ipairs(sets[a].layers[from]) do layers[k]=Image(im);layers[k]:flip() end
  sets[b].layers[i]=layers
  local im=blank();for _,layer in ipairs(layers) do im:drawImage(layer,Point(0,0)) end
  if i<=12 then sets[b].walk[i]=im else sets[b].idle[i-12]=im end
 end
end
local directions={'s','n','sw','se','nw','ne'}
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='ноги — отдельные фазы'
local layers={sprite.layers[1]}
for _,name in ipairs({'подол и бёдра','кофта и руки','постоянное лицо и волосы'}) do
 local l=sprite:newLayer();l.name=name;layers[#layers+1]=l
end
local board=blank(12*40,6*94)
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
local frame=0
for row,name in ipairs(directions) do
 for i=1,16 do
  frame=frame+1;if frame>1 then sprite:newEmptyFrame(frame) end
  sprite.frames[frame].duration=i<=12 and .08 or .6
  for k,im in ipairs(sets[name].layers[i]) do sprite:newCel(layers[k],frame,im,Point(0,0)) end
  if i<=12 then board:drawImage(sets[name].walk[i],Point((i-1)*40+2,(row-1)*94+4)) end
 end
end
for row,name in ipairs(directions) do
 local offset=(row-1)*16
 local t=sprite:newTag(offset+1,offset+12);t.name='walk_'..name;t.aniDir=AniDir.FORWARD
 t=sprite:newTag(offset+13,offset+16);t.name='idle_'..name;t.aniDir=AniDir.FORWARD
end
sprite:saveAs(out..'/Alisa_directional_v3.aseprite')
app.command.ExportSpriteSheet{ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=12,
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
board:resize(1920,2256);board:saveAs(out..'/Alisa_directional_v3_review.png')
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local function still(im,w,h,x,y)
 local image=blank(w,h);image:drawImage(floor,Point(w==320 and 0 or -100,h==240 and 0 or -90))
 image:drawImage(im,Point(x,y));return image
end
-- Six close views, one character at a time, two loops and a short neutral hold.
local close=Sprite(120,104,ColorMode.RGB);local closeFrame=0
for _,name in ipairs(directions) do
 for i=1,25 do
  closeFrame=closeFrame+1;if closeFrame>1 then close:newEmptyFrame(closeFrame) end
  local im=i<=24 and sets[name].walk[(i-1)%12+1] or sets[name].idle[1]
  close.frames[closeFrame].duration=i<=24 and .08 or .6
  close:newCel(close.layers[1],closeFrame,still(im,120,104,42,10),Point(0,0))
 end
end
close:resize(720,624);close:saveAs(out..'/Alisa_directional_v3_smooth.gif');close:close()
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
  local interval=2
  append(sets[name].walk[math.floor(step/interval)+1],.04)
  px=px+vx/length*37.5*.04;py=py+vy/length*37.5*.04
 end
 append(sets[name].idle[1],.48)
end
for i=62,101 do append(frameImage(dance,i),dance.frames[i].duration) end
game:resize(1280,960);game:saveAs(out..'/Alisa_directional_v3_game_smooth.gif')
local poster=Image(game);poster:saveAs(out..'/Alisa_directional_v3_poster.png')
game:close();side:close();sideIdle:close();dance:close();sprite:close()
f=assert(io.open(out..'/source/aseprite_report.txt','w'))
f:write('Aseprite ',tostring(app.version),'\n36x86; 96 cels, 12 tags, 4 layers.\n')
f:write('Walk: 12 x 80ms = 960ms. Idle: 4 x 600ms = 2400ms. Pivot 18,85.\n')
f:write('No automatic leg height normalisation; fixed native hip attachment. Maximum torso bob 1px.\n')
f:write('Six replacement directions; approved E/W and original dance are read-only.\n')
f:close()
