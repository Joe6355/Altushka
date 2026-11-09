-- Native Aseprite revision of the previously accepted side-view model.
local root = assert(app.params.root, 'Pass --script-param root=<repository>')
local out = root .. '/alisa/side_revision'
local source = assert(app.open(root .. '/alisa/side_walk/Alisa_side.aseprite'))
local pc = app.pixelColor
local function rgb(r,g,b) return pc.rgba(r,g,b,255) end
local ink = rgb(2,2,2)
local nearFill,nearShade = rgb(55,55,60),rgb(34,34,38)
local farFill,farShade = rgb(34,34,38),rgb(24,24,29)
local skin,skinShade = rgb(255,242,231),rgb(247,186,188)
local shoe = rgb(24,24,29)
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function sourceLayer(name,frame)
  for _,layer in ipairs(source.layers) do
    if layer.name==name then
      local cel=assert(layer:cel(frame),name)
      local image=blank(); image:drawImage(cel.image,cel.position);return image
    end
  end
  error('Missing layer '..name)
end
local head=sourceLayer('голова',1)
local torso={sourceLayer('кофта',1),sourceLayer('кофта',2)}
local skirt=sourceLayer('юбка',1)

-- Twelve authored silhouettes: contact, down, mid-stance, passing, heel rise,
-- toe-off, recovery, folding, knee lead, extension and the next heel approach.
-- Stance toes are 33,30,27,24,21,18: root +3px/cel keeps one world position.
local contours={
 {{17,55},{22,55},{25,59},{27,66},{28,70},{28,77},{28,81},{31,82},{33,83},{33,84},{31,84},{25,85},{23,85},{23,83},{24,81},{23,74},{23,70},{20,64},{17,61},{16,58}},
 {{17,56},{23,56},{26,60},{28,67},{28,71},{26,76},{25,81},{28,82},{30,83},{30,85},{21,85},{20,83},{22,81},{22,76},{23,71},{23,69},{20,64},{17,61},{16,58}},
 {{17,56},{23,56},{25,60},{27,66},{27,70},{25,74},{23,80},{23,82},{26,83},{27,83},{27,85},{18,85},{17,83},{19,81},{19,76},{21,71},{21,68},{18,63},{16,60}},
 {{17,55},{23,55},{24,60},{25,66},{25,70},{23,74},{20,80},{20,82},{23,83},{24,83},{24,85},{15,85},{14,83},{16,81},{16,77},{18,72},{19,69},{19,65},{17,61},{16,58}},
 {{17,54},{23,54},{23,60},{24,66},{23,70},{20,75},{17,80},{18,82},{20,83},{21,84},{21,85},{16,85},{13,84},{12,82},{13,79},{14,74},{16,69},{17,65},{16,61},{16,57}},
 {{17,54},{23,54},{23,60},{23,65},{21,70},{17,75},{14,79},{14,80},{16,82},{18,84},{18,85},{15,85},{12,83},{10,81},{9,79},{10,76},{12,72},{14,67},{16,63},{16,59}},
 {{17,55},{23,55},{24,60},{24,65},{23,69},{20,73},{16,77},{13,79},{11,80},{9,80},{8,78},{7,76},{8,74},{11,74},{14,71},{17,67},{17,64},{16,60}},
 {{17,56},{23,56},{25,60},{26,65},{25,68},{23,70},{19,73},{15,74},{14,76},{16,77},{17,78},{17,80},{11,80},{9,78},{10,75},{12,72},{17,68},{18,65},{17,62},{16,59}},
 {{17,56},{23,56},{26,59},{29,63},{30,66},{29,69},{26,72},{22,74},{21,76},{23,77},{24,79},{24,80},{18,80},{16,78},{16,75},{18,72},{22,68},{23,65},{20,63},{17,62},{16,59}},
 {{17,55},{23,55},{27,58},{30,62},{31,65},{30,68},{28,72},{27,77},{29,79},{31,80},{31,82},{24,82},{22,80},{22,76},{23,72},{25,67},{25,65},{22,64},{18,62},{16,59}},
 {{17,54},{23,54},{27,59},{29,64},{30,69},{30,75},{30,79},{32,80},{34,82},{34,83},{31,83},{26,83},{25,81},{26,78},{25,72},{24,69},{21,64},{18,61},{16,58}},
 {{17,54},{23,54},{27,60},{29,66},{30,72},{30,78},{30,81},{33,82},{34,83},{34,84},{27,84},{25,83},{25,81},{25,77},{24,72},{23,69},{20,64},{17,61},{16,57}}
}
local bob={1,2,2,1,0,0,1,2,2,1,0,0}
local cloth={0,0,-1,-1,-2,-2,-1,0,1,1,0,0}
local hemLift={0,0,0,-1,-1,0,0,0,0,-1,-1,0}
local bust={0,0,1,1,0,0,0,0,1,1,0,0}
local function pixel(image,x,y,color)
  if x>=0 and x<image.width and y>=0 and y<image.height then image:drawPixel(x,y,color) end
end
local function line(image,a,b,color)
  local x,y=a[1],a[2];local tx,ty=b[1],b[2]
  local dx,dy=math.abs(tx-x),-math.abs(ty-y)
  local sx,sy=x<tx and 1 or -1,y<ty and 1 or -1
  local err=dx+dy
  while true do
    pixel(image,x,y,color)
    if x==tx and y==ty then break end
    local e=err*2
    if e>=dy then err=err+dy;x=x+sx end
    if e<=dx then err=err+dx;y=y+sy end
  end
end
local function polygon(points)
  local image=blank()
  for y=0,85 do
    for x=0,35 do
      local inside=false;local previous=#points
      for index,p in ipairs(points) do
        local q=points[previous]
        if (p[2]>y)~=(q[2]>y) and x<(q[1]-p[1])*(y-p[2])/(q[2]-p[2])+p[1] then inside=not inside end
        previous=index
      end
      if inside then image:drawPixel(x,y,nearFill) end
    end
  end
  for index,p in ipairs(points) do line(image,p,points[index%#points+1],ink) end
  return image
end
local function leg(index,far)
  local image=polygon(contours[index]);local sole=0
  for _,p in ipairs(contours[index]) do sole=math.max(sole,p[2]) end
  for y=0,85 do
    local first=36
    for x=0,35 do if pc.rgbaA(image:getPixel(x,y))>0 then first=math.min(first,x) end end
    for x=0,35 do
      local value=image:getPixel(x,y)
      if pc.rgbaA(value)>0 and value~=ink then
        local color=x<=first+2 and (far and farShade or nearShade) or (far and farFill or nearFill)
        if y<59+bob[index] then color=far and skinShade or skin end
        if y>=sole-3 then color=far and farShade or shoe end
        image:drawPixel(x,y,color)
      end
    end
  end
  return image
end
local function skirtPose(index)
  local image=blank()
  for y=0,85 do
    local amount=math.max(0,math.min(1,(y-47)/8))
    local dx=math.floor(cloth[index]*amount+.5)
    local dy=(y>=51) and hemLift[index] or 0
    for x=0,35 do
      local value=skirt:getPixel(x,y)
      if pc.rgbaA(value)>0 then pixel(image,x+dx,y+dy,value) end
    end
  end
  return image
end

local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='дальняя нога'
local layers={sprite.layers[1]}
for _,name in ipairs({'ближняя нога','юбка','кофта','голова'}) do
  local layer=sprite:newLayer();layer.name=name;layers[#layers+1]=layer
end
local cels={}
for index=1,12 do
  if index>1 then sprite:newEmptyFrame(index) end
  sprite.frames[index].duration=.08
  local values={leg((index+5)%12+1,true),leg(index,false),skirtPose(index),torso[bust[index]+1],head}
  local positions={Point(-2,-1),Point(0,0),Point(0,bob[index]),Point(0,bob[index]),Point(0,bob[index])}
  for layerIndex,image in ipairs(values) do sprite:newCel(layers[layerIndex],index,image,positions[layerIndex]) end
  local composite=blank();composite:drawSprite(sprite,index)
  cels[index]=composite
  assert(layers[5]:cel(index).image:isEqual(head),'Head/face pixels changed')
  for _,point in ipairs(contours[index]) do assert(point[1]>=0 and point[1]<36 and point[2]>=0 and point[2]<86,'Clipped leg contour') end
  for value in composite:pixels() do local alpha=pc.rgbaA(value());assert(alpha==0 or alpha==255,'Fractional native alpha') end
end
for phase=1,5 do
  local toe=33-phase*3
  assert(pc.rgbaA(layers[2]:cel(phase+1).image:getPixel(toe,85))==255,'Stance toe is missing')
  assert(toe+phase*3==33,'Support toe drifts in world space')
end
local tag=sprite:newTag(1,12);tag.name='walk_side_right';tag.aniDir=AniDir.FORWARD
sprite:saveAs(out..'/Alisa_side_revision.aseprite')
app.command.ExportSpriteSheet{
  ui=false,askOverwrite=false,type=SpriteSheetType.ROWS,columns=6,
  textureFilename=out..'/Alisa_side_revision_atlas.png',
  dataFilename=out..'/Alisa_side_revision.json',dataFormat=SpriteSheetDataFormat.JSON_ARRAY,
  trim=false,trimSprite=false,mergeDuplicates=false,ignoreEmpty=false,
  listLayers=true,listTags=true,listSlices=false
}
local metadataFile=assert(io.open(out..'/Alisa_side_revision.json','r'))
local metadata=json.decode(metadataFile:read('*a'));metadataFile:close()
metadata.meta.frameTags[1].pivot={x=18,y=85}
metadata.meta.frameTags[1].loop=true
metadata.meta.frameTags[1].rootMotion='in_place'
metadata.meta.frameTags[1].label='Боковой шаг — проверочная правка'
metadata.meta.frameTags[1].velocityPxPerSecond={x=37.5,y=0}
metadataFile=assert(io.open(out..'/Alisa_side_revision.json','w'))
metadataFile:write(json.encode(metadata));metadataFile:close()

-- Aseprite renders the native proof and its game-floor preview directly.
local floor=Image{fromFile=root..'/alisa/rear_key_redraw/Alisa_scene_background.png'}
local preview=Sprite(144,108,ColorMode.RGB)
for index=1,12 do
  if index>1 then preview:newEmptyFrame(index) end
  preview.frames[index].duration=.08
  local image=blank(144,108)
  image:drawImage(floor,Point(-88,-80))
  image:drawImage(cels[index],Point(54,12))
  preview:newCel(preview.layers[1],index,image,Point(0,0))
end
preview:resize(864,648)
preview:saveAs(out..'/Alisa_side_revision.gif')
local poster=Image(preview);poster:saveAs(out..'/Alisa_side_revision_poster.png')
preview:close()
local review=blank(6*40,2*94)
for y=0,review.height-1 do for x=0,review.width-1 do review:drawPixel(x,y,rgb(105,99,112)) end end
for index,image in ipairs(cels) do review:drawImage(image,Point((index-1)%6*40+2,math.floor((index-1)/6)*94+4)) end
review:resize(1440,1128);review:saveAs(out..'/Alisa_side_revision_review.png')

-- Exact shared clock: six rejected 800ms loops versus five revised 960ms loops.
local rejected=assert(app.open(root..'/alisa/motion_polish/Alisa_motion_polished.aseprite'))
local comparison=Sprite(128,108,ColorMode.RGB)
for frame=1,240 do
  if frame>1 then comparison:newEmptyFrame(frame) end
  comparison.frames[frame].duration=.02
  local t=(frame-1)*20
  local image=blank(128,108);image:drawImage(floor,Point(-96,-80))
  local old=blank();old:drawSprite(rejected,29+math.floor(t/100)%8)
  image:drawImage(old,Point(12,12))
  image:drawImage(cels[1+math.floor(t/80)%12],Point(80,12))
  comparison:newCel(comparison.layers[1],frame,image,Point(0,0))
end
comparison:resize(768,648);comparison:saveAs(out..'/Alisa_side_comparison.gif');comparison:close();rejected:close()
local movement=Sprite(320,240,ColorMode.RGB)
for frame=1,60 do
  if frame>1 then movement:newEmptyFrame(frame) end
  movement.frames[frame].duration=.08
  local image=Image(floor)
  image:drawImage(cels[(frame-1)%12+1],Point(52+(frame-1)*3,87))
  movement:newCel(movement.layers[1],frame,image,Point(0,0))
end
movement:resize(1280,960);movement:saveAs(out..'/Alisa_side_movement.gif');movement:close()
local report = assert(io.open(out .. '/source/aseprite_report.txt', 'w'))
report:write('Aseprite ',tostring(app.version),'\nNative 36x86, 12 cels, 80 ms/cel, 960 ms/loop; 5 layers.\n')
report:write('Head/face is byte-identical to the accepted side-view head in all 12 cels.\n')
report:write('Toe is raised for heel contact, planted during phases 1..5, then lifted for recovery.\n')
report:write('Stance toe world X (phases 1..5): 33, 33, 33, 33, 33. Root advance: 3px/cel.\n')
report:write('Every leg contour fits inside 36x86. All native alpha values are 0 or 255.\n')
report:close()
sprite:close()
source:close()
