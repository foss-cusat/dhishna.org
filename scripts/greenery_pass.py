
import bpy, math, random, pathlib, json
from mathutils import Vector
ROOT=pathlib.Path('/home/rishi/devmt/dhishna.org')
scene=bpy.data.scenes['Dhishna_Campus_Detailed']
bpy.context.window.scene=scene
land=bpy.data.collections['V2_Landscape']
def hide(o):
    o.hide_render=True;o.hide_viewport=True;o['detail_hidden']=True
# Apply the latest reference layout once; retain the old scene for comparison.
if not scene.get('central_statue_layout'):
    for o in bpy.data.collections['V2_Kathakali'].objects:
        o.location.y+=12
    scene['central_statue_layout']=True
for name in ['V2_StatueIslandCurb','V2_StatueIslandGrass','V2_FlagPole','V2_FlagPoleBase','ContinuousMeadowUnderstorey']:
    o=scene.objects.get(name)
    if o:hide(o)
# Former statue island occupied the approach road; remove its generated hedge cores.
for o in scene.objects:
    if o.name.startswith('HedgeCore') and abs(o.location.x)<4.3 and -27<o.location.y<-19:
        hide(o)
# Remove old island leaves from the shared static leaf mesh while preserving the rest.
o=scene.objects.get('FoldedGroundLeaves')
if o and not o.get('island_removed'):
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data)
    delete=[]
    for v in bm.verts:
        p=o.matrix_world@v.co
        if abs(p.x)<4.3 and -27<p.y<-19:delete.append(v)
    bmesh.ops.delete(bm,geom=delete,context='VERTS')
    bm.to_mesh(o.data);bm.free();o['island_removed']=True
# The planted ground is continuous, interrupted only by campus circulation.
def zone(x,y):
    garden=(x/10.55)**2+((y+11)/6.93)**2
    if garden<1:
        if abs(x)<.73 or abs(y+11)<.65:return None
        if abs(x)<2.15 and abs(y+11)<1.8:return None
        return 'garden'
    if (x/15.85)**2+((y+11)/11.55)**2<1:return None
    if -29<x<29 and 1.15<y<20:return None
    if abs(x)<4.7 and y<-20:return None
    if 16.6<x<29 and -24.8<y<18:return None
    if abs(x)<9 and -35<y<-29:return None
    # Walk from the garden to the entrance.
    if abs(x)<8.4 and -3.8<y<1.5:return None
    return 'meadow'
# Single vertex-colour foliage material keeps a rich palette without many draw calls.
mat=bpy.data.materials.get('V3_LeafyMeadow') or bpy.data.materials.new('V3_LeafyMeadow')
mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear()
out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled')
col=nodes.new('ShaderNodeVertexColor');col.layer_name='FoliageColor'
mat.node_tree.links.new(col.outputs['Color'],bs.inputs['Base Color'])
mat.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
bs.inputs['Roughness'].default_value=.92
mat.diffuse_color=(.35,.48,.065,1)
palette=[(.25,.38,.035,1),(.37,.49,.07,1),(.46,.56,.105,1),(.32,.45,.06,1),(.52,.61,.15,1),(.40,.52,.085,1)]
for o in list(scene.objects):
    if o.name.startswith('LivingMeadow_'):bpy.data.objects.remove(o,do_unlink=True)
rng=random.Random(202701)
chunks={}
step=.38
nx=int(88/step);ny=int(76/step)
plants=0
for ix in range(nx):
    for iy in range(ny):
        x=-44+(ix+rng.uniform(.12,.88))*step
        y=-43+(iy+rng.uniform(.12,.88))*step
        z=zone(x,y)
        if z is None:continue
        # Small natural openings; the overall carpet remains dense.
        if rng.random()<(.16 if z=='meadow' else .12):continue
        cell=(int((x+44)//14),int((y+43)//14))
        d=chunks.setdefault(cell,{'v':[],'f':[],'c':[],'w':[]})
        plants+=1
        base=Vector((x,y,.375 if z=='garden' else .027))
        height=rng.uniform(.16,.35) if z=='garden' else rng.uniform(.37,.88)
        n=rng.randint(4,6) if z=='meadow' else rng.randint(3,5)
        phase=rng.random()*math.tau
        for j in range(n):
            a=phase+j*math.tau/n+rng.uniform(-.28,.28)
            axis=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
            h=height*rng.uniform(.75,1.18)
            width=rng.uniform(.075,.135) if z=='garden' else rng.uniform(.12,.22)
            lean=rng.uniform(.11,.25) if z=='garden' else rng.uniform(.27,.59)
            mid=base+axis*lean*.42+Vector((0,0,h*.58))
            tip=base+axis*lean+Vector((0,0,h))
            k=len(d['v'])
            d['v'].extend([tuple(base-side*width*.55),tuple(base+side*width*.55),
                          tuple(mid-side*width),tuple(mid+side*width),tuple(tip)])
            d['f'].extend([(k,k+1,k+3,k+2),(k+2,k+3,k+4)])
            d['w'].extend([0,0,.35,.35,1])
            color=palette[rng.randrange(len(palette))]
            for weight in [0,0,.55,.55,1]:
                d['c'].append(tuple(min(1,c*(.82+.21*weight)) for c in color[:3])+(1,))
animated=[]
for index,(cell,d) in enumerate(sorted(chunks.items())):
    if not d['v']:continue
    me=bpy.data.meshes.new('LivingMeadowMesh');me.from_pydata(d['v'],[],d['f']);me.update()
    me.materials.append(mat)
    color=me.color_attributes.new(name='FoliageColor',type='FLOAT_COLOR',domain='POINT')
    for i,c in enumerate(d['c']):color.data[i].color=c
    o=bpy.data.objects.new('LivingMeadow_'+str(index),me);land.objects.link(o)
    o['wind_kind']='grass';o['wind_roots_fixed']=True;o['continuous_groundcover']=True
    o.shape_key_add(name='Basis');key=o.shape_key_add(name='SlowBreeze')
    for i,w in enumerate(d['w']):
        # Tips move a few centimetres; bases never translate.
        p=Vector(d['v'][i]);local=math.sin(p.x*.15+p.y*.11)
        key.data[i].co=p+Vector((.075*w,.04*w*(.8+.2*local),-.012*w))
    phase=cell[0]*.37+cell[1]*.58
    for frame in range(1,242,10):
        key.value=.5+.5*math.sin((frame-1)/240*math.tau+phase)
        key.keyframe_insert('value',frame=frame)
    key.value=.5+.5*math.sin(phase);key.keyframe_insert('value',frame=241)
    o.data.shape_keys.animation_data.action.name='SlowGroundcoverBreeze_'+str(index)
    animated.append(o)
# Fuller, overlapping palm leaflets match the reference's feathered crowns.
if not scene.get('palm_leaflets_broadened'):
    for o in scene.objects:
        if not o.name.startswith('FeatheredPalm') or o.type!='MESH':continue
        # Every folded leaflet uses four successive vertices.
        for i in range(0,len(o.data.vertices)-3,4):
            vs=[o.data.vertices[i+j] for j in range(4)]
            near=(vs[0].co+vs[3].co)*.5
            for j in (0,3):vs[j].co=near+(vs[j].co-near)*1.6
            far=(vs[1].co+vs[2].co)*.5
            for j in (1,2):vs[j].co=far+(vs[j].co-far)*1.6
        o.data.update()
    scene['palm_leaflets_broadened']=True
scene.frame_set(1)
scene['groundcover_version']=3
scene['wind_description']='Continuous rooted leafy grass across planted ground and roundabout garden, gently phased 8 second breeze.'
scene.camera=scene.objects['V2_DhishnaCamera']
scene.render.resolution_x=1400;scene.render.resolution_y=875;scene.render.resolution_percentage=100
scene.cycles.samples=24
scene.render.filepath=str(ROOT/'artifacts/model-v2/campus-wide.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus-detailed.blend'),check_existing=False)
result={'plants':plants,'continuousWindChunks':len(animated),'statueCenter':[0,-11],'separateIslandRemoved':True,
        'triangles':sum(len(p.vertices)-2 for o in scene.objects if o.type=='MESH' and not o.hide_render for p in o.data.polygons)}
