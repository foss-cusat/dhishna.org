
import { Component, Suspense, useEffect, useMemo, useRef } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { ACESFilmicToneMapping, Color, DoubleSide, SRGBColorSpace, Mesh, Matrix3, MeshStandardMaterial, OrthographicCamera, Vector3, Vector4 } from 'three';
import { MODEL_URLS } from './model-assets';
import { CAMERA_POSITION, CAMERA_TARGET, cameraSpan } from './scene-policy';

type Props = {
  animate: boolean;
  compact: boolean;
  bottomAligned: boolean;
  pointer: React.RefObject<[number, number]>;
  onReady: () => void;
  onError: () => void;
};

class SceneBoundary extends Component<{ children: ReactNode; onError: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { this.props.onError(); }
  render() { return this.state.failed ? null : this.props.children; }
}

const WIND_VERTEX = `
float campusWeight = _wind_weight;
float campusPhase = dot(vec4(transformed, 1.0), uCampusPhaseBasis);
float campusSpeed = _wind_kind < 1.5 ? 1.7 : 0.785398;
float campusWave = sin(uCampusTime * campusSpeed + campusPhase);
vec3 campusWind = _wind_kind < 1.5
  ? vec3(0.0, 0.004 * campusWave, -0.065 * campusWave)
  : vec3(0.075 * campusWave, -0.009 * abs(campusWave), 0.04 * campusWave);
campusWind *= campusWeight;
// Mesh transforms are static; invert them once on the CPU rather than for every leaf vertex.
transformed += uCampusWorldToLocal * campusWind;
`;

function Scene({ animate, compact, bottomAligned, pointer, onReady }: Omit<Props, 'onError'>) {
  const path = compact ? MODEL_URLS.mobile : MODEL_URLS.desktop;
  const gltf = useLoader(GLTFLoader, path, (loader) => loader.setMeshoptDecoder(MeshoptDecoder));
  const { camera, size, invalidate, gl, setDpr } = useThree();
  const elapsed = useRef(0);
  const readyFrame = useRef(false);
  const counters = useRef({frames:0,last:0});
  const captureCounters = () => {
    const canvas=gl.domElement;
    canvas.dataset.drawCalls=String(gl.info.render.calls);
    canvas.dataset.triangles=String(gl.info.render.triangles);
    canvas.dataset.frames=String(counters.current.frames);
    canvas.dataset.gpuWind='rooted';
    canvas.dataset.profile=compact?'mobile':'desktop';
    canvas.dataset.cameraX=camera.position.x.toFixed(3);
    canvas.dataset.cameraY=camera.position.y.toFixed(3);
    const ortho = camera as OrthographicCamera;
    canvas.dataset.cameraWidth=(ortho.right-ortho.left).toFixed(3);
  };
  const sample = useRef({ elapsed: 0, frames: 0, settled: false });
  const windTime = useMemo(() => ({ value: 0 }), [gltf]);
  const home = useMemo(() => new Vector3(...CAMERA_POSITION), []);
  const look = useMemo(() => new Vector3(...CAMERA_TARGET), []);
  const destination = useMemo(() => new Vector3(), []);

  useMemo(() => {
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((node) => {
      if (!(node instanceof Mesh)) return;
      const wind = !!node.geometry.getAttribute('_wind_weight');
      // Tiny animated foliage does not need another high-density shadow pass.
      node.castShadow = !wind;
      node.receiveShadow = true;
      node.frustumCulled = true;
      if (!wind) return;
      const originals = Array.isArray(node.material) ? node.material : [node.material];
      const materials = originals.map((source) => {
        if (!(source instanceof MeshStandardMaterial)) return source;
        const material=source.clone();
        // The meadow uses vertex colours; tint its white multiplier to keep sunlit
        // blades green instead of pale cream under the illustrated daylight.
        if (source.name === 'V3_LeafyMeadow') material.color.setRGB(.62, .82, .40);
        return material;
      });
      node.material=Array.isArray(node.material)?materials:materials[0];
      const model=new Matrix3().setFromMatrix4(node.matrixWorld);
      const worldToLocal=model.clone().invert();
      const phaseAxis=new Vector3(.19,0,.11).applyMatrix3(model.clone().transpose());
      const origin=new Vector3().setFromMatrixPosition(node.matrixWorld);
      const phaseBasis=new Vector4(phaseAxis.x,phaseAxis.y,phaseAxis.z,origin.x*.19+origin.z*.11);
      materials.forEach((material) => {
        if (!(material instanceof MeshStandardMaterial)) return;
        material.side = DoubleSide;
        material.customProgramCacheKey = () => 'dhishna-rooted-wind-v5';
        material.onBeforeCompile = (shader) => {
          shader.uniforms.uCampusTime = windTime;
          shader.uniforms.uCampusWorldToLocal={value:worldToLocal};
          shader.uniforms.uCampusPhaseBasis={value:phaseBasis};
          shader.vertexShader = 'uniform float uCampusTime;\nuniform mat3 uCampusWorldToLocal;\nuniform vec4 uCampusPhaseBasis;\nattribute float _wind_weight;\nattribute float _wind_kind;\n' + shader.vertexShader;
          shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n' + WIND_VERTEX);
        };
        material.needsUpdate = true;
      });
      node.geometry.computeBoundingBox();
      node.geometry.computeBoundingSphere();
      if (node.geometry.boundingSphere) node.geometry.boundingSphere.radius *= 1.02;
    });
  }, [gltf, windTime]);

  useEffect(() => {
    const ortho = camera as OrthographicCamera;
    const span = cameraSpan(size.width, size.height, bottomAligned);
    const aspect = size.width / Math.max(size.height, 1);
    ortho.left = -span * aspect / 2; ortho.right = span * aspect / 2;
    // Keep the campus against the lower edge when a tall phone gives the scene more room.
    const baseHeight = size.width <= 456 ? 365 : 410;
    const bottomSpan = bottomAligned ? cameraSpan(size.width, Math.min(size.height, baseHeight), true) : span;
    ortho.bottom = -bottomSpan / 2; ortho.top = ortho.bottom + span;
    ortho.near = .1; ortho.far = 250;
    ortho.position.copy(home); ortho.lookAt(look); ortho.updateProjectionMatrix();
    invalidate();
  }, [camera, size, home, look, invalidate, bottomAligned]);

  useEffect(() => {
    readyFrame.current = false;
    sample.current = { elapsed: 0, frames: 0, settled: false };
    gl.shadowMap.needsUpdate = true;
    invalidate();
  }, [gltf, gl, invalidate]);

  // Demand rendering means paused, hidden and offscreen scenes draw no continuous frames.
  useEffect(() => {
    if (!animate) { invalidate(); return; }
    const timer = window.setInterval(invalidate, 1000 / (compact ? 30 : 45));
    return () => window.clearInterval(timer);
  }, [animate, compact, invalidate]);

  useFrame((_, delta) => {
    counters.current.frames++;
    const now=window.performance.now();
    if(now-counters.current.last>1000){captureCounters();counters.current.last=now;}
    if (!readyFrame.current) {
      readyFrame.current = true;
      requestAnimationFrame(() => {captureCounters();onReady();});
    }
    if (!animate) return;
    elapsed.current += Math.min(delta, .10);
    windTime.value = elapsed.current;
    destination.copy(home);
    destination.x += pointer.current[0] * (compact ? 1.8 : 1.2);
    destination.y += pointer.current[1] * (compact ? .9 : .6);
    camera.position.lerp(destination, 1 - Math.exp(-Math.min(delta, .1) * 3));
    camera.lookAt(look);
    const performance = sample.current;
    if (!performance.settled) {
      performance.frames++; performance.elapsed += Math.min(delta, 1);
      if (performance.frames >= 12 && performance.elapsed > 2.5) {
        if (performance.elapsed / performance.frames > .055) setDpr(compact ? .9 : .75);
        performance.settled = true;
      }
    }
  });

  return <>
    <color attach="background" args={['#c8d1a8']} />
    <fog attach="fog" args={['#c8d1a8', 125, 215]} />
    {/* Directional daylight and restrained sky fill preserve depth in the foliage. */}
    <hemisphereLight args={[new Color(.92, .97, .84), new Color(.27, .35, .13), 1.5]} />
    <ambientLight intensity={.12} />
    <directionalLight
      position={[-32.1493, 49.2106, 12.0311]} color="#fff8eb" intensity={3.5} castShadow
      shadow-mapSize={compact ? [1024, 1024] : [2048, 2048]}
      shadow-camera-left={-56} shadow-camera-right={56}
      shadow-camera-top={52} shadow-camera-bottom={-52}
      shadow-camera-near={1} shadow-camera-far={145}
      shadow-bias={-.0004} shadow-normalBias={.08}
    />
    <primitive object={gltf.scene} />
  </>;
}

export default function Campus(props: Props) {
  return <SceneBoundary onError={props.onError}>
    <Canvas orthographic shadows
      camera={{ position: [...CAMERA_POSITION], near: .1, far: 250, manual: true }}
      dpr={[1, props.compact ? 1.25 : 1.5]}
      frameloop="demand"
      gl={{ antialias: true, alpha: false, powerPreference: props.compact ? 'low-power' : 'high-performance' }}
      onCreated={({ gl }) => {
        // Rich daylight grading for the illustrated campus; textures retain their authored sRGB colours.
        gl.toneMapping = ACESFilmicToneMapping; gl.toneMappingExposure = 1.0;
        gl.outputColorSpace = SRGBColorSpace;
        gl.shadowMap.autoUpdate = false; gl.shadowMap.needsUpdate = true;
        gl.domElement.setAttribute('aria-hidden', 'true');
        gl.domElement.addEventListener('webglcontextlost', props.onError, { once: true });
      }} fallback={null}>
      <Suspense fallback={null}><Scene {...props} /></Suspense>
    </Canvas>
  </SceneBoundary>;
}
