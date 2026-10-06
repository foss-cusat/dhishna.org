
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { compactPrimitive, dedup, prune, weld, flatten, join, resample, meshopt, simplifyPrimitive } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';
import sharp from 'sharp';
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready, MeshoptSimplifier.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder,
});
const author = JSON.parse(await readFile('assets/model-v2-info.json', 'utf8'));
const sourceBytes = (await stat('assets/cusat-detailed.glb')).size;
const sourceCamera = { position:[34,43,62], target:[0,4,4], horizontalSpan:73 };

function vector(a, i) { const n=a.getElementSize(); return [...a.getArray().slice(i*n,i*n+n)]; }
function normal(a,b,c) {
  const u=b.map((v,i)=>v-a[i]), v=c.map((n,i)=>n-a[i]);
  const n=[u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
  const l=Math.hypot(...n)||1; return n.map(v=>v/l);
}
function simplifyGrass(doc, primitive, keep, stats) {
  const position=primitive.getAttribute('POSITION'), indices=primitive.getIndices().getArray();
  const color=primitive.getAttribute('COLOR_0');
  // Reconnect split normal vertices by position to identify individual blades.
  const map=new Map(), unique=[], vertexId=new Uint32Array(position.getCount());
  for(let i=0;i<position.getCount();i++) {
    const p=vector(position,i), key=p.join(',');
    let id=map.get(key);
    if(id===undefined) { id=unique.length; map.set(key,id); unique.push({p,index:i}); }
    vertexId[i]=id;
  }
  const parents=Uint32Array.from(unique,(_,i)=>i);
  function find(i) { while(parents[i]!==i) {parents[i]=parents[parents[i]];i=parents[i];}return i; }
  function union(a,b){a=find(a);b=find(b);if(a!==b)parents[b]=a;}
  for(let i=0;i<indices.length;i+=3) {union(vertexId[indices[i]],vertexId[indices[i+1]]);union(vertexId[indices[i]],vertexId[indices[i+2]]);}
  const islands=new Map();
  for(let i=0;i<unique.length;i++) {const id=find(i);if(!islands.has(id))islands.set(id,[]);islands.get(id).push(unique[i]);}
  const pos=[], normals=[], colours=[], weights=[], kinds=[], dst=[];
  const isColor=!!color;
  let seed=0;
  for(const leaf of islands.values()) {
    seed++;
    if(leaf.length!==5) continue; // Collapsed apron blades and accidental degenerate islands are removed.
    leaf.sort((a,b)=>a.p[1]-b.p[1]);
    const [r0,r1,m0,m1,tip]=leaf;
    if(tip.p[1] < -.1 || tip.p[1]-r0.p[1]<.05) continue;
    const hash=(Math.sin(r0.p[0]*127.1+r0.p[2]*311.7+seed*.17)*43758.5453)%1;
    if(Math.abs(hash)>keep)continue;
    const root=r0.p.map((v,i)=>(v+r1.p[i])*.5);
    const rootColor=isColor?vector(color,r0.index).map((v,i)=>(v+vector(color,r1.index)[i])*.5):null;
    const data=[[root,rootColor,0],[m0.p,isColor?vector(color,m0.index):null,.35],
                [tip.p,isColor?vector(color,tip.index):null,1],[m1.p,isColor?vector(color,m1.index):null,.35]];
    const a=normal(root,m0.p,tip.p),b=normal(root,tip.p,m1.p);
    const average=a.map((v,i)=>v+b[i]);const length=Math.hypot(...average)||1;
    const leafNormal=average.map(v=>v/length);
    for(const tri of [[0,1,2],[0,2,3]]) {
      let n=leafNormal;
      // Both folded faces should point towards the front/sky for soft lighting.
      if(n[1]<0)n=n.map(v=>-v);
      for(const i of tri) {
        dst.push(pos.length/3);pos.push(...data[i][0]);normals.push(...n);
        if(isColor)colours.push(...data[i][1]);
        weights.push(data[i][2]);kinds.push(2);
      }
    }
    stats.grassBlades++;stats.rootVertices+=2;
  }
  assert(pos.length>0, 'Grass conversion produced no blades');
  for(const semantic of primitive.listSemantics())primitive.setAttribute(semantic,null);
  for(const target of [...primitive.listTargets()])primitive.removeTarget(target);
  const buffer=doc.getRoot().listBuffers()[0];
  function attr(name,type,array) {return doc.createAccessor(name).setType(type).setArray(array).setBuffer(buffer);}
  primitive.setAttribute('POSITION',attr('grass-position','VEC3',new Float32Array(pos)));
  primitive.setAttribute('NORMAL',attr('grass-normal','VEC3',new Float32Array(normals)));
  if(isColor)primitive.setAttribute('COLOR_0',attr('grass-colour',color.getType(),new Float32Array(colours)));
  primitive.setAttribute('_WIND_WEIGHT',attr('rooted-wind-weight','SCALAR',new Float32Array(weights)));
  primitive.setAttribute('_WIND_KIND',attr('rooted-wind-kind','SCALAR',new Float32Array(kinds)));
  primitive.setIndices(attr('grass-index','SCALAR',new Uint32Array(dst)));
}

async function optimize(profile) {
  const compact=profile==='mobile';
  const doc=await io.read('assets/cusat-detailed.glb');
  for(const ext of doc.getRoot().listExtensionsUsed()) {
    if(ext.extensionName==='EXT_meshopt_compression')ext.dispose();
  }
  const stats={profile,sourceBytes,sourceTriangles:author.triangles,grassBlades:0,rootVertices:0,windMeshes:0};
  for(const node of doc.getRoot().listNodes()) {
    const mesh=node.getMesh();if(!mesh)continue;
    const kind=node.getExtras().wind_kind;
    for(const primitive of mesh.listPrimitives()) {
      if(kind==='grass' && node.getExtras().continuous_groundcover) {
        simplifyGrass(doc,primitive,compact?.62:1,stats);stats.windMeshes++;
      } else if(primitive.listTargets().length) {
        const target=primitive.listTargets()[0].getAttribute('POSITION'), values=target.getArray();
        const weights=new Float32Array(target.getCount());
        let max=0;for(let i=0;i<weights.length;i++){weights[i]=Math.hypot(values[i*3],values[i*3+1],values[i*3+2]);max=Math.max(max,weights[i]);}
        for(let i=0;i<weights.length;i++)weights[i]/=max||1;
        const buffer=doc.getRoot().listBuffers()[0];
        primitive.setAttribute('_WIND_WEIGHT',doc.createAccessor().setType('SCALAR').setArray(weights).setBuffer(buffer));
        primitive.setAttribute('_WIND_KIND',doc.createAccessor().setType('SCALAR').setArray(new Float32Array(weights.length).fill(kind==='flag'?1:kind==='grass'?2:3)).setBuffer(buffer));
        for(const t of [...primitive.listTargets()])primitive.removeTarget(t);
        stats.windMeshes++;
      }
    }
    node.setWeights([]);mesh.setWeights([]);
  }
  // The authoring clip remains in .blend. The browser uses anchored vertex wind instead of per-frame morph uploads.
  for(const a of [...doc.getRoot().listAnimations()]) {
    for(const c of [...a.listChannels()]) {c.setTargetNode(null);c.dispose();}
    for(const sampler of [...a.listSamplers()])sampler.dispose();
    a.dispose();
  }
  for(const mesh of doc.getRoot().listMeshes())for(const p of mesh.listPrimitives()) {
    const m=p.getMaterial();
    if(m&&!m.getBaseColorTexture()&&!m.getNormalTexture()&&!m.getMetallicRoughnessTexture()) {
      p.setAttribute('TEXCOORD_0',null);p.setAttribute('TANGENT',null);
    }
  }
  await doc.transform(prune(), dedup(), weld());
  for(const mesh of doc.getRoot().listMeshes()) {
    if(mesh.getName().includes('Grass')||mesh.getName().includes('Meadow'))continue;
    for(const p of mesh.listPrimitives()) {
      if(p.getAttribute('_WIND_WEIGHT'))continue;
      simplifyPrimitive(p,{simplifier:MeshoptSimplifier,ratio:compact?.45:.70,error:compact?.0005:.00015,lockBorder:false});
    }
  }
  // Join compatible materials after baking node transforms. Wind remains spatially varied in the shader.
  await doc.transform(flatten(),join({keepNamed:false}),prune(),dedup(),resample());
  for(const texture of doc.getRoot().listTextures()) {
    const size=compact?512:1024;
    const data=await sharp(texture.getImage()).resize({width:size,height:size,fit:'inside',withoutEnlargement:true}).webp({quality:compact?78:86,effort:6}).toBuffer();
    texture.setImage(data).setMimeType('image/webp');
  }
  const { EXTTextureWebP }=await import('@gltf-transform/extensions');
  doc.createExtension(EXTTextureWebP).setRequired(true);
  await doc.transform(meshopt({encoder:MeshoptEncoder,level:'high',quantizePosition:compact?12:13,quantizeNormal:8,quantizeTexcoord:12,quantizeColor:8,quantizeGeneric:8}));
  stats.triangles=doc.getRoot().listMeshes().reduce((n,m)=>n+m.listPrimitives().reduce((s,p)=>s+(p.getIndices()?.getCount()??p.getAttribute('POSITION').getCount())/3,0),0);
  stats.runtimeMeshes=doc.getRoot().listMeshes().length;
  stats.drawCalls=doc.getRoot().listMeshes().reduce((n,m)=>n+m.listPrimitives().length,0);
  stats.textureBytes=doc.getRoot().listTextures().reduce((n,t)=>n+t.getImage().byteLength,0);
  stats.textures=doc.getRoot().listTextures().map(t=>({name:t.getName(),size:t.getSize(),bytes:t.getImage().byteLength}));
  stats.wind='GPU vertex displacement with zero-weight roots; authoring animation retained in Blender';
  stats.compression=['EXT_meshopt_compression','KHR_mesh_quantization','EXT_texture_webp'];
  stats.camera=sourceCamera;
  stats.landmarks={cusatGate:true,centralStatue:true,extraTrees:13,statueScale:1.25,facadeWeathering:true,raisedRoofTiles:true};
  const output='public/models/'+(compact?'cusat-mobile.glb':'cusat.glb');
  await io.write(output,doc);stats.glbBytes=(await stat(output)).size;
  stats.hash=createHash('sha256').update(await readFile(output)).digest('hex').slice(0,12);
  stats.byteReductionPercent=Number((100*(1-stats.glbBytes/sourceBytes)).toFixed(1));
  await writeFile('public/models/'+(compact?'scene-info-mobile.json':'scene-info.json'),JSON.stringify(stats,null,2));
  console.log(profile+': '+(stats.glbBytes/1e6).toFixed(2)+' MB, '+stats.triangles.toLocaleString()+' triangles, '+stats.drawCalls+' draw calls');
  return stats;
}
await mkdir('public/models',{recursive:true});
const desktop=await optimize('desktop');
const mobile=await optimize('mobile');
await writeFile('artifacts/optimization-report.json',JSON.stringify({desktop,mobile},null,2));

await writeFile('src/model-assets.ts','/* Generated by scripts/optimize-model.mjs. */\nexport const MODEL_URLS = '+JSON.stringify({desktop:'/models/cusat.glb?v='+desktop.hash,mobile:'/models/cusat-mobile.glb?v='+mobile.hash},null,2)+' as const;\n');
