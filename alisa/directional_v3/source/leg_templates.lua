-- Positional edit guides only. The final costume/limbs are drawn by imagegen.
local root=assert(app.params.root)
local out=root..'/alisa/directional_v3/source'
local pc=app.pixelColor
local f=assert(io.open(out..'/pose_plan.json','r'));local plan=json.decode(f:read('*a'));f:close()
local colors={pc.rgba(230,55,65,255),pc.rgba(35,120,235,255)}
local function capsule(im,a,b,width,color)
 local dx,dy=b[1]-a[1],b[2]-a[2];local length=dx*dx+dy*dy
 for y=58,85 do for x=0,35 do
  local t=math.max(0,math.min(1,((x-a[1])*dx+(y-a[2])*dy)/length))
  if (x-a[1]-t*dx)^2+(y-a[2]-t*dy)^2<=width^2 then im:drawPixel(x,y,color) end
 end end
end
for _,name in ipairs({'sw','nw'}) do
 local src=assert(app.open(out..'/Native_'..name..'.aseprite'))
 local upper=Image(36,86,ColorMode.RGB);upper:drawSprite(src,9)
 for y=58,85 do for x=0,35 do upper:drawPixel(x,y,0) end end
 local guide=Image(1254,1254,ColorMode.RGB)
 local yaw=(name=='sw' and 45 or 135)*math.pi/180
 for i,p in ipairs(plan[name]) do
  local im=Image(36,86,ColorMode.RGB)
  for j,leg in ipairs(p.legs) do
   capsule(im,leg[1],leg[2],3.1,colors[j])
   capsule(im,leg[2],leg[3],2.6,colors[j])
   local toe={leg[3][1]-math.sin(yaw)*2.2,leg[3][2]+math.cos(yaw)*2.2}
   capsule(im,leg[3],toe,2.5,colors[j])
  end
  im:drawImage(upper,Point(0,0));im:resize(144,344)
  guide:drawImage(im,Point((i-1)%3*418+137,math.floor((i-1)/3)*418+30))
 end
 guide:saveAs(out..'/'..name:upper()..'_walk_template.png');src:close()
end
