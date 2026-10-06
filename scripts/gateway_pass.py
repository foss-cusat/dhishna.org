
"""Replace the temporary entry banner with a CUSAT-inspired iron gate."""
import bpy,math,random,pathlib,json
from mathutils import Vector,Matrix
ROOT=pathlib.Path('/home/rishi/devmt/dhishna.org')
s=bpy.data.scenes['Dhishna_Campus_Detailed'];bpy.context.window.scene=s
coll=bpy.data.collections.get('V3_Gateway')
if coll:
    for o in list(coll.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
    coll=bpy.data.collections.new('V3_Gateway');s.collection.children.link(coll)
trees=bpy.data.collections.get('V3_ApproachTrees')
if trees:
    for o in list(trees.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
    trees=bpy.data.collections.new('V3_ApproachTrees');s.collection.children.link(trees)
for o in s.objects:
    if o.name.startswith(('V2_BannerPole','V2_DhishnaBanner')):
        o.hide_render=True;o.hide_viewport=True;o['detail_hidden']=True
def material(name,color,metallic=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.8;p.inputs['Metallic'].default_value=metallic
    return m
iron=material('Gate_AgedIron',(.027,.040,.034),.35)
letters=material('Gate_WeatheredLetters',(.58,.61,.50),.15)
ornament=material('Gate_PatinaMedallions',(.28,.29,.20),.25)
bark=bpy.data.materials['V2_D_bark'];pink=bpy.data.materials['V2_D_pink']
cream=bpy.data.materials['V2_D_curb'];road=bpy.data.materials['V2_D_road']
leaves=[bpy.data.materials['V2_D_Leaf'+str(i)] for i in (0,1,2,3,4,5,7)]
active=coll
def relink(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    active.objects.link(o)
def box(name,p,dim,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name
    o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat);relink(o);return o
def rod(name,p,q,r,mat,vertices=8,r2=None):
    p=Vector(p);q=Vector(q)
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=r,radius2=r if r2 is None else r2,
                                  depth=(q-p).length,location=(p+q)*.5)
    o=bpy.context.object;o.name=name;o.rotation_euler=(q-p).to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mat);relink(o);return o
def mesh(name,v,f,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();me.materials.append(mat)
    o=bpy.data.objects.new(name,me);active.objects.link(o);return o
def line(name,points,r,mat):
    for p,q in zip(points,points[1:]):rod(name,p,q,r,mat,6)
Y=-30
# Broad, weathered masonry piers with recessed face panels and stone caps.
for sign in (-1,1):
    x=sign*7.8
    box('CusatGatePier',(x,Y,1.72),(1.32,1.15,3.38),pink)
    box('CusatGatePierPlinth',(x,Y,.19),(1.64,1.45,.32),cream)
    box('CusatGatePierCap',(x,Y,3.48),(1.54,1.38,.17),cream)
    box('CusatGatePierInset',(x,Y-.594,1.84),(.77,.035,2.41),bpy.data.materials['V2_D_pinklight'])
    for yy in (-.25,.25):
        rod('CusatGateHinge',(sign*7.05,Y+yy,.54),(sign*7.05,Y+yy,2.45),.045,iron)
    # Short adjoining walls anchor the gate to the tree-lined campus edge.
    box('CusatGateBoundaryWall',(sign*10.0,Y,1.15),(3.05,.65,2.25),pink)
    box('CusatGateBoundaryCap',(sign*10.0,Y,2.32),(3.15,.81,.14),cream)
# Flared paved apron joins the road at the new entry.
mesh('CusatGateApron',[(-4.5,-35.4,.082),(4.5,-35.4,.082),(7.07,-31.7,.082),
                      (7.07,-28.8,.082),(4.5,-27.4,.082),(-4.5,-27.4,.082),
                      (-7.07,-28.8,.082),(-7.07,-31.7,.082)],
     [(0,1,2,3,4,5,6,7)],road)
# Three concentric curved iron ribs form the university's characteristic arch.
arc_specs=[(8.18,5.22),(8.46,5.93),(8.73,6.64)]
def ap(rx,rz,t,y=Y):return (rx*math.cos(t),y,2.70+rz*math.sin(t))
for rx,rz in arc_specs:
    line('CusatGateArchRib',[ap(rx,rz,math.pi-i*math.pi/80) for i in range(81)],.041,iron)
for i in range(39):
    t=math.pi-i*math.pi/38
    rod('CusatGateArchWeb',ap(*arc_specs[0],t),ap(*arc_specs[-1],t),.023,iron,6)
# Cross braces give the overhead sign frame depth.
for sign in (-1,1):
    line('CusatGateArchFoot',[(sign*8.18,Y,2.70),(sign*7.8,Y,3.43)],.055,iron)
# Individual letters follow the actual curved sign baseline.
def arc_text(text,rx,rz,zoff,size,spacing):
    glyphs=[];widths=[]
    for ch in text:
        if ch==' ':glyphs.append(None);widths.append(size*.40+spacing);continue
        d=bpy.data.curves.new('GateLetter','FONT');d.body=ch;d.size=size;d.align_x='CENTER'
        d.extrude=.009;d.bevel_depth=.002;d.resolution_u=3
        o=bpy.data.objects.new('CusatGateLetter_'+ch,d);coll.objects.link(o);d.materials.append(letters)
        glyphs.append(o);widths.append(size*(.32 if ch in 'I' else .72 if ch in 'MW' else .60)+spacing)
    samples=[math.pi-i*math.pi/3000 for i in range(3001)]
    pts=[Vector((rx*math.cos(t),0,rz*math.sin(t))) for t in samples]
    lengths=[0]
    for p,q in zip(pts,pts[1:]):lengths.append(lengths[-1]+(q-p).length)
    offset=(lengths[-1]-sum(widths))*.5
    import bisect
    for o,width in zip(glyphs,widths):
        distance=offset+width*.5;offset+=width
        if o is None:continue
        idx=min(len(samples)-1,bisect.bisect_left(lengths,distance));t=samples[idx]
        tangent=Vector((rx*math.sin(t),0,-rz*math.cos(t))).normalized()
        up=Vector((-tangent.z,0,tangent.x))
        o.matrix_world=Matrix(((tangent.x,up.x,0,rx*math.cos(t)),
                               (0,0,-1,Y-.065),
                               (tangent.z,up.z,0,2.70+rz*math.sin(t)+zoff),
                               (0,0,0,1)))
arc_text('COCHIN UNIVERSITY OF',8.56,6.08,.11,.61,.11)
arc_text('SCIENCE AND TECHNOLOGY',8.28,5.35,.08,.57,.09)
# Pair of closed iron leaves, with a pointed central profile and repeated lancet arches.
for sign in (-1,1):
    xmin,xmax=(-7.06,-.06) if sign<0 else (.06,7.06)
    for z in (.27,1.23,2.08):
        rod('CusatGateLeafRail',(xmin,Y,z),(xmax,Y,z),.034,iron)
    def top(x):return 2.75+1.27*(1-abs(x)/7.06)
    line('CusatGatePointedTop',[(xmin,Y,top(xmin)),(xmax,Y,top(xmax))],.062,iron)
    for x in (xmin,xmax):
        rod('CusatGateLeafStile',(x,Y,.23),(x,Y,top(x)),.052,iron)
    for i in range(17):
        x=xmin+(i+.5)*(xmax-xmin)/17
        rod('CusatGatePicket',(x,Y,.28),(x,Y,top(x)-.14),.018,iron,6)
        # Small pointed arches sit above the medallion rail.
        z=top(x)-.56;w=.17
        line('CusatGateLancet',[(x-w,Y,z-.38),(x-w,Y,z),(x,Y,z+.34),
                              (x+w,Y,z),(x+w,Y,z-.38)],.021,letters)
        # Low-relief round ornaments echo the gate without bright metallic shine.
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.17,depth=.023,
                                            location=(x,Y-.025,1.43),rotation=(math.pi/2,0,0))
        o=bpy.context.object;o.name='CusatGateMedallion';o.data.materials.append(ornament);relink(o)
    for z in (.91,1.80):
        box('CusatGateLatch',(sign*.12,Y-.075,z),(.18,.12,.085),iron)
# The smaller administrative-office plaque is carried below the large arch.
box('CusatAdministrativeSignFrame',(0,Y,5.10),(6.6,.14,.36),iron)
d=bpy.data.curves.new('AdministrativeOfficeLabel','FONT');d.body='ADMINISTRATIVE OFFICE'
d.align_x='CENTER';d.align_y='CENTER';d.size=.27;d.extrude=.004
o=bpy.data.objects.new('CusatAdministrativeOfficeLabel',d);coll.objects.link(o)
o.location=(0,Y-.088,5.10);o.rotation_euler=(math.pi/2,0,0);d.materials.append(letters)
# Enlarge only the figure, keeping the pedestal and garden layout stable.
if not s.get('statue_enlarged'):
    anchor=Vector((0,-11,1.58));transform=Matrix.Translation(anchor)@Matrix.Scale(1.25,4)@Matrix.Translation(-anchor)
    for o in bpy.data.collections['V2_Kathakali'].objects:
        if o.name.startswith(('V2_StatuePlinth','V2_StatuePlaque')):continue
        o.matrix_world=transform@o.matrix_world
    s['statue_enlarged']=1.25
# Extra trees frame the gateway and make the campus perimeter feel wooded.
active=trees;rng=random.Random(270117)
positions=[(-14,-36,9),(20,-39,9),(-26,-36,12),(31,-33,12),
           (-37,-23,14),(40,-17,14),(-40,-6,16),(40,16,16),
           (-36,29,15),(-24,31,14),(-8,30,15),(14,31,14),(31,29,16)]
for index,(x,y,h) in enumerate(positions):
    crown=Vector((x+rng.uniform(-.7,.7),y+rng.uniform(-.7,.7),h*.86))
    base=Vector((x,y,.04));p=base
    for i in range(4):
        q=base.lerp(crown,(i+1)/4)+Vector((rng.uniform(-.10,.10),rng.uniform(-.10,.10),0))
        rod('ApproachTreeTrunk',p,q,.30*(1-.16*i),bark,8,r2=.30*(1-.16*(i+1)));p=q
    for j in range(5):
        a=j*math.tau/5+rng.uniform(-.35,.35)
        end=crown+Vector((math.cos(a)*h*.20,math.sin(a)*h*.17,rng.uniform(.0,1.65)))
        rod('ApproachTreeBranch',base.lerp(crown,.65),end,.12,bark,7,r2=.055)
        radius=h*rng.uniform(.16,.23)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2 if j%2 else 1,radius=1,location=end)
        o=bpy.context.object;o.name='ApproachTreeCrown'
        o.scale=(radius*rng.uniform(.95,1.16),radius*rng.uniform(.8,1.02),radius*rng.uniform(.82,1.18))
        o.data.materials.append(leaves[(index+j)%len(leaves)]);relink(o)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=crown+Vector((0,0,1.7)))
    o=bpy.context.object;o.name='ApproachTreeCrownTop';o.scale=(h*.20,h*.20,h*.22)
    o.data.materials.append(leaves[(index+2)%len(leaves)]);relink(o)
s.camera=s.objects['V2_DhishnaCamera'];s.frame_set(1)
s['gateway_reference']='/tmp/codex-clipboard-9QGX5N.png'
s['gateway_version']=1;s['extra_trees']=len(positions)
s.render.filepath=str(ROOT/'artifacts/model-v2/campus-wide.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus-detailed.blend'),check_existing=False)
result={'bannerRemoved':True,'gate':'CUSAT arch and paired iron leaves','extraTrees':len(positions),'statueScale':1.25}
