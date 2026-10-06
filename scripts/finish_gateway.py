
import bpy,pathlib
from mathutils import Vector
s=bpy.data.scenes['Dhishna_Campus_Detailed']
mat=bpy.data.materials.get('Gate_SignLetterIron') or bpy.data.materials.new('Gate_SignLetterIron')
mat.use_nodes=True;mat.diffuse_color=(.045,.062,.048,1)
p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=mat.diffuse_color;p.inputs['Roughness'].default_value=.85
for o in bpy.data.collections['V3_Gateway'].objects:
    if o.name.startswith('CusatGateLetter_'):
        o.data.materials.clear();o.data.materials.append(mat)
def apron(x,y):
    if not -35.55<y<-27.25:return False
    if y<-31.7:w=4.5+(y+35.4)/3.7*2.57
    elif y<-28.8:w=7.07
    else:w=7.07-(y+28.8)/1.4*2.57
    return abs(x)<w+.12
cleared=0
for o in s.objects:
    if o.hide_render or o.type!='MESH':continue
    if o.get('wind_kind')=='grass':
        keys=o.data.shape_keys.key_blocks
        for i in range(0,len(keys[0].data)-4,5):
            p=o.matrix_world@((keys[0].data[i].co+keys[0].data[i+1].co)*.5)
            if not apron(p.x,p.y):continue
            cleared+=1
            for key in keys:
                for j in range(5):key.data[i+j].co.z=-1
    elif o.name=='FoldedGroundLeaves':
        for v in o.data.vertices:
            p=o.matrix_world@v.co
            if apron(p.x,p.y):v.co.z=-1
s.frame_set(1)
result={'clearedGrassBlades':cleared,'letterContrastImproved':True}
