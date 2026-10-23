import bpy, sys
src, out = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
for im in bpy.data.images:
    if im.size[0]:
        im.filepath_raw = f"{out}/{im.name}.png"; im.file_format = "PNG"; im.save()
