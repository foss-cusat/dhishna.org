"""Dhishna 2027 campus. Run inside Blender or: blender -b --python scripts/build_scene.py
Creates a new named scene; never deletes the user's existing scenes.
Seeded geometry, no external assets. Exports static geometry batched by collection/material.
"""
import bpy, math, random, json, os
from pathlib import Path
from mathutils import Vector
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1] if '__file__' in globals() else Path('/home/rishi/devmt/dhishna.org')
SEED = 2027
rng = random.Random(SEED)
scene = bpy.data.scenes.new('Dhishna_Campus')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
collections = {}
for name in ['Architecture', 'Landscape', 'Kathakali', 'Festival', 'Students', 'Lighting']:
    c = bpy.data.collections.new('Dhishna_' + name)
    scene.collection.children.link(c)
    collections[name] = c
category = 'Architecture'
def srgb(v):
    return v / 12.92 if v < 0.04045 else ((v + 0.055) / 1.055) ** 2.4
def material(name, hexcolor):
    rgb = tuple(srgb(int(hexcolor[i:i+2],16)/255) for i in (0,2,4))
    m = bpy.data.materials.new('D_' + name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb,1)
    p.inputs['Roughness'].default_value = .88
    return m
M = {name: material(name,color) for name,color in {
    'cream':'ede3c8','white':'fff4df','pink':'b96873','pinklight':'ce8790','dark':'24443b',
    'glass':'3e6560','wood':'6d472c','bark':'805b36','earth':'b0bc70','grass':'8aa957',
    'road':'a3a18a','path':'d5c7a0','curb':'e6dfc3','gold':'dfa633','orange':'ee8850',
    'red':'b63740','teal':'38756c','blue':'536e91','skin':'b88050','hair':'302d23',
    'statuegreen':'368c53','statuewhite':'f8eddd','statuered':'dc343e','black':'232f2a'
}.items()}
ROOF = [material('Roof'+str(i),h) for i,h in enumerate(['aa5940','b56646','c57b50','a4533b','cc8756','b96d48'])]
LEAF = [material('Leaf'+str(i),h) for i,h in enumerate(['3e7940','4a8743','649b48','79aa51','95b757','317145','548c40','a2bf64'])]
primitives={}
def mesh(name, verts, faces, mat):
    d=bpy.data.meshes.new(name+'Mesh')
    d.from_pydata(verts,[],faces);d.update()
    if mat: d.materials.append(mat)
    o=bpy.data.objects.new(name,d);collections[category].objects.link(o)
    return o
def object_from(name,data,loc,scale=(1,1,1),rotation=(0,0,0)):
    o=bpy.data.objects.new(name,data);collections[category].objects.link(o)
    o.location=loc;o.scale=scale;o.rotation_euler=rotation
    return o
def box(name,loc,size,mat,rotation=(0,0,0)):
    key=('box',mat.name)
    if key not in primitives:
        verts=[(x*.5,y*.5,z*.5) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        faces=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
        d=bpy.data.meshes.new('UnitCube_'+mat.name);d.from_pydata(verts,[],faces);d.materials.append(mat)
        primitives[key]=d
    return object_from(name,primitives[key],loc,size,rotation)
def cone(name,loc,r1,r2,h,mat,n=12,rotation=(0,0,0)):
    key=('cone',n,round(r2/r1,4) if r1 else 0,mat.name)
    if key not in primitives:
        ratio=r2/r1 if r1 else 0
        verts=[(math.cos(i*2*math.pi/n)*r,math.sin(i*2*math.pi/n)*r,z) for r,z in [(1,-.5),(ratio,.5)] for i in range(n)]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        d=bpy.data.meshes.new('Cone_'+str(len(primitives)));d.from_pydata(verts,[],faces);d.materials.append(mat)
        primitives[key]=d
    return object_from(name,primitives[key],loc,(r1,r1,h),rotation)
def rod(name,a,b,r,mat,n=8):
    a,b=Vector(a),Vector(b);d=b-a
    o=cone(name,(a+b)*.5,r,r,d.length,mat,n)
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return o
def ico(name,loc,size,mat,sub=1):
    key=('ico',sub,mat.name)
    if key not in primitives:
        import bmesh
        d=bpy.data.meshes.new('Ico_'+mat.name+str(sub));bm=bmesh.new()
        bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1)
        bm.to_mesh(d);bm.free();d.materials.append(mat)
        primitives[key]=d
    return object_from(name,primitives[key],loc,size,(rng.random()*.4,rng.random()*.4,rng.random()*6.28))
def polygon_xz(name,points,y,depth,mat):
    n=len(points)
    v=[(x,y+dy,z) for dy in (0,depth) for x,z in points]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,v,f,mat)
def arch(name,x,y,z,w,h,mat):
    pts=[(x-w/2,z),(x+w/2,z),(x+w/2,z+h*.67)]
    pts += [(x+w*.5*math.cos(t),z+h*.67+h*.33*math.sin(t)) for t in [i*math.pi/8 for i in range(1,9)]]
    return polygon_xz(name,pts,y,.12,mat)
def text(name,body,loc,size,mat,rotation=(math.pi/2,0,0)):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.align_x='CENTER';d.align_y='CENTER';d.extrude=.008
    d.materials.append(mat);o=bpy.data.objects.new(name,d);collections[category].objects.link(o)
    o.location=loc;o.rotation_euler=rotation
    return o
def roof(name,cx,cy,w,d,z,rise):
    # Hipped roof with colored tile quads. Rows follow slopes, cap pieces add relief.
    ridge=max(w*.5-d*.38, .2)
    v=[(cx-w/2,cy-d/2,z),(cx+w/2,cy-d/2,z),(cx+w/2,cy+d/2,z),(cx-w/2,cy+d/2,z),(cx-ridge,cy,z+rise),(cx+ridge,cy,z+rise)]
    roofobj=mesh(name,v,[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4)],ROOF[0])
    box(name+'_FasciaFront',(cx,cy-d/2,z-.10),(w,.16,.24),M['wood'])
    box(name+'_FasciaBack',(cx,cy+d/2,z-.10),(w,.16,.24),M['wood'])
    box(name+'_FasciaLeft',(cx-w/2,cy,z-.10),(.16,d,.24),M['wood'])
    box(name+'_FasciaRight',(cx+w/2,cy,z-.10),(.16,d,.24),M['wood'])
    verts=[];faces=[];indices=[]
    rows=max(4,int(d/.7));cols=max(8,int(w/.48))
    for side in (-1,1):
        for row in range(rows):
            t0=row/rows;t1=(row+1)/rows
            hw0=w/2+(ridge-w/2)*t0;hw1=w/2+(ridge-w/2)*t1
            for col in range(cols):
                a=col/cols;b=(col+1)/cols
                p=[(cx-hw0+2*hw0*a,cy+side*d/2*(1-t0),z+rise*t0+.028),
                   (cx-hw0+2*hw0*b,cy+side*d/2*(1-t0),z+rise*t0+.028),
                   (cx-hw1+2*hw1*b,cy+side*d/2*(1-t1),z+rise*t1+.028),
                   (cx-hw1+2*hw1*a,cy+side*d/2*(1-t1),z+rise*t1+.028)]
                off=len(verts);verts+=p;faces.append(tuple(range(off,off+4)));indices.append(rng.randrange(len(ROOF)))
    tile=mesh(name+'_Tiles',verts,faces,None)
    for m in ROOF:tile.data.materials.append(m)
    for p,i in zip(tile.data.polygons,indices):p.material_index=i
    rod(name+'_Ridge',(cx-ridge,cy,z+rise+.08),(cx+ridge,cy,z+rise+.08),.11,ROOF[4])
    return roofobj
def window(x,y,z,w=1.1,h=2.5,pointed=False):
    box('WindowFrame',(x,y,z+h/2),(w+.16,.18,h+.18),M['white'])
    if pointed:
        arch('ArchedWindow',x,y-.11,z,w,h,M['dark'])
    else: box('WindowGlass',(x,y-.12,z+h/2),(w,.08,h),M['glass'])
    box('WindowMullion',(x,y-.18,z+h/2),(.08,.08,h),M['white'])
    box('WindowTransom',(x,y-.19,z+h*.38),(w,.08,.08),M['white'])
    box('WindowSill',(x,y-.22,z-.08),(w+.30,.40,.12),M['cream'])

# Architecture: facade at y=3, entrance projects into garden.
for x in (-10.7,10.7):
    box('TowerCream',(x,6.4,8.8),(5.8,6.8,17.6),M['cream'])
    box('TowerPinkInset',(x,2.96,9.0),(3.95,.13,15.8),M['pink'])
    box('TowerFoot',(x,6.4,.30),(6.15,7.0,.60),M['pink'])
    for z in (1.4,6.6,11.8):
        for dx in (-.93,.93):window(x+dx,2.81,z,1.23,3.25,True)
        box('TowerLevelBand',(x,2.70,z+3.75),(4.02,.10,.12),M['cream'])
    roof('TowerRoof',x,6.4,7.6,8.3,17.7,2.9)
    polygon_xz('TowerGable',[(x-3.0,17.75),(x+3.0,17.75),(x,20.45)],2.12,.18,M['white'])
    polygon_xz('GableInset',[(x-2.20,18.05),(x+2.20,18.05),(x,19.97)],2.08,.07,M['pinklight'])
    # Kerala-style white bargeboards and small geometric ornament.
    rod('GableTrim',(x-3.1,2.03,17.80),(x,2.03,20.56),.12,M['white'])
    rod('GableTrim',(x,2.03,20.56),(x+3.1,2.03,17.80),.12,M['white'])
    for dx in [-1.8,-1.2,-.6,0,.6,1.2,1.8]:
        z=18.55+(1-abs(dx)/2.4)*.65
        box('GableDiamond',(x+dx,1.96,z),(.24,.06,.24),M['white'],(0,math.pi/4,0))
    rod('RoofFinial',(x,6.4,20.62),(x,6.4,21.5),.09,M['gold'])

box('MainBuilding',(0,7.3,6.3),(15.6,8.6,12.6),M['cream'])
for z in (1.2,5.5,9.2):
    box('FacadePinkBand',(0,2.93,z+1.35),(15.6,.14,2.9),M['pinklight'])
    for x in (-6.1,-3.1,0,3.1,6.1):window(x,2.78,z,1.65,2.6)
roof('CentralRoof',0,7.3,16.6,10,12.7,2.35)
# Two wings behind towers, with visible windows.
for side in (-1,1):
    x=side*20.3
    box('SideWing',(x,9,5.1),(13.4,9,10.2),M['cream'])
    for z in (1.3,5.9):
        box('WingPinkBand',(x,4.46,z+1.35),(13.4,.12,3.0),M['pinklight'])
        for dx in (-4.6,-1.6,1.6,4.6):window(x+dx,4.34,z,1.6,2.7)
    roof('WingRoof',x,9,14.5,10.2,10.3,2.0)
    # Outer side windows.
    for yy in (6.0,9.0,12.0):
        for zz in (2.6,7.1):
            box('SideGlass',(x+side*6.74,yy,zz),(.09,1.25,2.5),M['glass'])
            box('SideLintel',(x+side*6.81,yy,zz+1.3),(.14,1.5,.13),M['white'])
# Entrance, three shadowed arches, columns, tiled verandah.
box('EntranceShadow',(0,2.10,2.1),(14,.30,4.2),M['dark'])
for x in (-4.8,0,4.8):arch('EntranceArch',x,1.89,.15,3.75,3.75,M['dark'])
for x in (-7.2,-2.4,2.4,7.2):
    box('VerandahPillar',(x,.2,2.45),(.42,.52,4.9),M['white'])
    box('PillarBase',(x,.2,.3),(.70,.75,.50),M['cream'])
    box('PillarCapital',(x,.2,4.60),(.72,.76,.30),M['white'])
box('EntrancePlatform',(0,.2,.15),(15.8,5.0,.30),M['curb'])
for i in range(3):
    box('EntranceStep',(0,-2.6-i*.38,.10-i*.05),(16,.65,.20),M['cream'])
roof('VerandahRoof',0,.85,16.3,5.6,4.85,1.65)
box('BalconyFloor',(0,1.0,6.9),(15.4,3.4,.27),M['cream'])
for x in (-7.2,-2.4,2.4,7.2):box('UpperPillar',(x,.0,8.0),(.3,.4,2.2),M['white'])
for x in [i*.38 for i in range(-19,20)]:
    cone('BalconyBaluster',(x,-.77,7.48),.08,.065,.9,M['white'],8)
box('BalconyRail',(0,-.77,7.99),(15.0,.22,.18),M['white'])
roof('BalconyRoof',0,1.0,16.2,4.2,9.0,1.55)
text('CUSATSign','C U S A T',(0,2.47,11.1),.70,M['white'])

# Grounds: large continuous terrain, oval approach road and manicured garden.
category='Landscape'
box('CampusGround',(0,0,-.22),(160,145,.40),M['earth'])
def disk(name,x,y,rx,ry,z,depth,mat,n=64):
    o=cone(name,(x,y,z),1,1,depth,mat,n);o.scale.x=rx;o.scale.y=ry
    return o
disk('ApproachRoad',0,-11,15.3,11.0,.025,.08,M['road'])
disk('GardenCurb',0,-11,11.25,7.65,.13,.30,M['curb'])
disk('GardenLawn',0,-11,10.86,7.25,.29,.16,M['grass'])
box('GardenWalk',(0,-11,.40),(1.0,14.3,.07),M['path'])
box('GardenCrossWalk',(0,-11,.41),(21.5,.9,.07),M['path'])
box('EntranceWalk',(0,-3.7,.1),(5.1,3.0,.1),M['path'])
box('RoadExit',(0,-32,.05),(7.0,23,.08),M['road'])
disk('StatueIslandCurb',0,-23,4.0,3.25,.15,.35,M['curb'],48)
disk('StatueIslandGrass',0,-23,3.65,2.93,.35,.13,M['grass'],48)
rod('FlagPole',(0,-10,.45),(0,-10,10.5),.045,M['cream'])
cone('FlagPoleBase',(0,-10,.60),.6,.4,.5,M['curb'],12)
for yy in (-31,-30,-29):
    for xx in (-2.5,-1.5,-.5,.5,1.5,2.5):box('Crossing',(xx,yy,.11),(.65,.32,.035),M['cream'])
# Gravel path towards the fest stalls on right.
box('StallPath',(22,-6,.05),(10,37,.12),M['path'])
for side in (-1,1):
    for yy in range(-6,18,6):
        cone('TerracottaPot',(side*15.9,yy,.48),.35,.52,.75,ROOF[2])
        ico('PotShrub',(side*15.9,yy,1.3),(.65,.65,.90),LEAF[3],2)

# Kathakali statue in a garden island. Front faces -Y.
category='Kathakali'
sx,sy=0,-23
box('StatuePlinth',(sx,sy,.90),(3.15,2.4,1.15),M['red'])
box('StatuePlinthCap',(sx,sy,1.51),(3.5,2.65,.18),M['statuered'])
box('StatuePlaque',(sx,sy-1.22,.9),(1.9,.035,.42),M['black'])
for dx in (-.34,.34):
    cone('StatueLeg',(sx+dx,sy,1.98),.17,.16,.9,M['statuered'],10)
    box('StatueFoot',(sx+dx,sy-.16,1.60),(.31,.48,.17),M['black'])
cone('KathakaliSkirt',(sx,sy,3.02),1.52,.52,1.55,M['statuewhite'],32)
for z,r in [(2.31,1.50),(2.46,1.38),(2.63,1.24)]:
    cone('SkirtRedTrim',(sx,sy,z),r,r-.03,.085,M['statuered'],32)
for i in range(16):
    a=i*2*math.pi/16
    ico('SkirtOrnament',(sx+1.43*math.cos(a),sy+1.43*math.sin(a),2.45),(.08,.08,.10),M['gold'])
cone('KathakaliTorso',(sx,sy,4.13),.48,.58,.80,M['statuered'],12)
box('CostumeFront',(sx,sy-.47,4.12),(.55,.08,.75),M['black'])
for z in (3.88,4.14,4.40):ico('GoldJewelry',(sx,sy-.54,z),(.14,.07,.14),M['gold'])
# Arms held in a dance gesture.
for side in (-1,1):
    shoulder=(sx+side*.55,sy,4.40);elbow=(sx+side*.95,sy-.10,4.0);hand=(sx+side*.72,sy-.42,4.54)
    rod('StatueUpperArm',shoulder,elbow,.16,M['statuered'])
    rod('StatueForearm',elbow,hand,.13,M['statuered'])
    ico('StatueHand',hand,(.16,.12,.17),M['gold'])
ico('ChuttiFaceFrame',(sx,sy-.13,4.90),(.52,.25,.48),M['statuewhite'],2)
ico('KathakaliGreenFace',(sx,sy-.36,4.97),(.30,.14,.32),M['statuegreen'],2)
for dx in (-.12,.12):box('StatueEye',(sx+dx,sy-.49,5.06),(.115,.03,.045),M['black'])
box('StatueMouth',(sx,sy-.50,4.86),(.18,.035,.045),M['statuered'])
# Disk crown set vertically. Its concentric rings and dots read at hero scale.
for rad,yy,mat in [(0.83,.14,M['statuered']),(.72,.08,M['gold']),(.60,.02,M['statuewhite']),(.49,-.05,M['gold'])]:
    cone('KathakaliCrown',(sx,sy+yy,5.71),rad,rad,.075,mat,32,(math.pi/2,0,0))
for i in range(18):
    a=i*math.pi*2/18
    ico('CrownPearl',(sx+.67*math.cos(a),sy-.045,5.71+.67*math.sin(a)),(.06,.06,.06),M['statuered'])
cone('CrownFinial',(sx,sy+.10,6.65),.12,0,.50,M['gold'],8)

# Dense layered vegetation. Shared meshes keep the editable file reasonably small.
category='Landscape'
def tree(x,y,h):
    rod('TreeTrunk',(x,y,0),(x,y,h*.73),.14+h*.014,M['bark'])
    for i,(dx,dy,dz,s) in enumerate([(-.20,0,.73,.27),(.18,.08,.83,.25),(0,-.08,.95,.25)]):
        mat=LEAF[rng.randrange(len(LEAF))]
        ico('TreeCanopy',(x+dx*h,y+dy*h,h*dz),(h*s,h*s*.90,h*s*.94),mat,2)
        if i<2:rod('TreeBranch',(x,y,h*.50),(x+dx*h,y+dy*h,h*dz),.09,M['bark'])
def palm(x,y,h):
    rod('PalmTrunk',(x,y,0),(x+.4,y,h),.18,M['bark'],10)
    for i in range(8):
        a=i*math.pi/4;dx=math.cos(a);dy=math.sin(a)
        v=[(x+.4,y,h),(x+.4+dx*1.6-dy*.35,y+dy*1.6+dx*.35,h+.35),
           (x+.4+dx*4,y+dy*4,h-1.1),(x+.4+dx*1.6+dy*.35,y+dy*1.6-dx*.35,h+.35)]
        mesh('PalmFrond',v,[(0,1,2),(0,2,3)],LEAF[i%6])
# Trees framing building without hiding facade.
for x,y,h in [(-23,-9,11),(-28,0,15),(-31,12,15),(-22,21,16),(-11,23,14),(2,27,15),
              (16,25,14),(29,22,16),(34,10,13),(33,-3,12),(-33,-22,12),(36,-24,13),(-18,-28,9),(24,-29,8)]:
    tree(x,y,h)
for i in range(42):
    x=rng.uniform(-54,54);y=rng.uniform(22,52)
    tree(x,y,rng.uniform(8,17))
for x,y,h in [(-21,-18,12),(30,-17,13),(-35,8,16),(27,26,16),(40,5,14)]:palm(x,y,h)
# Manicured garden perimeter.
for i in range(36):
    a=i*2*math.pi/36
    x,y=10.2*math.cos(a),-11+6.5*math.sin(a)
    if abs(x)<1.2 or abs(y+11)<.7:continue
    ico('GardenHedge',(x,y,.85),(.7,.55,.75),LEAF[3 if i%3 else 2],2)
for i in range(13):
    a=i*2*math.pi/13
    x,y=3.05*math.cos(a),-23+2.43*math.sin(a)
    ico('StatueHedge',(x,y,.70),(.47,.45,.55),LEAF[2],2)
# Layered undergrowth, leaving roads, facade and stalls open.
for i in range(550):
    x=rng.uniform(-58,58);y=rng.uniform(-47,42)
    if (-29<x<29 and y>1 and y<20) or (abs(x)<17 and -35<y<2) or (17<x<28 and -24<y<17):continue
    r=rng.uniform(.35,1.5)
    ico('WildShrub',(x,y,r*.5),(r,r*.8,r*.85),rng.choice(LEAF),1 if i%3 else 2)
# Low polygon grass tufts combined to avoid thousands of objects.
gv=[];gf=[]
for i in range(2200):
    x=rng.uniform(-58,58);y=rng.uniform(-46,42)
    if (-29<x<29 and 1<y<20) or (abs(x)<17 and -35<y<2) or (17<x<28 and -24<y<17):continue
    h=rng.uniform(.22,.70);w=h*.35
    for a in (rng.uniform(0,6.28),rng.uniform(0,6.28)):
        dx=math.cos(a)*w;dy=math.sin(a)*w;k=len(gv)
        gv.extend([(x-dx,y-dy,.01),(x+dx,y+dy,.01),(x+dx*.7,y+dy*.7,h)])
        gf.append((k,k+1,k+2))
grass=mesh('MeadowGrass',gv,gf,LEAF[3]);grass.data.materials.append(LEAF[7])
for p in grass.data.polygons:p.material_index=rng.randrange(2)
for i in range(90):
    x=rng.uniform(-33,33);y=rng.uniform(-33,-3)
    if abs(x)<17:continue
    ico('MeadowFlower',(x,y,.55),(.12,.12,.12),M['orange'] if i%3 else M['pinklight'])

# Dense fern beds soften the edges of the campus without covering the approach.
frng = random.Random(SEED + 1)
for i in range(340):
    x=frng.uniform(-38,38);y=frng.uniform(-39,25)
    if (-29<x<29 and 1<y<20) or (abs(x)<17 and -35<y<2) or (17<x<28 and -24<y<17):continue
    r=frng.uniform(.5,1.25)
    ico('FernBedShrub',(x,y,r*.48),(r,r*.82,r*.85),LEAF[i%8],2)
fern_v=[];fern_f=[];fern_m=[]
for i in range(1350):
    x=frng.uniform(-45,45);y=frng.uniform(-41,31)
    if (-29<x<29 and 1<y<20) or (abs(x)<17 and -35<y<2) or (17<x<28 and -24<y<17):continue
    h=frng.uniform(.35,.95)
    for j in range(6):
        a=j*math.pi/3+frng.random()*.2;dx=math.cos(a);dy=math.sin(a)
        k=len(fern_v)
        fern_v.extend([(x,y,.03),(x+dx*h*.42-dy*h*.13,y+dy*h*.42+dx*h*.13,h*.65),
                       (x+dx*h,y+dy*h,h*.42),(x+dx*h*.42+dy*h*.13,y+dy*h*.42-dx*h*.13,h*.65)])
        fern_f.extend([(k,k+1,k+2),(k,k+2,k+3)])
        fern_m.extend([i%8,(i+2)%8])
fern=mesh('FernBeds',fern_v,fern_f,None)
for mat in LEAF:fern.data.materials.append(mat)
for p,i in zip(fern.data.polygons,fern_m):p.material_index=i

# A few individually named foliage meshes animate in the web scene.
for i,(x,y) in enumerate([(-17,-20),(17,-24),(29,-10),(-20,-6)]):
    o=ico('Breeze_'+str(i),(x,y,1.1),(1.2,.9,1.4),LEAF[3],2)
    o['breeze']=True

# Festival preparations, restrained warm palette.
category='Festival'
def stall(x,y,index):
    box('StallDeck',(x,y,.15),(4.7,3.6,.22),M['wood'])
    box('StallBack',(x,y+1.5,1.6),(4.3,.15,2.7),M['cream'])
    box('StallCounter',(x,y-.4,1.25),(4.2,1.0,.18),M['wood'])
    box('StallFront',(x,y-.75,.70),(4.0,.13,1.0),M['teal'] if index%2 else M['pink'])
    for dx in (-2.1,2.1):
        for dy in (-1.4,1.4):rod('StallPost',(x+dx,y+dy,.25),(x+dx,y+dy,3.45),.09,M['wood'])
    roof('StallRoof',x,y,5.2,4.4,3.5,.95)
    box('StallSign',(x,y-2.23,2.98),(3.8,.12,.70),M['teal'])
    text('StallLabel',['MAKE / BUILD','DHISHNA','IDEA LAB'][index],(x,y-2.31,2.98),.30,M['white'])
    for j in range(4):
        box('StallCrate',(x-1.3+j*.8,y+.5,1.55),(.5,.5,.45),M['orange'] if j%2 else M['gold'])
for i,y in enumerate((-13,-5,3)):stall(23,y,i)
# Entry banner suspended between poles, with an editable label.
for x in (-7.8,7.8):rod('BannerPole',(x,-30,0),(x,-30,5.5),.065,M['wood'])
box('DhishnaBanner',(0,-30,4.65),(15.5,.10,1.5),M['teal'])
text('DhishnaBannerLabel','D H I S H N A   /   2 0 2 7',(0,-30.075,4.68),.58,M['white'])
# Bunting; flags remain separate for gentle web movement.
def bunting(a,b,count):
    rod('BuntingRope',a,b,.017,M['wood'],6)
    a,b=Vector(a),Vector(b)
    for i in range(count):
        t=(i+1)/(count+1);p=a.lerp(b,t);p.z-=math.sin(t*math.pi)*.45
        o=mesh('Flag_'+str(len(scene.objects)),[(-.32,0,0),(.32,0,0),(0,0,-.7)],[(0,1,2)],M['orange'] if i%3==0 else M['pink'] if i%3==1 else M['gold'])
        o.location=p;o['breeze']=True
bunting((-7.8,-30,5.5),(7.8,-30,5.5),18)
bunting((18,-18,5.2),(29,8,5.2),24)
for x,y in [(18,-18),(29,8)]:rod('BuntingPole',(x,y,0),(x,y,5.3),.06,M['wood'])
# Folding benches and preparation crates.
for x,y in [(-17,-6),(17,-17),(-18,-17)]:
    box('BenchSeat',(x,y,.95),(2.6,.65,.16),M['wood'])
    for dx in (-1,1):box('BenchLeg',(x+dx,y,.5),(.12,.50,.85),M['teal'])
for x,y in [(18,-9),(19,-10),(28,-3)]:
    box('PrepCrate',(x,y,.48),(.85,.85,.9),M['wood'])
    for z in (.18,.45,.72):box('CrateSlat',(x,y-.44,z),(.89,.055,.07),M['gold'])
# Two slim freestanding posters.
for x,y in [(-17,-2),(17,-3)]:
    rod('PosterPole',(x,y,0),(x,y,3.7),.07,M['wood'])
    box('Poster',(x,y,2.9),(1.4,.12,1.7),M['pink'])
    text('PosterType','D / 27',(x,y-.08,3.0),.35,M['white'])

# Small students, posing as preparation crew.
category='Students'
def student(x,y,shirt,angle=0,carrying=False):
    parts=[]
    def b(n,loc,size,mat):
        o=box(n,loc,size,mat);parts.append(o);return o
    for dx in (-.16,.16):
        b('StudentTrouser',(x+dx,y,.46),(.20,.24,.78),M['blue'])
        b('StudentShoe',(x+dx,y-.10,.11),(.22,.40,.16),M['hair'])
    b('StudentShirt',(x,y,1.17),(.64,.38,.64),shirt)
    parts.append(ico('StudentHead',(x,y,1.80),(.26,.24,.29),M['skin'],2))
    parts.append(ico('StudentHair',(x,y+.025,1.97),(.28,.25,.18),M['hair'],2))
    if carrying:
        for dx in (-.38,.38):parts.append(rod('StudentArm',(x+dx,y,1.4),(x+dx,y-.40,1.0),.085,shirt))
        b('CarriedBox',(x,y-.44,1.02),(.62,.55,.52),M['gold'])
    else:
        for dx in (-.38,.38):parts.append(rod('StudentArm',(x+dx,y,1.40),(x+dx,y, .91),.095,shirt))
    for o in parts:
        offset=o.location-Vector((x,y,0))
        o.location.x=x+offset.x*math.cos(angle)-offset.y*math.sin(angle)
        o.location.y=y+offset.x*math.sin(angle)+offset.y*math.cos(angle)
        o.rotation_euler.z+=angle
for x,y,mat,a,c in [(19,-11,M['teal'],-.5,True),(21,-10,M['pink'],.8,False),
                     (18,-4,M['cream'],.3,True),(-5,-6,M['orange'],-.5,False),
                     (-3,-7,M['teal'],.5,False),(8,-26,M['cream'],-.2,True),
                     (27,0,M['pink'],1,False)]:student(x,y,mat,a,c)

# Light and camera: warm, soft morning sun with an elevated reference composition.
category='Lighting'
world=bpy.data.worlds.new('DhishnaDaylight');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.73,.82,.65,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.world=world
ld=bpy.data.lights.new('DhishnaSun','SUN');ld.energy=2.5;ld.angle=.13
sun=bpy.data.objects.new('DhishnaSun',ld);collections[category].objects.link(sun)
sun.rotation_euler=(math.radians(25),math.radians(-25),math.radians(-30))
ld=bpy.data.lights.new('DhishnaSoftbox','AREA');ld.energy=1800;ld.shape='DISK';ld.size=35
fill=bpy.data.objects.new('DhishnaSoftbox',ld);collections[category].objects.link(fill);fill.location=(-25,-35,40)
fill.rotation_euler=(Vector((0,0,0))-fill.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('DhishnaCamera');cd.type='ORTHO';cd.ortho_scale=75
camera=bpy.data.objects.new('DhishnaCamera',cd);collections[category].objects.link(camera)
camera.location=(36,-64,46)
target=Vector((0,-3,3.5))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.render.film_transparent=False
scene.render.filepath=str(ROOT/'public/campus-poster.png')
scene['seed']=SEED
scene['reference']='CUSAT main building photographs provided by user; original stylized geometry'
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.color_type='MATERIAL'
scene.view_layers[0].update()
(ROOT/'assets').mkdir(parents=True,exist_ok=True)
(ROOT/'public/models').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus.blend'),check_existing=False)
# Export optimization: editable source stays intact; temporary static batches reduce draw calls.
def export_web():
    source_objects=list(scene.objects)
    runtime=bpy.data.collections.new('Dhishna_RuntimeExport');scene.collection.children.link(runtime)
    grouped=defaultdict(lambda: [[],[]])
    animated=[]
    # Text is evaluated to meshes using the dependency graph, preserving signage in GLB.
    deps=bpy.context.evaluated_depsgraph_get()
    for o in source_objects:
        if o.type not in {'MESH','FONT'}:continue
        if o.get('breeze'):
            animated.append(o);continue
        evaluated=o.evaluated_get(deps)
        d=evaluated.to_mesh()
        collection=o.users_collection[0].name if o.users_collection else 'Scene'
        for poly in d.polygons:
            mat=d.materials[poly.material_index] if len(d.materials)>poly.material_index else M['cream']
            verts,faces=grouped[(collection,mat.name)]
            k=len(verts)
            verts.extend([tuple(o.matrix_world @ d.vertices[i].co) for i in poly.vertices])
            faces.append(tuple(range(k,k+len(poly.vertices))))
        evaluated.to_mesh_clear()
    exported=[]
    for (collection,matname),(verts,faces) in grouped.items():
        d=bpy.data.meshes.new('Batch_'+collection+'_'+matname);d.from_pydata(verts,[],faces);d.update()
        d.materials.append(bpy.data.materials[matname])
        o=bpy.data.objects.new(d.name,d);runtime.objects.link(o);exported.append(o)
    for o in scene.objects:o.select_set(False)
    for o in exported+animated:o.select_set(True)
    bpy.context.view_layer.objects.active=exported[0]
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'public/models/cusat.glb'),export_format='GLB',
        use_selection=True,use_active_scene=True,export_animations=False,export_cameras=False,
        export_lights=False,export_extras=True,export_texcoords=False,export_materials='EXPORT',
        export_meshopt_compression_enable=True,export_meshopt_extension='EXT_meshopt_compression')
    stats={'seed':SEED,'compression':'EXT_meshopt_compression','sourceObjects':len(source_objects),'runtimeMeshes':len(exported)+len(animated),
           'triangles':sum(len(p.vertices)-2 for o in exported+animated for p in o.data.polygons),
           'glbBytes':(ROOT/'public/models/cusat.glb').stat().st_size,
           'camera':{'position':[36,46,64],'target':[0,3.5,3],'horizontalSpan':75}}
    for o in exported:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(data)
    bpy.data.collections.remove(runtime)
    for o in source_objects:o.select_set(False)
    bpy.context.view_layer.objects.active=camera;camera.select_set(True)
    (ROOT/'public/models/scene-info.json').write_text(json.dumps(stats,indent=2))
    return stats
stats=export_web()
result={'scene':scene.name,'stats':stats,'blend':str(ROOT/'assets/dhishna-campus.blend')}
