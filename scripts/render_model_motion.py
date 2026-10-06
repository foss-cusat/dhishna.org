
import bpy,pathlib,subprocess,json
root=pathlib.Path('/home/rishi/devmt/dhishna.org')
s=bpy.data.scenes['Dhishna_Campus_Detailed'];bpy.context.window.scene=s
frames=root/'artifacts/model-v2/motion-frames';frames.mkdir(exist_ok=True)
old=(s.camera,s.render.resolution_x,s.render.resolution_y,s.cycles.samples,s.render.filepath)
try:
    s.camera=s.objects['GardenCloseup']
    s.render.resolution_x=800;s.render.resolution_y=500;s.cycles.samples=8
    for i in range(32):
        s.frame_set(1+round(i*240/32))
        s.render.filepath=str(frames/('frame-%03d.png'%i))
        bpy.ops.render.render(write_still=True)
    dest=root/'artifacts/model-v2/grass-breeze.mp4'
    process=subprocess.run(['ffmpeg','-y','-framerate','4','-i',str(frames/'frame-%03d.png'),
                            '-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-movflags','+faststart',str(dest)],
                           capture_output=True,text=True)
    if process.returncode:raise RuntimeError(process.stderr[-1500:])
    result={'video':str(dest),'seconds':8,'frames':32,'bytes':dest.stat().st_size}
finally:
    s.camera,s.render.resolution_x,s.render.resolution_y,s.cycles.samples,s.render.filepath=old
    s.frame_set(1)
