-- Sampling and palette cleanup in Aseprite. Source drawings are kept intact.
local root=assert(app.params.root)
local out=root..'/alisa/directional_v3/source'
local pc=app.pixelColor
local function blank(w,h) return Image(w or 36,h or 86,ColorMode.RGB) end
local function round(n) return math.floor(n+.5) end
local function rgba(c) return pc.rgba(c[1],c[2],c[3],255) end
local palette={
 {0,0,0},{24,24,29},{34,34,38},{43,43,48},{55,55,60},{70,70,78},
 {154,154,161},{190,190,200},{210,210,215},{212,214,223},{232,232,239},
 {241,242,246},{242,242,245},{255,255,255},{253,243,233},{248,191,190},
 {247,186,188},{229,145,158},{212,112,135},{50,190,225},{91,218,238},{171,239,246}}
local function color(value,y)
 local r,g,b=pc.rgbaR(value),pc.rgbaG(value),pc.rgbaB(value)
 local l=(r+g+b)/3
 if math.max(r,g,b)-math.min(r,g,b)<30 and l<130 then
  if l<32 then return rgba(palette[1]) end
  if y<46 then
   if l<52 then return rgba(palette[2]) elseif l<80 then return rgba(palette[3]) else return rgba(palette[4]) end
  else
   if l<53 then return rgba(palette[2]) elseif l<72 then return rgba(palette[4]) else return rgba(palette[5]) end
  end
 end
 local best,distance=palette[1],math.huge
 for _,p in ipairs(palette) do
  local d=(r-p[1])^2+(g-p[2])^2+(b-p[3])^2
  if d<distance then best,distance=p,d end
 end
 return rgba(best)
end
local config={
 s={file='S',center=208,top=24,neck=159,waist=224,hem=278,sole=394},
 n={file='N',center=208,top=26,neck=151,waist=211,hem=272,sole=400},
 sw={file='SW',center=207,top=30,neck=165,waist=228,hem=281,sole=403},
 nw={file='NW',center=200,top=27,neck=151,waist=210,hem=272,sole=397}}
local board=blank(8*40,4*94)
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
for row,name in ipairs({'s','n','sw','nw'}) do
 local c=config[name]
 local input=Image{fromFile=out..'/'..c.file..'_generated.png'}
 local cell=input.width/3
 local function sourceY(y)
  if y<=30 then return c.top+y*(c.neck-c.top)/31 end
  if y<=46 then return c.neck+(y-31)*(c.waist-c.neck)/15 end
  if y<=58 then return c.waist+(y-46)*(c.hem-c.waist)/12 end
  return c.hem+(y-58)*(c.sole-c.hem)/27
 end
 local native={}
 for frame=1,9 do
  local ox,oy=(frame-1)%3*cell,math.floor((frame-1)/3)*cell
  local im=blank()
  for y=0,85 do for x=0,35 do
   local sx,sy=round(ox+c.center+(x-17.5)*4.35),round(oy+sourceY(y))
   if sx>=ox and sx<ox+cell and sy>=oy and sy<oy+cell then
    local value=input:getPixel(sx,sy)
    if pc.rgbaA(value)>=210 then im:drawPixel(x,y,color(value,y)) end
   end
  end end
  native[frame]=im
 end
 local sprite=Sprite(36,86,ColorMode.RGB)
 local layer=sprite.layers[1];layer.name='исходные позы в сетке 36x86'
 for frame=1,9 do
  if frame>1 then sprite:newEmptyFrame(frame) end
  sprite.frames[frame].duration=frame==9 and .6 or .12
  sprite:newCel(layer,frame,native[frame],Point(0,0))
  if frame<=8 then board:drawImage(native[frame],Point((frame-1)*40+2,(row-1)*94+4)) end
 end
 sprite:saveAs(out..'/Native_'..name..'.aseprite');sprite:close()
end
board:resize(1920,2256);board:saveAs(out..'/Native_raw_review.png')
