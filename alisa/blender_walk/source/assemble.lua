local out = assert(app.params.out)
local render = assert(app.params.render)
local count = assert(tonumber(app.params.frames))
local name = app.params.name or "Alisa_walk"
local sprite = Sprite(36, 86, ColorMode.RGB)
local layer = sprite.layers[1]
layer.name = "Алиса"

local clips = {}
if app.params.clips then
  local index = 1
  for label, length, duration in app.params.clips:gmatch("([%w_]+):(%d+):(%d+)") do
    local finish = index + tonumber(length) - 1
    clips[#clips+1] = {name=label, first=index, last=finish, duration=tonumber(duration)}
    index = finish + 1
  end
  assert(index == count + 1, "Clip sizes do not match the number of cels")
else
  clips[1] = {name="walk_se", first=1, last=count}
end

local clip_index = 1
for i = 1, count do
  if i > 1 then sprite:newEmptyFrame(i) end
  if i > clips[clip_index].last then clip_index = clip_index + 1 end
  local first = math.floor((i - 1) * 1000 / count + .5)
  local last = math.floor(i * 1000 / count + .5)
  sprite.frames[i].duration = (clips[clip_index].duration or last - first) / 1000
  local cel = Image{fromFile=string.format("%s/pixel_%02d.png", render, i - 1)}
  assert(cel.width == 36 and cel.height == 86)
  sprite:newCel(layer, i, cel, Point(0, 0))
end

for _, clip in ipairs(clips) do
  local tag = sprite:newTag(clip.first, clip.last)
  tag.name = clip.name
  tag.aniDir = AniDir.FORWARD
end
sprite:saveAs(out .. "/" .. name .. ".aseprite")
app.command.ExportSpriteSheet{
  ui=false, askOverwrite=false, type=SpriteSheetType.ROWS, columns=tonumber(app.params.columns) or count,
  textureFilename=out .. "/" .. name .. "_atlas.png",
  dataFilename=out .. "/" .. name .. ".json", dataFormat=SpriteSheetDataFormat.JSON_ARRAY,
  listTags=true, trimSprite=false, trim=false, extrude=false,
}
sprite:close()
