local root=assert(app.params.root)
local out=root..'/alisa/directional_v3/source'
local pc=app.pixelColor
local board=Image(160,94,ColorMode.RGB)
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
for j,name in ipairs({'s','n','sw','nw'}) do
 local sprite=assert(app.open(out..'/Native_'..name..'.aseprite'))
 local im=Image(36,86,ColorMode.RGB);im:drawSprite(sprite,9)
 im:saveAs(out..'/Master_'..name..'.png')
 board:drawImage(im,Point((j-1)*40+2,4));sprite:close()
end
board:resize(1280,752);board:saveAs(out..'/Master_review.png')
