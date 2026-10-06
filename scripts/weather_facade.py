
"""Image-based plaster weathering, mapped in campus metres rather than tiled per wall."""
import bpy,pathlib,math,json
import numpy as np
import struct,zlib
from mathutils import Vector
ROOT=pathlib.Path('/home/rishi/devmt/dhishna.org')
OUT=ROOT/'assets/textures';OUT.mkdir(exist_ok=True)
s=bpy.data.scenes['Dhishna_Campus_Detailed'];bpy.context.window.scene=s
W,H=2048,1024
X=np.linspace(-29,29,W,dtype=np.float32)[None,:]
Z=np.linspace(0,22,H,dtype=np.float32)[:,None]
rng=np.random.default_rng(271027)
cloud=np.zeros((H,W),np.float32)
for scale,amp in [(1.7,.45),(3.8,.26),(8.5,.17),(19,.08),(40,.04)]:
    phase=rng.uniform(0,6.28,3)
    cloud+=amp*np.sin(X/scale+phase[0])*np.sin(Z/(scale*.73)+phase[1])+amp*.3*np.sin((X+Z*.4)/(scale*.63)+phase[2])
cloud=np.clip((cloud+1.05)/2.1,0,1)
grain=rng.random((H,W),dtype=np.float32)-.5
# Multi-scale random mottling gives the plaster organic marks rather than a wave pattern.
noise_fft=np.fft.fft2(rng.standard_normal((H,W)).astype(np.float32))
fy=np.fft.fftfreq(H)[:,None];fx=np.fft.fftfreq(W)[None,:]
mottle=np.zeros((H,W),np.float32)
for radius,weight in [(3,.24),(13,.36),(48,.40)]:
    filtered=np.fft.ifft2(noise_fft*np.exp(-.5*(math.tau*radius)**2*(fx*fx+fy*fy))).real
    mottle+=(filtered/max(float(filtered.std()),1e-6)*weight).astype(np.float32)
chips=np.clip((mottle-.75)*1.6,0,1)
base_damp=np.exp(-Z/.48)*(.13+.10*cloud)
runoff=np.zeros((H,W),np.float32)
# Eaves and horizontal ledges shelter the wall; runoff trails vary in width and length.
for lo,hi,top in [(-13.6,-7.8,17.6),(7.8,13.6,17.6),(-27,-13.6,10.2),(13.6,27,10.2),(-7.8,7.8,12.7)]:
    for j in range(max(5,int((hi-lo)*1.9))):
        x=rng.uniform(lo,hi);width=rng.uniform(.035,.17);length=rng.uniform(.55,2.9)
        distance=top-Z
        drift=.055*np.sin(Z*1.4+rng.random()*6.28)
        stream=np.exp(-((X-x-drift)/width)**2)*np.exp(-np.maximum(distance,0)/length)
        runoff+=stream*(distance>=0)*rng.uniform(.065,.155)
# Window sill drips follow the actual model's window locations.
for o in bpy.data.collections['V2_Architecture'].objects:
    if not o.name.startswith('V2_WindowFrame'):continue
    corners=[o.matrix_world@Vector(c) for c in o.bound_box]
    lo=min(p.x for p in corners);hi=max(p.x for p in corners);sill=min(p.z for p in corners)
    for x in (lo+.08,hi-.08):
        distance=sill-Z
        runoff+=np.exp(-((X-x)/rng.uniform(.04,.09))**2)*np.exp(-np.maximum(distance,0)/rng.uniform(.35,.95))*(distance>=0)*rng.uniform(.055,.105)
# Thin, irregular worn patches and fine plaster pores.
worn=np.maximum(np.clip((cloud-.66)*3.2,0,1)*(.42+.58*np.clip(grain+.5,0,1)),chips*.8)
dirt=np.clip(base_damp+runoff+.028*cloud+.025*np.maximum(mottle,0),0,.30)
height=grain*.0025+cloud*.002+worn*.004
gz,gx=np.gradient(height)
normal=np.stack([-gx*85,-gz*65,np.ones_like(gx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
rough=np.clip(.84+.10*cloud+.07*worn+.035*grain,.76,.98)
def save_image(name,array,noncolor=False):
    # Array row 0 represents the ground; PNG row 0 is the top of the image.
    if array.ndim==2:array=np.repeat(array[:,:,None],3,axis=2)
    path=OUT/(name+'.png');pixels=(np.clip(array[::-1],0,1)*255+.5).astype(np.uint8)
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    header=struct.pack('>IIBBBBB',pixels.shape[1],pixels.shape[0],8,2,0,0,0)
    scanlines=b''.join(b'\x00'+pixels[row].tobytes() for row in range(pixels.shape[0]))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(scanlines,6))+chunk(b'IEND',b''))
    image=bpy.data.images.get(name)
    if image:
        image.filepath=str(path);image.reload()
    else:image=bpy.data.images.load(str(path),check_existing=False);image.name=name
    image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
    image.pack();return image
normal_image=save_image('V4_PlasterWear_Normal',normal*.5+.5,True)
rough_image=save_image('V4_PlasterWear_Roughness',rough,True)
weather={}
for key in ['cream','pink','pinklight','white']:
    original=bpy.data.materials['V2_D_'+key]
    base=np.array(original.diffuse_color[:3],np.float32)
    color=np.broadcast_to(base,(H,W,3)).copy()
    fade=(.022+.06*cloud+.15*worn)[:,:,None]
    faded=np.array([.82,.77,.65],np.float32) if key in ['pink','pinklight'] else np.array([.88,.83,.71],np.float32)
    color=color*(1-fade)+faded*fade
    color=color*(1-dirt[:,:,None])+np.array([.23,.205,.15],np.float32)*dirt[:,:,None]
    # Restrained moss and splash staining only at the lowest part of the facade.
    moss=(np.exp(-Z/.20)*np.clip((cloud-.53)*2.0,0,1)*.085)[:,:,None]
    color=color*(1-moss)+np.array([.18,.22,.095],np.float32)*moss
    color*=1+grain[:,:,None]*.015
    srgb=np.where(color<=.0031308,color*12.92,1.055*np.maximum(color,0)**(1/2.4)-.055)
    color_image=save_image('V4_Weathered_'+key+'_BaseColor',srgb)
    mat=bpy.data.materials.get('V4_Weathered_'+key) or original.copy()
    mat.name='V4_Weathered_'+key;mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled')
    mat.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    for name,img,socket in [('WeatherColour',color_image,'Base Color'),('WeatherRoughness',rough_image,'Roughness')]:
        n=nodes.new('ShaderNodeTexImage');n.name=name;n.image=img;n.extension='EXTEND'
        mat.node_tree.links.new(n.outputs['Color'],bs.inputs[socket])
    tex=nodes.new('ShaderNodeTexImage');tex.name='WeatherNormal';tex.image=normal_image;tex.extension='EXTEND'
    nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.32
    mat.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    mat['weathering']='Faded plaster, eave and window runoff, low damp staining, fine pitting; bitmap atlas.'
    weather['V2_D_'+key]=mat
    weather[mat.name]=mat
targets=[]
s.view_layers[0].update()
for o in bpy.data.collections['V2_Architecture'].objects:
    if o.type!='MESH' or o.hide_render or not any(m and m.name in weather for m in o.data.materials):continue
    for i,m in enumerate(o.data.materials):
        if m and m.name in weather:o.data.materials[i]=weather[m.name]
    if not o.get('weather_uv_backup'):
        layer=o.data.uv_layers.active
        if layer:layer.name='BeforeWeatherUV'
        o['weather_uv_backup']=True
    uv=o.data.uv_layers.get('WeatherUV') or o.data.uv_layers.new(name='WeatherUV')
    uv.active_render=True;o.data.uv_layers.active_index=list(o.data.uv_layers).index(uv)
    for poly in o.data.polygons:
        n=(o.matrix_world.to_3x3()@poly.normal).normalized()
        axis=max(range(3),key=lambda k:abs(n[k]))
        for li in poly.loop_indices:
            p=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
            horizontal=p.x if axis!=0 else o.location.x+p.y-o.location.y
            uv.data[li].uv=((horizontal+29)/58,p.z/22 if axis!=2 else (p.y+18)/58)
    o['image_weathering']=True;targets.append(o.name)
s['facade_weathering_version']=1;s['facade_texture_resolution']='2048 x 1024'
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/dhishna-campus-detailed.blend'),check_existing=False)
result={'weatheredObjects':len(targets),'imageMaps':6,'textureResolution':[W,H],'geometryChanged':False}
