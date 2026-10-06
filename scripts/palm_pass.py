
# Reference palm crowns: layered, asymmetric arching fronds with folded leaflets.
import bpy,math,random,pathlib
from mathutils import Vector
scene=bpy.data.scenes['Dhishna_Campus_Detailed']
land=bpy.data.collections['V2_Landscape']
for o in list(scene.objects):
    if o.name.startswith(('FeatheredPalm','PalmMidrib','NaturalPalm')):
        bpy.data.objects.remove(o,do_unlink=True)
leafnames=['V2_D_Leaf0','V2_D_Leaf1','V2_D_Leaf2','V2_D_Leaf3','V2_D_Leaf4','V2_D_Leaf7']
mats=[bpy.data.materials[n] for n in leafnames]
rng=random.Random(117)
for palm,(x,y,h) in enumerate([(-21,-18,12),(30,-17,13),(-35,8,16),(27,26,16),(40,5,14)]):
    verts=[];faces=[];mi=[]
    for j in range(15):
        a=j*math.tau/9+.23+rng.uniform(-.15,.15)
        axis=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
        base=Vector((x+.4,y,h+rng.uniform(-.12,.25)))
        length=rng.uniform(4.0,5.7) if j<9 else rng.uniform(2.5,4.5)
        rise=rng.uniform(.75,1.6) if j<9 else rng.uniform(1.8,3.0)
        drop=rng.uniform(2.1,3.4) if j<9 else rng.uniform(.6,1.4)
        def position(t):return base+axis*(length*t)+Vector((0,0,rise*math.sin(math.pi*t)-drop*t*t))
        for i in range(28):
            t=(i+.4)/28;p=position(t)
            spread=(1.25 if j<9 else .95)*math.sin(math.pi*t)**.60+.055
            for sign in (-1,1):
                direction=side*sign
                # Leaflets lean forward and curl down at the tip.
                mid=p+direction*spread*.56+axis*.12+Vector((0,0,-.12))
                tip=p+direction*spread+axis*.30+Vector((0,0,-.30-.28*t))
                width=.125*math.sin(math.pi*t)**.4+.025
                k=len(verts)
                verts.extend([tuple(p-axis*.065),tuple(mid-axis*width),tuple(mid+Vector((0,0,.055))),
                              tuple(mid+axis*width),tuple(tip)])
                faces.extend([(k,k+1,k+2),(k,k+2,k+3),(k+1,k+4,k+2),(k+2,k+4,k+3)])
                shade=(palm+j+(1 if sign>0 else 0))%len(mats)
                mi.extend([shade,(shade+1)%len(mats),shade,(shade+1)%len(mats)])
        # A narrow curved central blade joins the individual leaflets.
        for i in range(20):
            p=position(i/20);q=position((i+1)/20);k=len(verts)
            verts.extend([tuple(p-side*.035),tuple(p+side*.035),tuple(q-side*.026),tuple(q+side*.026)])
            faces.append((k,k+1,k+3,k+2));mi.append(0)
    me=bpy.data.meshes.new('NaturalPalmCrown');me.from_pydata(verts,[],faces);me.update()
    for m in mats:me.materials.append(m)
    for p,idx in zip(me.polygons,mi):p.material_index=idx
    o=bpy.data.objects.new('NaturalPalm_'+str(palm),me);land.objects.link(o)
scene['palm_crown_version']=3
bpy.ops.wm.save_as_mainfile(filepath='/home/rishi/devmt/dhishna.org/assets/dhishna-campus-detailed.blend',check_existing=False)
result={'palmCrowns':5,'layeredFronds':75}
