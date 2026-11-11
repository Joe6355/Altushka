local root=assert(app.params.root)
local out=root..'/alisa/confident_walk/source'
local source=assert(app.open(root..'/recolor/blue_eyes/Altushka_blue.aseprite'))
local board=Image(320,94,ColorMode.RGB)
local pc=app.pixelColor
for it in board:pixels() do it(pc.rgba(105,99,112,255)) end
for column,frame in ipairs({1,6,11,16,21,26,31,36}) do
  local image=Image(36,86,ColorMode.RGB);image:drawSprite(source,frame)
  if frame==6 then image:saveAs(out..'/Original_master.png') end
  board:drawImage(image,Point((column-1)*40+2,4))
end
board:resize(1920,564);board:saveAs(out..'/Original_motion_landmarks.png')
source:close()
