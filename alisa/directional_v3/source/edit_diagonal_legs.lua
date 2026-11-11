-- Native contour edits for the two diagonal views. The generated roughs kept
-- repeating one leading foot; each silhouette here is an authored cel, as in
-- the accepted SideRevision. No mesh deformation or tweening is used.
local root=assert(app.params.root)
local out=root..'/alisa/directional_v3/source'
local pc=app.pixelColor
local function rgb(r,g,b) return pc.rgba(r,g,b,255) end
local ink=rgb(0,0,0)
local function blank() return Image(36,86,ColorMode.RGB) end
local shapes={
 sw={
  {{18,55},{24,55},{23,61},{21,68},{19,72},{17,78},{16,81},{17,82},{17,84},{14,85},{10,85},{9,84},{10,82},{12,81},{12,79},{14,72},{15,68},{16,61}},
  {{18,56},{24,56},{24,62},{23,68},{22,72},{19,78},{18,81},{19,82},{19,84},{16,85},{13,85},{12,84},{13,82},{14,80},{15,76},{17,71},{17,67},{17,62}},
  {{18,56},{24,56},{25,62},{25,68},{24,72},{22,77},{21,80},{22,81},{22,82},{19,83},{16,83},{15,82},{16,80},{17,77},{18,72},{19,68},{18,63}},
  {{18,55},{24,55},{26,61},{27,66},{27,70},{25,75},{24,78},{25,79},{25,81},{22,82},{20,81},{19,80},{20,78},{21,74},{22,69},{21,66},{18,62}},
  {{18,54},{24,54},{27,60},{29,65},{30,68},{29,72},{27,76},{28,77},{29,78},{28,80},{24,80},{22,79},{22,77},{24,73},{24,69},{22,66},{19,63},{17,60}},
  {{18,54},{24,54},{28,59},{30,63},{30,66},{28,69},{26,72},{26,73},{28,74},{28,76},{24,77},{22,76},{21,74},{22,71},{24,67},{24,65},{22,63},{18,61},{17,58}},
  {{18,55},{24,55},{27,59},{28,63},{27,66},{24,69},{22,73},{21,75},{23,76},{23,78},{19,79},{17,78},{16,76},{17,73},{19,69},{21,65},{20,63},{17,61}},
  {{18,55},{24,55},{25,60},{25,65},{23,69},{20,73},{18,78},{17,80},{19,81},{19,83},{15,84},{12,84},{11,83},{12,81},{14,79},{14,76},{16,70},{17,66},{16,61}}
 },
 nw={
  {{18,55},{24,55},{23,60},{21,64},{19,68},{17,73},{15,75},{15,76},{16,77},{15,79},{11,79},{8,78},{8,76},{11,75},{12,73},{13,69},{15,64},{16,60}},
  {{18,56},{24,56},{24,62},{23,67},{22,70},{19,75},{18,78},{18,79},{19,80},{18,81},{14,82},{11,81},{10,79},{12,78},{13,76},{14,72},{16,67},{17,63}},
  {{18,56},{24,56},{25,62},{26,68},{25,72},{23,77},{22,80},{23,81},{22,83},{18,84},{15,83},{14,82},{15,80},{17,78},{18,73},{19,69},{18,64}},
  {{18,55},{24,55},{27,61},{28,67},{28,71},{26,77},{26,81},{27,82},{26,84},{23,85},{20,85},{19,83},{20,81},{21,77},{22,72},{22,68},{19,63},{17,60}},
  {{18,54},{24,54},{28,60},{30,67},{31,71},{30,77},{29,80},{30,82},{30,84},{27,85},{24,85},{23,83},{24,80},{24,77},{25,72},{24,69},{21,64},{18,61},{17,58}},
  {{18,54},{24,54},{28,58},{30,63},{30,67},{28,71},{27,75},{28,77},{29,78},{28,80},{25,81},{23,80},{22,78},{23,75},{24,71},{24,67},{22,64},{18,61},{17,58}},
  {{18,55},{24,55},{27,58},{29,62},{28,66},{26,69},{23,72},{22,75},{24,76},{24,78},{20,79},{18,78},{17,76},{18,73},{20,70},{22,66},{21,64},{18,62},{17,59}},
  {{18,55},{24,55},{25,59},{25,63},{23,67},{20,70},{18,73},{17,74},{19,75},{19,77},{15,78},{12,77},{11,75},{12,73},{14,71},{15,67},{17,63},{16,60}}
 }
}
local function pixel(im,x,y,c)
 if x>=0 and x<36 and y>=0 and y<86 then im:drawPixel(x,y,c) end
end
local function line(im,a,b,c)
 local x,y=a[1],a[2];local dx,dy=math.abs(b[1]-x),-math.abs(b[2]-y)
 local sx,sy=x<b[1] and 1 or -1,y<b[2] and 1 or -1
 local err=dx+dy
 while true do
  pixel(im,x,y,c);if x==b[1] and y==b[2] then break end
  local e=err*2
  if e>=dy then err=err+dy;x=x+sx end
  if e<=dx then err=err+dx;y=y+sy end
 end
end
local bob={1,2,1,0,1,2,1,0}
local function leg(points,far,index)
 local im=blank();local sole=0
 for _,p in ipairs(points) do sole=math.max(sole,p[2]) end
 for y=0,85 do for x=0,35 do
  local inside=false;local last=#points
  for i,p in ipairs(points) do
   local q=points[last]
   if (p[2]>y)~=(q[2]>y) and x<(q[1]-p[1])*(y-p[2])/(q[2]-p[2])+p[1] then inside=not inside end
   last=i
  end
  if inside then im:drawPixel(x,y,rgb(55,55,60)) end
 end end
 for i,p in ipairs(points) do line(im,p,points[i%#points+1],ink) end
 for y=0,85 do
  local first=36
  for x=0,35 do if pc.rgbaA(im:getPixel(x,y))>0 then first=math.min(first,x) end end
  for x=0,35 do
   local v=im:getPixel(x,y)
   if pc.rgbaA(v)>0 and v~=ink then
    local color=x<=first+2 and (far and rgb(24,24,29) or rgb(34,34,38)) or (far and rgb(43,43,48) or rgb(55,55,60))
    if y<60+bob[index] then color=far and rgb(247,186,188) or rgb(253,243,233) end
    if y>=sole-3 then color=far and rgb(24,24,29) or rgb(34,34,38) end
    im:drawPixel(x,y,color)
   end
  end
 end
 return im
end
for _,name in ipairs({'sw','nw'}) do
 local s=Sprite(36,86,ColorMode.RGB);local far=s.layers[1];far.name='дальняя нога'
 local near=s:newLayer();near.name='ближняя нога'
 for i=1,8 do
  if i>1 then s:newEmptyFrame(i) end
  s.frames[i].duration=.12
  s:newCel(far,i,leg(shapes[name][(i+3)%8+1],true,(i+3)%8+1),Point(-6,-1))
  s:newCel(near,i,leg(shapes[name][i],false,i),Point(0,0))
 end
 s:saveAs(out..'/Legs_'..name..'.aseprite');s:close()
end
