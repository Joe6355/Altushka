local root=assert(app.params.root)
local out=root..'/alisa/directional_v3/source'
local pc=app.pixelColor
local function blank(w,h) return Image(w,h,ColorMode.RGB) end
local front=assert(app.open(root..'/recolor/blue_eyes/Altushka_blue.aseprite'))
local side=assert(app.open(root..'/alisa/side_revision/Alisa_side_revision.aseprite'))
local board=blank(160,94)
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
for i,entry in ipairs({{front,6},{side,1},{side,6},{front,1}}) do
 local im=blank(36,86);im:drawSprite(entry[1],entry[2])
 board:drawImage(im,Point((i-1)*40+2,4))
end
board:resize(1280,752);board:saveAs(out..'/Identity_reference.png')
local upper=blank(36,86);upper:drawSprite(front,6)
local f=assert(io.open(out..'/pose_plan.json','r'));local plan=json.decode(f:read('*a'));f:close()
local colors={pc.rgba(230,55,65,255),pc.rgba(35,120,235,255)}
local function capsule(im,a,b,width,color)
 local dx,dy=b[1]-a[1],b[2]-a[2];local length=dx*dx+dy*dy
 for y=0,85 do for x=0,35 do
  local t=math.max(0,math.min(1,((x-a[1])*dx+(y-a[2])*dy)/length))
  if (x-a[1]-t*dx)^2+(y-a[2]-t*dy)^2<=width^2 then im:drawPixel(x,y,color) end
 end end
end
for name,frames in pairs(plan) do
 local guide=blank(1536,1536)
 local yaw=({s=0,n=180,sw=45,nw=135})[name]*math.pi/180
 for i,p in ipairs(frames) do
  local im=blank(36,86)
  for j,leg in ipairs(p.legs) do
   capsule(im,leg[1],leg[2],3.1,colors[j])
   capsule(im,leg[2],leg[3],2.6,colors[j])
   local toe={leg[3][1]-math.sin(yaw)*2.2,leg[3][2]+math.cos(yaw)*2.2}
   capsule(im,leg[3],toe,2.5,colors[j])
  end
  local grey=pc.rgba(115,115,120,255)
  -- Neutral front/back envelope, not the original three-quarter silhouette.
  for y=7,30 do for x=0,35 do
   if ((x-17.5)/14.5)^2+((y-18)/12)^2<=1 then im:drawPixel(x,y,grey) end
  end end
  for _,p in ipairs({{17,1},{18,1},{19,2},{19,3},{18,4},{18,5},{18,6},{18,7}}) do im:drawPixel(p[1],p[2],grey) end
  for y=30,57 do
   local half=y<33 and 4 or (y<43 and (11-(y-33)*.45) or (y<47 and 6 or (6+(y-47)*.7)))
   for x=math.ceil(17.5-half),math.floor(17.5+half) do im:drawPixel(x,y,grey) end
  end
  for _,arm in ipairs({{{10,33},{6,39},{11,45}},{{25,33},{29,39},{24,45}}}) do
   capsule(im,arm[1],arm[2],2,grey);capsule(im,arm[2],arm[3],2,grey)
  end
  im:resize(180,430)
  guide:drawImage(im,Point((i-1)%3*512+166,math.floor((i-1)/3)*512+40))
 end
 guide:saveAs(out..'/Guide_'..name..'.png')
end
front:close();side:close()
