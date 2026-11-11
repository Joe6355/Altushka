-- One native cel, authored against the neighbouring passing/contact cels.
-- This initialization is separate from the build: subsequent Aseprite edits
-- to Pose04_legs.aseprite remain the source of truth.
local root=assert(app.params.root)
local pc=app.pixelColor
local function rgb(r,g,b) return pc.rgba(r,g,b,255) end
local far={
 {12,17},{12,17},{13,17},{13,18},{13,18},{14,18},{14,18},
 {14,19},{15,19},{15,20},{16,20},{16,21},{17,21},{17,22},
 {18,22},{18,23},{19,23},{19,23},{19,23},{19,23},{19,24},
 {19,25},{18,25},{18,24}}
local near={
 {17,23},{17,23},{17,23},{17,23},{17,23},{17,23},{18,23},
 {18,23},{18,24},{18,24},{18,24},{18,24},{18,24},{18,23},
 {18,23},{18,23},{17,22},{17,22},{17,22},{17,22},{17,21},
 {17,21},{16,21},{15,21},{14,20},{14,20},{15,19}}
local function paint(rows,back)
 local im=Image(36,86,ColorMode.RGB)
 local fill=back and rgb(43,43,48) or rgb(55,55,60)
 local shade=back and rgb(24,24,29) or rgb(43,43,48)
 local shoe=back and rgb(34,34,38) or rgb(55,55,60)
 for i,span in ipairs(rows) do
  local y=57+i
  for x=span[1],span[2] do
   local color=fill
   if x==span[1]+1 or (y>=67 and y<=73 and x==span[2]-1) then color=shade end
   if y>=79 then color=shoe end
   im:drawPixel(x,y,color)
  end
 end
 local mask=Image(im)
 local function solid(x,y)
  return x>=0 and x<36 and y>=0 and y<86 and pc.rgbaA(mask:getPixel(x,y))>0
 end
 for y=58,85 do for x=0,35 do
  if solid(x,y) and (not solid(x-1,y) or not solid(x+1,y) or not solid(x,y-1) or not solid(x,y+1)) then
   im:drawPixel(x,y,rgb(0,0,0))
  end
 end end
 return im
end
local sprite=Sprite(36,86,ColorMode.RGB)
sprite.layers[1].name='дальняя нога — опора'
sprite:newCel(sprite.layers[1],1,paint(far,true),Point(0,0))
local layer=sprite:newLayer();layer.name='ближняя нога — выход к контакту'
sprite:newCel(layer,1,paint(near,false),Point(0,0))
sprite:saveAs(root..'/alisa/walk_drawn_v2/source/Pose04_legs.aseprite')
local image=Image(36,86,ColorMode.RGB);image:drawSprite(sprite,1)
image:saveAs(root..'/alisa/walk_drawn_v2/source/Pose04_legs.png')
sprite:close()

local firstContact={
 {11,18},{11,18},{11,18},{11,18},{11,17},{11,17},{11,17},
 {11,17},{11,17},{11,17},{11,17},{10,16},{10,16},{10,16},
 {10,16},{10,16},{10,16},{10,15},{10,15},{10,15},{10,15},
 {10,15},{10,15},{9,15},{8,15},{7,14},{7,14},{8,13}}
local lastSupport={
 {20,25},{20,25},{20,25},{20,25},{20,25},{20,25},{20,25},
 {20,25},{20,26},{20,26},{20,26},{20,26},{21,26},{21,26},
 {21,26},{21,26},{21,26},{21,26},{21,26},{21,26},{21,26},
 {21,26},{21,26},{20,26},{19,26},{18,25},{18,25},{19,24}}
local function single(name,label,rows)
 local s=Sprite(36,86,ColorMode.RGB);s.layers[1].name=label
 local im=paint(rows,false)
 s:newCel(s.layers[1],1,im,Point(0,0))
 s:saveAs(root..'/alisa/walk_drawn_v2/source/'..name..'.aseprite')
 im:saveAs(root..'/alisa/walk_drawn_v2/source/'..name..'.png');s:close()
end
single('Pose01_far','дальняя нога — контакт',firstContact)
single('Pose08_near','ближняя нога — завершение опоры',lastSupport)
