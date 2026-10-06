"""Export the detailed model for review, without replacing the landing page's public assets."""
import bpy, json
from pathlib import Path
from collections import defaultdict
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1] if '__file__' in globals() else Path('/home/rishi/devmt/dhishna.org')
scene=bpy.data.scenes.get('Dhishna_Campus_Detailed')
if not scene:raise RuntimeError('Load assets/dhishna-campus-detailed.blend first.')
bpy.context.window.scene=scene
scene.frame_set(1)
scene.view_layers[0].update()
# glTF reads packed bytes, which can lag behind the image shown in Blender.
# Refresh the authoring PNGs before every export so both renderers use the same pixels.
for image in bpy.data.images:
    if not image.name.startswith(('V2_', 'V4_')):
        continue
    texture_path = Path(bpy.path.abspath(image.filepath))
    if not texture_path.is_file():
        continue
    if image.is_dirty:
        image.save()
    data = texture_path.read_bytes()
    image.pack(data=data, data_len=len(data))
source_objects=[o for o in scene.objects if not o.hide_render]
# UV projections for any last-added timber/stone parts.
for o in source_objects:
    if o.type!='MESH' or o.data.uv_layers:continue
    layer=o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        normal=(o.matrix_world.to_3x3() @ poly.normal).normalized()
        axis=max(range(3),key=lambda k:abs(normal[k]))
        for li in poly.loop_indices:
            p=o.matrix_world @ o.data.vertices[o.data.loops[li].vertex_index].co
            uv=(p.y,p.z) if axis==0 else (p.x,p.z) if axis==1 else (p.x,p.y)
            layer.data[li].uv=(uv[0]*.45,uv[1]*.45)
# Validate loop closure and anchored stems before saving.
animated=[o for o in source_objects if o.type=='MESH' and o.data.shape_keys]
root_error=0.0
max_tip_deformation=0.0
for o in animated:
    keys=o.data.shape_keys.key_blocks
    basis=keys[0]
    kind=o.get('wind_kind','')
    if kind=='flag':indices=[0,1]
    else:indices=[i for i in range(len(basis.data)) if i%5==0 or (kind=='grass' and i%5==1)]
    for key in list(keys)[1:]:
        for i in indices:root_error=max(root_error,(key.data[i].co-basis.data[i].co).length)
        for i in range(len(basis.data)):max_tip_deformation=max(max_tip_deformation,(key.data[i].co-basis.data[i].co).length)
assert root_error<1e-7,'Wind deformation moves plant roots or flag anchors'
scene.frame_set(1)
start={o.name:[key.value for key in o.data.shape_keys.key_blocks] for o in animated}
scene.frame_set(241)
end={o.name:[key.value for key in o.data.shape_keys.key_blocks] for o in animated}
loop_error=max(abs(a-b) for name,values in start.items() for a,b in zip(values,end[name]))
assert loop_error<1e-6,'Wind animation fails to close'
scene.frame_set(1)
deps=bpy.context.evaluated_depsgraph_get()
groups=defaultdict(lambda:{'verts':[],'faces':[],'uvs':[]})
runtime=bpy.data.collections.new('V2_RuntimeExport')
scene.collection.children.link(runtime)
batches=[]
try:
    for o in source_objects:
        if o.type not in {'MESH','FONT'} or o in animated:continue
        eval_obj=o.evaluated_get(deps)
        data=eval_obj.to_mesh()
        uv=data.uv_layers.active
        for poly in data.polygons:
            mat=data.materials[poly.material_index] if len(data.materials)>poly.material_index else None
            if not mat:continue
            category=o.users_collection[0].name
            group=groups[(category,mat.name)]
            index=len(group['verts'])
            for li in poly.loop_indices:
                vi=data.loops[li].vertex_index
                group['verts'].append(tuple(o.matrix_world @ data.vertices[vi].co))
                group['uvs'].append(tuple(uv.data[li].uv) if uv else (0,0))
            group['faces'].append(tuple(range(index,index+len(poly.vertices))))
        eval_obj.to_mesh_clear()
    for (category,matname),group in groups.items():
        d=bpy.data.meshes.new('DetailBatch_'+category+'_'+matname)
        d.from_pydata(group['verts'],[],group['faces']);d.update()
        d.materials.append(bpy.data.materials[matname])
        uv=d.uv_layers.new(name='UVMap')
        for poly in d.polygons:
            for li in poly.loop_indices:uv.data[li].uv=group['uvs'][d.loops[li].vertex_index]
        o=bpy.data.objects.new(d.name,d);runtime.objects.link(o);batches.append(o)
    for o in scene.objects:o.select_set(False)
    for o in batches+animated:o.select_set(True)
    bpy.context.view_layer.objects.active=batches[0]
    destination=ROOT/'assets/cusat-detailed.glb'
    bpy.ops.export_scene.gltf(
        filepath=str(destination),export_format='GLB',check_existing=False,
        use_selection=True,use_active_scene=True,export_cameras=False,export_lights=False,
        export_materials='EXPORT',export_texcoords=True,export_normals=True,export_extras=True,
        export_meshopt_compression_enable=True,export_meshopt_extension='EXT_meshopt_compression',
        export_animations=True,export_animation_mode='SCENE',export_frame_range=True,
        export_frame_step=5,export_force_sampling=True,export_anim_scene_split_object=False,
        export_morph=True,export_morph_normal=False,export_morph_tangent=False)
    stats={'version':3,'centralStatue':True,'separateStatueIsland':False,'continuousGrassChunks':sum(bool(o.get('continuous_groundcover')) for o in animated),'sourceObjects':len(scene.objects)-len(batches),'visibleObjects':len(source_objects),
           'runtimeMeshes':len(batches)+len(animated),
           'triangles':sum(len(p.vertices)-2 for o in batches+animated for p in o.data.polygons),
           'glbBytes':destination.stat().st_size,
           'animatedObjects':len(animated),'grassAndLeafPatches':sum(o.get('wind_kind')!='flag' for o in animated),
           'windLoopSeconds':8,'rootError':root_error,'loopError':loop_error,
           'maxRestTipDeformationMeters':max_tip_deformation,
           'compression':'EXT_meshopt_compression',
           'textures':[i.name for i in bpy.data.images if i.name.startswith(('V2_','V4_'))],
           'siteChanged':False,'facadeWeathering':bool(scene.get('facade_weathering_version')),'facadeTextureResolution':[2048,1024],'extraTrees':scene.get('extra_trees',0),'statueScale':scene.get('statue_enlarged',1),'referenceGateAdded':bool(scene.get('gateway_version'))}
    (ROOT/'assets/model-v2-info.json').write_text(json.dumps(stats,indent=2))
finally:
    for o in batches:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(data)
    bpy.data.collections.remove(runtime)
    for o in scene.objects:o.select_set(False)
    scene.camera.select_set(True);bpy.context.view_layer.objects.active=scene.camera
    scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus-detailed.blend'),check_existing=False)
result=stats
