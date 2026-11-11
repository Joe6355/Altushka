-- Positional drawing reference only. Blue and red identify the two limbs.
local root=assert(app.params.root)
local pc=app.pixelColor
local src=assert(app.open(root..'/recolor/blue_eyes/Altushka_blue.aseprite'))
local original=Image(36,86,ColorMode.RGB);original:drawSprite(src,6)
local phases={
 {{{13,55},{11,68},{9,81}},{{20,55},{23,67},{28,77}}},
 {{{13,55},{12,68},{11,80}},{{20,55},{23,67},{24,74}}},
 {{{13,55},{13,68},{13,79}},{{20,55},{20,65},{19,74}}},
 {{{13,55},{13,68},{15,78}},{{20,55},{17,66},{16,78}}},
 {{{13,55},{15,68},{17,77}},{{20,55},{17,69},{15,81}}},
 {{{13,55},{12,68},{14,74}},{{20,55},{18,69},{17,80}}},
 {{{13,55},{10,65},{10,74}},{{20,55},{20,68},{19,79}}},
 {{{13,55},{8,66},{7,78}},{{20,55},{20,68},{21,78}}}}
local canvas=Image(1536,1024,ColorMode.RGB)
local function capsule(im,a,b,width,color)
 local dx,dy=b[1]-a[1],b[2]-a[2];local l=dx*dx+dy*dy
 for y=0,85 do for x=0,35 do
  local t=math.max(0,math.min(1,((x-a[1])*dx+(y-a[2])*dy)/l))
  if (x-a[1]-t*dx)^2+(y-a[2]-t*dy)^2<=width^2 then im:drawPixel(x,y,color) end
 end end
end
local colors={pc.rgba(35,125,245,255),pc.rgba(245,60,65,255)}
for frame,legs in ipairs(phases) do
 local im=Image(36,86,ColorMode.RGB)
 for side,p in ipairs(legs) do
  capsule(im,p[1],p[2],3.4,colors[side]);capsule(im,p[2],p[3],2.8,colors[side])
  for y=p[3][2]+1,p[3][2]+3 do for x=p[3][1]-4,p[3][1]+2 do im:drawPixel(x,y,colors[side]) end end
 end
 for y=0,58 do for x=0,35 do
  local c=original:getPixel(x,y)
  if pc.rgbaA(c)>0 then im:drawPixel(x,y,c) end
 end end
 im:resize(180,430)
 canvas:drawImage(im,Point((frame-1)%4*384+120,math.floor((frame-1)/4)*512+30))
end
canvas:saveAs(root..'/alisa/walk_drawn_v2/source/pose_guide.png');src:close()
