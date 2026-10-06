"""Model-only detail pass for Dhishna. Run with the original assets/dhishna-campus.blend loaded.
Creates a separate scene and writes only assets/ and artifacts/model-v2/. The landing site is untouched.
"""
import bpy, math, random, json, numpy as np
from pathlib import Path
from mathutils import Vector
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1] if '__file__' in globals() else Path('/home/rishi/devmt/dhishna.org')
OUT=ROOT/'artifacts/model-v2'
TEXTURES=ROOT/'assets/textures'
OUT.mkdir(parents=True,exist_ok=True)
TEXTURES.mkdir(parents=True,exist_ok=True)
rng=random.Random(271006)
original=bpy.data.scenes.get('Dhishna_Campus')
if original is None: raise RuntimeError('Load assets/dhishna-campus.blend first.')
scene=bpy.data.scenes.new('Dhishna_Campus_Detailed')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene.render.engine='CYCLES'
scene.cycles.samples=40
scene.cycles.use_denoising=True
scene.render.resolution_x=1800
scene.render.resolution_y=1125
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=.25
scene.render.film_transparent=False
scene.render.fps=30
scene.frame_start=1
scene.frame_end=241
scene.world=original.world.copy()
scene.world.name='V2_WarmDaylight'
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.68,.78,.62,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.75

collections={}
materials={}
objects={}
for old in original.collection.children:
    name=old.name.replace('Dhishna_','')
    collection=bpy.data.collections.new('V2_'+name)
    scene.collection.children.link(collection)
    collections[name]=collection
    for source in old.objects:
        obj=source.copy()
        obj.name='V2_'+source.name
        if source.data:obj.data=source.data.copy()
        collection.objects.link(obj)
        objects[source.name]=obj
        if obj.type in {'MESH','FONT'}:
            for i,mat in enumerate(list(obj.data.materials)):
                if not mat:continue
                if mat.name not in materials:
                    copy=mat.copy();copy.name='V2_'+mat.name
                    materials[mat.name]=copy
                obj.data.materials[i]=materials[mat.name]
scene.camera=objects[original.camera.name]
scene.camera.data.ortho_scale=73
scene.camera.location=(34,-62,43)
scene.camera.rotation_euler=(Vector((0,-4,4))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
objects['DhishnaSun'].data.energy=3.2
objects['DhishnaSun'].data.angle=.10
objects['DhishnaSun'].rotation_euler=(math.radians(27),math.radians(-23),math.radians(-32))
objects['DhishnaSoftbox'].data.energy=1100
category='Architecture'
primitives={}
def hide(obj):
    obj.hide_render=True;obj.hide_viewport=True;obj['detail_hidden']=True
def mesh(name,verts,faces,mats,indices=None,uvs=None):
    d=bpy.data.meshes.new(name+'Mesh')
    d.from_pydata(verts,[],faces);d.update()
    for mat in mats:d.materials.append(mat)
    if indices:
        for p,i in zip(d.polygons,indices):p.material_index=i
    if uvs:
        layer=d.uv_layers.new(name='UVMap')
        for p in d.polygons:
            for li in p.loop_indices:layer.data[li].uv=uvs[d.loops[li].vertex_index]
    o=bpy.data.objects.new(name,d);collections[category].objects.link(o)
    return o
def box(name,loc,size,mat,rotation=(0,0,0)):
    key=('cube',mat.name)
    if key not in primitives:
        verts=[(x*.5,y*.5,z*.5) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        faces=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
        o=mesh(name,verts,faces,[mat]);primitives[key]=o.data
    else:
        o=bpy.data.objects.new(name,primitives[key]);collections[category].objects.link(o)
    o.location=loc;o.scale=size;o.rotation_euler=rotation;return o
def rod(name,a,b,r,mat,n=8):
    a,b=Vector(a),Vector(b);delta=b-a
    key=('rod',mat.name,n)
    if key not in primitives:
        verts=[(r0*math.cos(i*2*math.pi/n),r0*math.sin(i*2*math.pi/n),z) for r0,z in [(1,-.5),(1,.5)] for i in range(n)]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        o=mesh(name,verts,faces,[mat]);primitives[key]=o.data
    else:
        o=bpy.data.objects.new(name,primitives[key]);collections[category].objects.link(o)
    o.location=(a+b)*.5;o.scale=(r,r,delta.length)
    o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();return o
def ico(name,loc,scale,mat,sub=1):
    key=('ico',sub,mat.name)
    if key not in primitives:
        import bmesh
        d=bpy.data.meshes.new('V2Ico_'+str(len(primitives)));bm=bmesh.new()
        bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1)
        bm.to_mesh(d);bm.free();d.materials.append(mat);primitives[key]=d
    o=bpy.data.objects.new(name,primitives[key]);collections[category].objects.link(o)
    o.location=loc;o.scale=scale;o.rotation_euler=(rng.random()*.7,rng.random()*.7,rng.random()*6.28)
    return o
def srgb_to_linear(v):
    return v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4
def linear_to_srgb(v):
    return 12.92*v if v<.0031308 else 1.055*v**(1/2.4)-.055
def new_mat(name,color):
    m=bpy.data.materials.new('V2_'+name);m.use_nodes=True
    rgb=[srgb_to_linear(int(color[i:i+2],16)/255) for i in (0,2,4)]
    m.diffuse_color=(*rgb,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=.87
    return m
M={k.removeprefix('D_'):v for k,v in materials.items()}
M['weather']=new_mat('WaterStaining','9b9476')
M['moss']=new_mat('Moss','657347')
M['edge']=new_mat('OldMortar','b5b292')
M['terracotta']=new_mat('Terracotta','a75b3a')
M['metal']=new_mat('AgedMetal','496559')
M['pebble']=new_mat('Pebble','aa9c7a')
M['mulch']=new_mat('Mulch','6b6842')
M['leafdark']=new_mat('DeepLeaf','2c6438')
M['leafmid']=new_mat('EmeraldLeaf','4a8d3d')
M['leaflight']=new_mat('YoungLeaf','a5be55')
M['leafgold']=new_mat('DryGrass','b5b76a')
M['flowerpink']=new_mat('PinkPetal','e197a1')
M['flowerblue']=new_mat('BluePetal','819db5')
ROOF=[M['Roof'+str(i)] for i in range(6)]
LEAF=[M['Leaf'+str(i)] for i in range(8)]
# Deeper, less pastel vegetation while retaining low-poly facet shading.
leaf_palette=['2f713d','4e883b','669b43','7ca84b','93b34f','28663b','477c35','a5b95b']
for mat,color in zip(LEAF,leaf_palette):
    rgb=[srgb_to_linear(int(color[i:i+2],16)/255) for i in (0,2,4)]
    mat.diffuse_color=(*rgb,1);mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*rgb,1)

# Actual UV image textures: colored plaster, clay, timber, bark, and grit.
# They are packed into the blend and embedded into the later GLB, not Blender-only procedural nodes.
np_rng=np.random.default_rng(271006)
N=512
yy,xx=np.mgrid[0:N,0:N].astype(np.float32)/N
noise=np_rng.random((N,N)).astype(np.float32)
coarse=(np.sin(xx*18+np.cos(yy*11))+np.sin(yy*24+xx*7)+np.sin(xx*37-yy*21))*.026
plaster=np.clip(.985+coarse*.20+(noise-.5)*.018, .95,1.0)
clay=np.clip(.975+.009*np.sin(xx*85+np.sin(yy*8)*3)+(noise-.5)*.05+coarse*.15,.92,1)
timber=np.clip(.97+.025*np.sin(xx*150+np.sin(yy*8)*5)+.018*np.sin(xx*43)+(noise-.5)*.03,.89,1)
grit=np.clip(.985+coarse*.18+(noise-.5)*.032,.94,1)
patterns={'plaster':plaster,'clay':clay,'timber':timber,'grit':grit}
def image_png(name,rgb,noncolor=False):
    rgba=np.concatenate([rgb,np.ones((N,N,1),dtype=np.float32)],axis=2).astype(np.float32)
    image=bpy.data.images.new(name,width=N,height=N,alpha=True)
    image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
    image.pixels.foreach_set(rgba.reshape(-1))
    image.file_format='PNG';image.filepath_raw=str(TEXTURES/(name+'.png'))
    image.save();image.pack();return image
texture_records=[]
normal_images={}
for typ,pattern in patterns.items():
    dy,dx=np.gradient(pattern)
    strength=1.8 if typ=='timber' else .7
    nx=-dx*strength;ny=-dy*strength
    nz=np.ones_like(nx)
    length=np.sqrt(nx*nx+ny*ny+nz*nz)
    rgb=np.stack((nx/length*.5+.5,ny/length*.5+.5,nz/length*.5+.5),axis=2)
    normal_images[typ]=image_png('V2_'+typ+'_normal',rgb,True)
for key in ['cream','white','pink','pinklight','wood','bark','earth','grass','road','path','curb']+['Roof'+str(i) for i in range(6)]:
    mat=M[key]
    typ='clay' if key.startswith('Roof') else 'timber' if key in ['wood','bark'] else 'grit' if key in ['earth','grass','road','path','curb'] else 'plaster'
    rgb=mat.diffuse_color[:3]
    # Image pixel values are linear; PNG saving applies sRGB encoding for color textures.
    pixels=np.stack([patterns[typ]*linear_to_srgb(v) for v in rgb],axis=2)
    img=image_png('V2_'+key+'_color',pixels)
    nt=mat.node_tree;p=nt.nodes.get('Principled BSDF')
    tex=nt.nodes.new('ShaderNodeTexImage');tex.name='SurfaceColor';tex.image=img
    nt.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    normtex=nt.nodes.new('ShaderNodeTexImage');normtex.image=normal_images[typ]
    norm=nt.nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.35 if typ!='timber' else .6
    nt.links.new(normtex.outputs['Color'],norm.inputs['Color']);nt.links.new(norm.outputs['Normal'],p.inputs['Normal'])
    p.inputs['Roughness'].default_value=.90 if typ=='grit' else .84
    texture_records.append({'material':mat.name,'type':typ,'image':img.name})

# Give all copied textured meshes a world-scale box projection.
def projected_uv(o,scale=1.0):
    if o.type!='MESH' or o.get('detail_hidden'):return
    d=o.data
    if d.uv_layers:return
    layer=d.uv_layers.new(name='UVMap')
    for poly in d.polygons:
        normal=(o.matrix_world.to_3x3() @ poly.normal).normalized()
        axis=max(range(3),key=lambda k:abs(normal[k]))
        for li in poly.loop_indices:
            v=o.matrix_world @ d.vertices[d.loops[li].vertex_index].co
            uv=(v.y,v.z) if axis==0 else (v.x,v.z) if axis==1 else (v.x,v.y)
            layer.data[li].uv=(uv[0]*scale,uv[1]*scale)
scene.view_layers[0].update()
for o in list(scene.objects):projected_uv(o,.32 if o.type=='MESH' else 1)

# Hide the flat checker tiles in this new scene and replace them with raised, overlapping clay tiles.
for name,o in objects.items():
    if '_Tiles' in name or '_Ridge' in name:hide(o)
roof_specs=[('TowerWest',-10.7,6.4,7.6,8.3,17.7,2.9),('TowerEast',10.7,6.4,7.6,8.3,17.7,2.9),
 ('Central',0,7.3,16.6,10,12.7,2.35),('WingWest',-20.3,9,14.5,10.2,10.3,2.0),
 ('WingEast',20.3,9,14.5,10.2,10.3,2.0),('Verandah',0,.85,16.3,5.6,4.85,1.65),
 ('Balcony',0,1,16.2,4.2,9,1.55)]
roof_specs += [('Stall'+str(i),23,y,5.2,4.4,3.5,.95) for i,y in enumerate([-13,-5,3])]
tile_count=0
category='Architecture'
for name,cx,cy,w,d,z,rise in roof_specs:
    category='Festival' if name.startswith('Stall') else 'Architecture'
    ridge=max(w*.5-d*.38,.2)
    vertices=[];faces=[];uvs=[];indices=[]
    surfaces=[
      ((cx,cy-d/2,z),(1,0,0),(0,d/2,rise),w/2,ridge),
      ((cx,cy+d/2,z),(1,0,0),(0,-d/2,rise),w/2,ridge),
      ((cx-w/2,cy,z),(0,1,0),(w/2-ridge,0,rise),d/2,0),
      ((cx+w/2,cy,z),(0,1,0),(-w/2+ridge,0,rise),d/2,0)]
    for origin,axis,direction,half_bottom,half_top in surfaces:
        origin=Vector(origin);U=Vector(axis);D=Vector(direction);Nrm=U.cross(D).normalized()
        if Nrm.z<0:Nrm=-Nrm
        rows=max(2,math.ceil(D.length/.60));tilewidth=.40
        for row in range(rows):
            t0=row/rows
            t1=min(1,(row+1)/rows+.11/D.length)
            hw0=half_bottom+(half_top-half_bottom)*t0
            hw1=half_bottom+(half_top-half_bottom)*t1
            lo=-math.ceil(hw0/tilewidth)
            hi=math.ceil(hw0/tilewidth)
            for col in range(lo,hi):
                x0=col*tilewidth+.003
                x1=(col+1)*tilewidth-.003
                if x1<-hw1 or x0>hw1:
                    # Edge tile is tapered to the hipped boundary, rather than extending beyond it.
                    if x1<-hw0 or x0>hw0:continue
                matindex=rng.choices(range(6),weights=[3,5,5,2,2,4])[0]
                offset=.012+row*.002
                start=len(vertices)
                for t,hw,v in [(t0,hw0,0),(t1,hw1,1)]:
                    for j in range(7):
                        u=j/6
                        x=max(-hw,min(hw,x0+(x1-x0)*u))
                        profile=.047*math.sin(math.pi*u)**.85+.012*math.sin(math.pi*u*3)**2
                        p=origin+U*x+D*t+Nrm*(offset+profile)
                        vertices.append(tuple(p));uvs.append((u,v))
                reverse=U.cross(D).dot(Nrm)<0
                for j in range(6):
                    f=(start+j,start+j+1,start+j+8,start+j+7)
                    faces.append(tuple(reversed(f)) if reverse else f);indices.append(matindex)
                # Thin front lip makes the overlapping rows cast an actual shadow.
                lipstart=len(vertices)
                for j in range(7):
                    p=Vector(vertices[start+j])-Nrm*.028
                    vertices.append(tuple(p));uvs.append((j/6,.04))
                for j in range(6):
                    faces.append((start+j+1,start+j,lipstart+j,lipstart+j+1));indices.append(max(0,matindex-1))
                tile_count+=1
    o=mesh('RaisedClayTiles_'+name,vertices,faces,ROOF,indices,uvs)
    o['tileCountApprox']=tile_count
    def cap_chain(a,b,label):
        a,b=Vector(a),Vector(b);length=(b-a).length;n=max(1,math.ceil(length/.6))
        for i in range(n):
            p=a.lerp(b,i/n);q=a.lerp(b,min(1,(i+1)/n+.02))
            rod(label,p,q,.115,ROOF[(i+2)%6],10)
    cap_chain((cx-ridge,cy,z+rise+.15),(cx+ridge,cy,z+rise+.15),'RidgeCap_'+name)
    for side in (-1,1):
        for sy in (-1,1):
            cap_chain((cx+side*w/2,cy+sy*d/2,z+.08),(cx+side*ridge,cy,z+rise+.15),'HipCap_'+name)
    # Rafters project below eaves, giving the roof a constructed underside.
    for dx in np.arange(-w/2+.4,w/2,.85):
        box('EaveRafter_'+name,(cx+float(dx),cy-d/2+.15,z-.17),(.11,.8,.12),M['wood'])
    if not name.startswith('Stall'):
        rod('RainGutter_'+name,(cx-w/2,cy-d/2-.08,z-.16),(cx+w/2,cy-d/2-.08,z-.16),.06,M['metal'])
        for side in (-1,1):
            x=cx+side*(w/2-.20)
            if name.startswith('Tower'):
                rod('RainDownpipe_'+name,(x,cy-d/2+.28,.30),(x,cy-d/2+.28,z-.3),.045,M['metal'])

# Facade details: small relief, edge bands, ornate gables, worn plinth, window recesses.
category='Architecture'
for x in (-10.7,10.7):
    for side in (-1,1):
        box('TowerCornerTrim',(x+side*2.82,2.89,8.8),(.15,.16,17.35),M['white'])
    for z in (1.4,6.6,11.8):
        for dx in (-.93,.93):
            for h in (0,1.15,2.35):
                box('TowerWindowLowerDetail',(x+dx,2.58,z+h+.05),(1.25,.055,.06),M['cream'])
    # Scalloped white gable carving underneath the slope.
    for sign in (-1,1):
        a=Vector((x,1.94,20.38));b=Vector((x+sign*2.9,1.94,17.85))
        for i in range(14):
            p=a.lerp(b,(i+.5)/14)
            ico('GableCarvedRosette',p,(.12,.045,.12),M['white'],1)
    for dx in (-.9,-.3,.3,.9):
        rod('GableFretwork',(x+dx,1.96,18.15),(x+dx,1.96,19.55-abs(dx)*.65),.035,M['white'],6)
    # The visible outer wall receives recessed side windows and horizontal trim.
    side=-1 if x<0 else 1
    for z in (2.2,7.4,12.6):
        box('TowerSideWindow',(x+side*2.92,6.8,z+1.3),(.07,1.50,2.7),M['dark'])
        for yy in (6.02,6.8,7.58):
            box('TowerSideMullion',(x+side*2.98,yy,z+1.3),(.09,.06,2.8),M['cream'])
    box('TowerCornice',(x,2.7,17.3),(5.85,.38,.24),M['cream'])
    # Subtle damp and flaked patches at the footing: small irregular forms, not uniform noise.
    for i in range(13):
        px=x+rng.uniform(-2.6,2.6)
        box('PlinthWear',(px,2.91,.28+rng.uniform(.0,.6)),(rng.uniform(.08,.36),.022,rng.uniform(.08,.30)),M['weather'])
for x in (-7.2,-2.4,2.4,7.2):
    for z in (1,2.5,4):
        box('PillarJoint',(x,-.07,z),(.44,.055,.025),M['edge'])
# Actual door panels, handles, and entrance beams visible below the verandah.
for x in (-4.8,0,4.8):
    box('DoorPanels',(x,1.74,1.75),(2.55,.16,3.25),M['wood'])
    for side in (-1,1):
        for z in (.85,2.2):
            box('DoorInset',(x+side*.6,1.635,z),(1.0,.08,1.05),M['dark'])
        rod('DoorBrassHandle',(x+side*.16,1.52,1.42),(x+side*.16,1.52,1.83),.025,M['gold'])
    box('DoorThreshold',(x,1.2,.30),(2.9,1.2,.16),M['curb'])
for x in np.arange(-7,7.1,.8):
    box('VerandahCeilingSlat',(float(x),.75,4.56),(.09,4,.07),M['wood'])

# Natural landscape. Replace the repeating spherical garden bushes with irregular leafy hedges.
category='Landscape'
for name,o in objects.items():
    if name.startswith(('GardenHedge','StatueHedge','WildShrub','FernBedShrub','MeadowGrass','FernBeds','Breeze_','PalmFrond')):
        hide(o)
# Shrink some of the very large canopy balls into irregular overlapping clusters.
for name,o in objects.items():
    if name.startswith('TreeCanopy'):
        o.scale*=.88
        for i in range(2):
            offset=Vector((rng.uniform(-1.5,1.5),rng.uniform(-1.1,1.1),rng.uniform(-.6,.8)))
            ico('CanopyDetail',o.location+offset,tuple(v*rng.uniform(.28,.40) for v in o.scale),LEAF[rng.choice([0,1,2,5,6])],1)

# Palm leaves are feathered fronds with individually folded leaflets, not solid triangle umbrellas.
for x,y,h in [(-21,-18,12),(30,-17,13),(-35,8,16),(27,26,16),(40,5,14)]:
    for j in range(9):
        a=j*2*math.pi/9+.2;axis=Vector((math.cos(a),math.sin(a),0))
        side=Vector((-math.sin(a),math.cos(a),0))
        base=Vector((x+.4,y,h))
        verts=[];faces=[];mi=[]
        for i in range(25):
            t=(i+.5)/25
            p=base+axis*(4.7*t)+Vector((0,0,.70*math.sin(math.pi*t)-1.6*t*t))
            width=1.08*math.sin(math.pi*t)**.65+.06
            for sign in (-1,1):
                end=p+side*sign*width-axis*.30+Vector((0,0,-.15))
                v=[tuple(p-axis*.14),tuple(end-axis*.10),tuple(end),tuple(p+axis*.14+Vector((0,0,.065)))]
                k=len(verts);verts+=v;faces.extend([(k,k+1,k+3),(k+1,k+2,k+3)])
                mi.extend([j%8,(j+2)%8])
        o=mesh('FeatheredPalm',verts,faces,LEAF,mi)
        rod('PalmMidrib',base,base+axis*4.7+Vector((0,0,-1.6)),.026,M['leafdark'],6)

# Dense pockets of leaves, broad-leaf plants, folded grass, small flowers, pebbles, and moss.
plant_mat=[M['leafdark'],LEAF[0],LEAF[1],LEAF[2],LEAF[3],LEAF[4],LEAF[7],M['leafgold']]
plant_verts=[];plant_faces=[];plant_indices=[]
def leaf_shape(center,axis,length,width,matid):
    center=Vector(center);axis=Vector(axis).normalized()
    side=axis.cross(Vector((0,0,1)))
    if side.length<.01:side=Vector((1,0,0))
    side.normalize()
    mid=center+axis*length*.46+Vector((0,0,length*.10))
    tip=center+axis*length
    verts=[tuple(center),tuple(mid-side*width*.5),tuple(mid+Vector((0,0,width*.12))),tuple(mid+side*width*.5),tuple(tip)]
    k=len(plant_verts);plant_verts.extend(verts)
    plant_faces.extend([(k,k+1,k+2),(k,k+2,k+3),(k+1,k+4,k+2),(k+2,k+4,k+3)])
    plant_indices.extend([matid,(matid+1)%len(plant_mat),matid,(matid+1)%len(plant_mat)])
# Manicured hedge clusters, with slight species/size variation.
for name,o in objects.items():
    if name.startswith(('GardenHedge','StatueHedge','PotShrub')):
        p=o.location;size=sum(o.scale)/3
        for j in range(3):
            center=p+Vector((rng.uniform(-.27,.27),rng.uniform(-.27,.27),rng.uniform(-.16,.22)))
            ico('HedgeCore',center,(size*.64,size*.54,size*.70),LEAF[rng.choice([0,1,2])],1)
        for j in range(24):
            a=rng.random()*6.28;r=rng.uniform(.1,size*.65)
            center=Vector((p.x+math.cos(a)*r,p.y+math.sin(a)*r,p.z+rng.uniform(-.25,.4)*size))
            leaf_shape(center,(math.cos(a)*.65,math.sin(a)*.65,rng.uniform(.25,.8)),rng.uniform(.22,.48),.15,rng.choice([1,2,3,4]))
# Clustering on forest margins gives open paths and dense, varied green beds.
def planted(x,y):
    if (-28.8<x<28.8 and 1.3<y<19.5):return False
    if ((x/15.8)**2+((y+11)/11.5)**2)<1:return False
    if abs(x)<4.6 and -42<y<-20:return False
    if ((x/4.7)**2+((y+23)/3.9)**2)<1:return False
    if (16.8<x<28.8 and -24.5<y<18):return False
    if abs(x)<9 and -35<y<-29:return False
    return True
patch_centers=[(-22,-10),(-25,-25),(-17,-25),(-30,0),(-31,15),(32,4),(32,-19),(17,-29),(28,-30),(-8,-33),(-22,-34),(4,22)]
# Each wind patch will be a separate object with rooted morph deformation.
wind_objects=[]
for patch_index,(px,py) in enumerate(patch_centers):
    v=[];f=[];mi=[];weights=[]
    for i in range(170):
        x=px+rng.gauss(0,2.0);y=py+rng.gauss(0,2.0)
        if not planted(x,y):continue
        base=Vector((x,y,.035))
        height=rng.uniform(.38,1.10)
        for j in range(rng.randint(4,7)):
            a=rng.random()*6.28;axis=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
            lean=rng.uniform(.15,.42);width=rng.uniform(.035,.10)
            p0=base-side*width;p1=base+side*width
            mid=base+axis*lean*.4+Vector((0,0,height*.50))
            tip=base+axis*lean+Vector((0,0,height))
            k=len(v);v.extend([tuple(p0),tuple(p1),tuple(mid-side*width*.6),tuple(mid+side*width*.6),tuple(tip)])
            f.extend([(k,k+1,k+3,k+2),(k+2,k+3,k+4)])
            mi.extend([rng.choice([2,3,4,5,6,7]),rng.choice([3,4,5,6])])
            weights.extend([0,0,.28,.28,1.0])
    if not v:continue
    o=mesh('WindGrass_'+str(patch_index),v,f,plant_mat,mi)
    o['wind_roots_fixed']=True;o['wind_kind']='grass';o['wind_phase']=patch_index*.57
    o.shape_key_add(name='Basis')
    positive=o.shape_key_add(name='Gust')
    negative=o.shape_key_add(name='Return')
    for i,w in enumerate(weights):
        p=Vector(v[i]);motion=Vector((.085*w,.045*w,-.008*w))
        positive.data[i].co=p+motion;negative.data[i].co=p-motion*.65
    for key,phase in [(positive,patch_index*.57),(negative,patch_index*.57+math.pi)]:
        for frame in range(1,242,10):
            t=(frame-1)/240*math.pi*4
            key.value=max(0,math.sin(t+phase))*.78
            key.keyframe_insert('value',frame=frame)
        # Loop closure is explicit.
        key.value=max(0,math.sin(phase))*.78
        key.keyframe_insert('value',frame=241)
    o.data.shape_keys.animation_data.action.name='CampusBreeze_'+str(patch_index)
    wind_objects.append(o)
# Broad-leaf plant clusters and asymmetric shrub cores.
for px,py in patch_centers:
    for i in range(22):
        x=px+rng.gauss(0,2);y=py+rng.gauss(0,2)
        if not planted(x,y):continue
        h=rng.uniform(.35,.90)
        for j in range(6):
            a=j*math.pi/3+rng.random()*.3
            leaf_shape((x,y,.12),(math.cos(a)*.70,math.sin(a)*.70,.40),h,.22,rng.choice([1,2,3,4,5]))
    for i in range(8):
        x=px+rng.gauss(0,2);y=py+rng.gauss(0,2)
        if not planted(x,y):continue
        s=rng.uniform(.4,.95)
        for j in range(3):
            ico('NaturalShrub',(x+rng.uniform(-.28,.28),y+rng.uniform(-.24,.24),s*.6),(s*.68,s*.52,s*.72),LEAF[rng.choice([0,1,2,5])],1)
        for j in range(15):
            a=rng.random()*6.28
            leaf_shape((x+math.cos(a)*s*.4,y+math.sin(a)*s*.4,s*.8),(math.cos(a)*.6,math.sin(a)*.6,.5),.30,.15,rng.choice([2,3,4,5]))
# Fine ground cover throughout non-cleared margins.
for i in range(2300):
    x=rng.uniform(-45,45);y=rng.uniform(-42,32)
    if not planted(x,y):continue
    h=rng.uniform(.14,.40)
    for j in range(3):
        a=rng.random()*6.28
        leaf_shape((x,y,.02),(math.cos(a)*.5,math.sin(a)*.5,.8),h,h*.30,rng.choice([2,3,4,5,6,7]))
mesh('FoldedGroundLeaves',plant_verts,plant_faces,plant_mat,plant_indices)
# Small flowers and scattered stones kept near edges rather than evenly spread.
for px,py in patch_centers[:9]:
    for i in range(7):
        x=px+rng.gauss(0,1.5);y=py+rng.gauss(0,1.5)
        if not planted(x,y):continue
        h=rng.uniform(.35,.7)
        rod('FlowerStem',(x,y,.04),(x,y,h),.015,M['leafdark'],5)
        for j in range(4):
            a=j*math.pi/2
            ico('FlowerPetal',(x+.06*math.cos(a),y+.06*math.sin(a),h),(.07,.06,.035),M['flowerpink'] if i%3 else M['flowerblue'],1)
        ico('FlowerCenter',(x,y,h+.03),(.035,.035,.025),M['gold'],1)
for i in range(140):
    x=rng.uniform(-30,33);y=rng.uniform(-34,5)
    if not planted(x,y):continue
    s=rng.uniform(.08,.25)
    ico('PathPebble',(x,y,.04),(s,s*.8,s*.5),M['pebble'],1)


# A continuous low understorey bridges the larger planting pockets.
# Cleared road, garden, entrance, and festival paths remain readable.
category='Landscape'
carpet_rng=random.Random(271007)
carpet_v=[];carpet_f=[];carpet_m=[]
for i in range(8800):
    x=carpet_rng.uniform(-43,43);y=carpet_rng.uniform(-42,31)
    if not planted(x,y):continue
    base=Vector((x,y,.025))
    for j in range(carpet_rng.randint(3,5)):
        h=carpet_rng.uniform(.23,.72);a=carpet_rng.random()*6.28
        axis=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
        width=carpet_rng.uniform(.063,.135);lean=carpet_rng.uniform(.12,.4)
        mid=base+axis*lean*.40+Vector((0,0,h*.50));tip=base+axis*lean+Vector((0,0,h))
        k=len(carpet_v)
        carpet_v.extend([tuple(base-side*width),tuple(base+side*width),tuple(mid-side*width*.62),tuple(mid+side*width*.62),tuple(tip)])
        carpet_f.extend([(k,k+1,k+3,k+2),(k+2,k+3,k+4)])
        carpet_m.extend([carpet_rng.choice([2,3,4,5]),carpet_rng.choice([3,4,5,6,7])])
mesh('ContinuousMeadowUnderstorey',carpet_v,carpet_f,plant_mat,carpet_m)
# Individual broad-leaf tips bend locally while each leaf's stem stays rooted.
for patch_index,(px,py) in enumerate([(-22,-10),(-17,-25),(32,-19),(17,-29),(-30,0),(32,4)]):
    v=[];f=[];mi=[];weights=[]
    for i in range(16):
        x=px+carpet_rng.uniform(-1.3,1.3);y=py+carpet_rng.uniform(-1.3,1.3)
        if not planted(x,y):continue
        center=Vector((x,y,.08))
        for j in range(7):
            a=j*math.pi*2/7+carpet_rng.random()*.4
            length=carpet_rng.uniform(.42,.82);width=carpet_rng.uniform(.16,.30)
            axis=Vector((math.cos(a)*.65,math.sin(a)*.65,.5)).normalized()
            side=Vector((-math.sin(a),math.cos(a),0))
            mid=center+axis*length*.5
            tip=center+axis*length
            k=len(v)
            v.extend([tuple(center),tuple(mid-side*width*.5),tuple(mid+Vector((0,0,width*.15))),tuple(mid+side*width*.5),tuple(tip)])
            f.extend([(k,k+1,k+2),(k,k+2,k+3),(k+1,k+4,k+2),(k+2,k+4,k+3)])
            mi.extend([2,3,3,4]);weights.extend([0,.5,.55,.5,1])
    if not v:continue
    o=mesh('WindBroadLeaves_'+str(patch_index),v,f,plant_mat,mi)
    o['wind_kind']='broadleaf';o['wind_roots_fixed']=True
    o.shape_key_add(name='Basis')
    key=o.shape_key_add(name='LeafFlutter')
    for i,w in enumerate(weights):key.data[i].co=Vector(v[i])+Vector((.06*w,-.035*w,-.014*w))
    phase=patch_index*.65
    for frame in range(1,242,10):
        key.value=(.5+.5*math.sin((frame-1)/240*math.pi*4+phase))*.75
        key.keyframe_insert('value',frame=frame)
    key.value=(.5+.5*math.sin(phase))*.75;key.keyframe_insert('value',frame=241)
    o.data.shape_keys.animation_data.action.name='LeafBreeze_'+str(patch_index)
    wind_objects.append(o)

# Garden curb is jointed rather than a perfect unbroken ring.
for i in range(76):
    a=i*math.pi*2/76
    p=Vector((11.2*math.cos(a),-11+7.58*math.sin(a),.30))
    q=Vector((10.90*math.cos(a),-11+7.29*math.sin(a),.30))
    rod('CurbJoint',p,q,.012,M['edge'],5)
# Walkway paving joints and moss tufts in the border cracks.
for y in np.arange(-17.7,-4.5,.8):
    box('WalkPavingJoint',(0,float(y),.451),(1.0,.022,.012),M['edge'])
for x in np.arange(-10.3,10.4,.8):
    box('CrossWalkJoint',(float(x),-11,.461),(.022,.90,.012),M['edge'])
for i in range(30):
    a=rng.random()*6.28
    if abs(math.sin(a))<.12 or abs(math.cos(a))<.12:continue
    ico('CurbMoss',(11.05*math.cos(a),-11+7.45*math.sin(a),.33),(.12,.10,.045),M['moss'],1)


# Slatted campus benches and a pair of parked student bicycles add everyday detail.
category='Landscape'
for name,o in objects.items():
    if not name.startswith('BenchSeat'):continue
    x,y,z=o.location
    hide(o)
    for j in range(4):
        box('BenchSeatSlat',(x,y-.27+j*.18,z),(2.6,.14,.11),M['wood'])
    for dx in (-1.08,1.08):
        rod('BenchBackSupport',(x+dx,y+.28,.48),(x+dx,y+.39,1.88),.042,M['metal'])
    for j in range(3):
        box('BenchBackSlat',(x,y+.38,1.24+j*.22),(2.6,.13,.15),M['metal'])
    for dx in (-1.2,1.2):
        rod('BenchArmrest',(x+dx,y-.20,1.30),(x+dx,y+.40,1.30),.045,M['metal'])
def bicycle(x,y):
    # Bike plane is X/Z, wheel axles run along Y.
    for cx in (x-.70,x+.70):
        R=.36;r=.025;verts=[];faces=[]
        for a in range(20):
            theta=a*math.pi*2/20
            for b in range(6):
                phi=b*math.pi*2/6
                verts.append((cx+(R+r*math.cos(phi))*math.cos(theta),y+r*math.sin(phi),.39+(R+r*math.cos(phi))*math.sin(theta)))
        for a in range(20):
            for b in range(6):
                faces.append((a*6+b,((a+1)%20)*6+b,((a+1)%20)*6+(b+1)%6,a*6+(b+1)%6))
        mesh('BicycleTyre',verts,faces,[M['hair']])
        for a in range(10):
            t=a*math.pi*2/10
            rod('BicycleSpoke',(cx,y,.39),(cx+R*.92*math.cos(t),y,.39+R*.92*math.sin(t)),.007,M['edge'],5)
    rear=(x-.70,y,.39);front=(x+.70,y,.39);crank=(x-.05,y,.42);saddle=(x-.30,y,.99);head=(x+.42,y,1.04)
    for a,b in [(rear,crank),(rear,saddle),(crank,saddle),(saddle,head),(crank,head),(front,head)]:
        rod('BicycleFrame',a,b,.027,M['metal'],8)
    rod('BicycleSeatpost',saddle,(x-.33,y,1.15),.025,M['edge'])
    box('BicycleSaddle',(x-.34,y,1.17),(.28,.18,.065),M['hair'])
    rod('BicycleHandleStem',head,(x+.47,y,1.24),.022,M['edge'])
    rod('BicycleHandlebar',(x+.47,y-.24,1.24),(x+.47,y+.24,1.24),.022,M['edge'])
    rod('BicycleCrank',(x-.05,y-.07,.42),(x+.12,y-.07,.28),.02,M['edge'])
    box('BicyclePedal',(x+.12,y-.15,.28),(.16,.20,.05),M['hair'])
    rod('BicycleKickstand',(x-.14,y,.44),(x-.20,y-.27,.03),.016,M['metal'],6)
bicycle(-15.2,-2.4)
bicycle(17.8,-15.6)

# Festival props, constructed rather than plain box placeholders.
category='Festival'
for y in (-13,-5,3):
    for x in np.arange(21.1,25,.38):
        box('StallPanelBoard',(float(x),y-.86,.69),(.30,.025,.87),M['wood'])
    for side in (-1,1):
        rod('StallBrace',(23+side*2.1,y-1.4,2.4),(23+side*1.45,y-1.4,3.4),.065,M['wood'])
    box('StallShelf',(23,y+.8,2.2),(3.7,.55,.10),M['wood'])
    for i in range(8):
        x=21.6+i*.38
        rod('DisplayBottle',(x,y+.85,2.26),(x,y+.85,2.55),.08,M['teal'] if i%2 else M['orange'],8)
    for i in range(4):
        box('CounterBook',(21.7+i*.75,y-.25,1.41),(.43,.55,.065),M['pink'] if i%2 else M['cream'],(0,0,rng.uniform(-.15,.15)))
# Wooden poster noticeboard with pins and paper edges near the building.
box('Noticeboard',(16,-1,2.3),(2.4,.18,1.9),M['wood'])
for x in (15,17):rod('NoticeboardLeg',(x,-.90,0),(x,-.90,3.25),.065,M['wood'])
for dx,z,mat in [(-.62,2.5,M['cream']),(0,2.2,M['pink']),(0.64,2.53,M['white'])]:
    box('PinnedPoster',(16+dx,-1.10,z),(.56,.022,.72),mat,(0,rng.uniform(-.02,.02),0))
    ico('PosterPin',(16+dx,-1.14,z+.31),(.028,.028,.028),M['gold'],1)
# Crates have open slats and darker interiors.
for name,o in objects.items():
    if name.startswith('PrepCrate'):
        center=o.location
        box('CrateInterior',(center.x,center.y,center.z+.45),(.64,.64,.015),M['dark'])
        for x in (-.33,.33):
            for y in (-.33,.33):
                box('CrateCorner',(center.x+x,center.y+y,center.z),(.075,.075,.91),M['wood'])

# Additional costume relief makes the Kathakali landmark read better in close-up.
category='Kathakali'
for i in range(32):
    a=i*2*math.pi/32
    # Thin red/gold radial strips on the lower skirt.
    p=Vector((1.42*math.cos(a),-23+1.42*math.sin(a),2.38))
    q=Vector((.58*math.cos(a),-23+.58*math.sin(a),3.65))
    rod('SkirtPleat',p,q,.023,M['cream'],5)
for z in (3.86,4.04,4.22,4.40):
    for side in (-1,1):
        ico('CostumeBead',(side*.24,-23.54,z),(.043,.033,.045),M['gold'],1)
for side in (-1,1):
    ico('KathakaliEarring',(side*.43,-23.23,4.80),(.11,.06,.14),M['gold'],2)
# More white/gold crown detailing.
for i in range(24):
    a=i*math.pi*2/24
    ico('CrownOuterPearl',(.79*math.cos(a),-23.005,5.71+.79*math.sin(a)),(.04,.03,.04),M['statuewhite'],1)

# Flags have an anchored top edge and billow, with exported morph animation.
for name,o in objects.items():
    if not name.startswith('Flag_'):continue
    o['breeze']=False;o['wind_kind']='flag'
    o.shape_key_add(name='Basis')
    key=o.shape_key_add(name='Flutter')
    for v,original_v in zip(key.data,o.data.vertices):
        weight=max(0,-original_v.co.z/.7)
        v.co.y+=weight*.07
    phase=int(name.split('_')[-1])*.31
    for frame in range(1,242,10):
        key.value=(.5+.5*math.sin((frame-1)/240*math.pi*8+phase))*.7
        key.keyframe_insert('value',frame=frame)
    key.value=(.5+.5*math.sin(phase))*.7;key.keyframe_insert('value',frame=241)
    o.data.shape_keys.animation_data.action.name='BuntingFlutter_'+name
scene.frame_set(1)
scene['detail_version']=2
scene['reference_video']='/home/rishi/obs/2026-10-06 12-46-16.mp4'
scene['wind_description']='Rooted grass/flag morphs, 8 second loop. No whole-bush rigid-body wobble.'
# Assign UV projection to new textured objects; detailed tiles already have their own UVs.
scene.view_layers[0].update()
for o in scene.objects:projected_uv(o,.45)
# Select the camera and frame the revised model for the user.
for o in scene.objects:o.select_set(False)
scene.camera.select_set(True);bpy.context.view_layer.objects.active=scene.camera
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.color_type='MATERIAL'
scene.render.filepath=str(OUT/'campus-wide.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus-detailed.blend'),check_existing=False)
visible=[o for o in scene.objects if not o.hide_render]
stats={'version':2,'scene':scene.name,'objects':len(scene.objects),'visibleObjects':len(visible),
       'triangles':sum(len(p.vertices)-2 for o in visible if o.type=='MESH' for p in o.data.polygons),
       'raisedTiles':tile_count,'texturedMaterials':len(texture_records),'textureResolution':512,
       'animatedGrassPatches':len(wind_objects),'windLoopSeconds':8,'siteChanged':False}
(ROOT/'assets/model-v2-info.json').write_text(json.dumps(stats,indent=2))
result=stats
