
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import sharp from 'sharp';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import { boundedPointer, cameraSpan, shouldAnimate, tiltPointer } from '../src/scene-policy.ts';

test('responsive camera and bounded motion respect stop conditions', () => {
  for (const [width,height] of [[1440,900],[1024,768],[468,410],[432,365]]) {
    const span=cameraSpan(width,height);
    assert(Number.isFinite(span) && span>=39);
    assert(span*width/height>=60);
  }
  assert.deepEqual(boundedPointer(5,-3),[1,-1]);
  assert(shouldAnimate(false,true));
  for (const args of [[true,true],[true,false],[false,false]])assert(!shouldAnimate(...args));
});
test('desktop and mobile assets retain textured landmarks and rooted wind within web budgets', async () => {
  await MeshoptDecoder.ready;
  const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
  for(const [name,budget,triBudget] of [['cusat',12*1024*1024,650000],['cusat-mobile',8*1024*1024,480000]]) {
    const path='public/models/'+name+'.glb',file=readFileSync(path);
    assert.equal(file.toString('utf8',0,4),'glTF');assert.equal(file.readUInt32LE(8),file.length);
    assert(file.length<budget, name+' byte budget');
    const info=JSON.parse(readFileSync('public/models/'+(name==='cusat'?'scene-info':'scene-info-mobile')+'.json','utf8'));
    assert(info.triangles<triBudget, name+' triangle budget');
    assert(info.drawCalls<130, name+' draw-call budget');
    assert(info.landmarks.cusatGate && info.landmarks.centralStatue && info.landmarks.facadeWeathering && info.landmarks.raisedRoofTiles);
    assert.equal(info.landmarks.statueScale,1.25);
    const doc=await io.read(path);
    const mats=doc.getRoot().listMaterials();
    assert(mats.some(m=>m.getName().startsWith('Gate_')));
    const weather=mats.filter(m=>m.getName().startsWith('V4_Weathered_'));
    assert.equal(weather.length,4);
    weather.forEach(m=>assert(m.getBaseColorTexture()&&m.getNormalTexture()&&m.getMetallicRoughnessTexture()));
    // A previous packed-image export retained dark, stale PNGs while Blender showed
    // the updated files. Check colour fidelity independently of the render settings.
    for (const key of ['road', 'path', 'grass', 'Roof0', 'Roof3', 'Roof5']) {
      const mat=mats.find(m=>m.getName()==='V2_D_'+key);
      assert(mat?.getBaseColorTexture(), 'Authored colour map: '+key);
      const actual=await sharp(mat.getBaseColorTexture().getImage()).stats();
      const source=await sharp('assets/textures/V2_'+key+'_color.png').stats();
      for(let channel=0;channel<3;channel++) {
        assert(Math.abs(actual.channels[channel].mean-source.channels[channel].mean)<3,
          name+' preserves source texture colours: '+key+' channel '+channel);
      }
    }
    let roots=0,tips=0;
    for(const mesh of doc.getRoot().listMeshes())for(const p of mesh.listPrimitives()) {
      const wind=p.getAttribute('_WIND_WEIGHT');
      if(!wind)continue;
      assert(p.getAttribute('_WIND_KIND'));
      for(const value of wind.getArray()) {
        assert(value>=0 && value<=1);
        if(value===0)roots++;
        if(value===1)tips++;
      }
      assert.equal(p.listTargets().length,0,'GPU wind replaces costly morph uploads');
    }
    assert(roots>20000 && tips>20000,'Dense, rooted foliage is retained');
    doc.getRoot().listTextures().forEach(t=>assert(Math.max(...t.getSize())<=(name==='cusat'?1024:512)));
  }
  assert(existsSync('assets/dhishna-campus-detailed.blend'));
  assert(existsSync('public/campus-poster.webp'));
});

test('phone tilt is relative, bounded, noise-resistant, and follows screen rotation', () => {
  const origin={beta:48,gamma:4};
  assert.deepEqual(tiltPointer(origin,origin),[0,0]);
  assert.deepEqual(tiltPointer({beta:48.2,gamma:4.3},origin),[0,0]);
  const portrait=tiltPointer({beta:48,gamma:22},origin);
  assert.equal(portrait[0],1);assert.equal(portrait[1],0);
  const landscape=tiltPointer({beta:48,gamma:22},origin,90);
  assert(Math.abs(landscape[0])<1e-10);assert.equal(landscape[1],-1);
  assert.deepEqual(tiltPointer({beta:-90,gamma:80},origin),[1,-1]);
  const wrapped=tiltPointer({beta:-179,gamma:0},{beta:179,gamma:0});
  assert(wrapped[1]>0 && wrapped[1]<.1,'Crossing 180 degrees does not cause a full camera jump');
  assert.deepEqual(tiltPointer({beta:NaN,gamma:Infinity},origin),[0,0]);
});
