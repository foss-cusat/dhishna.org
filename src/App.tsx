import { lazy, Suspense, useCallback, useRef, useState } from 'react';
import { useMediaQuery, usePageVisible, useSceneVisible } from './hooks';
import { boundedPointer, shouldAnimate } from './scene-policy';
import { usePhoneTilt } from './usePhoneTilt';

const Campus = lazy(() => import('./Campus'));

function Spark({ className = '' }: { className?: string }) {
  return <svg className={className} width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
    <path d="M14 0 16.7 9.3 24 4 18.7 11.3 28 14 18.7 16.7 24 24 16.7 18.7 14 28 11.3 18.7 4 24 9.3 16.7 0 14 9.3 11.3 4 4 11.3 9.3Z" fill="currentColor" />
  </svg>;
}

export default function App() {
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  const finePointer = useMediaQuery('(hover: hover) and (pointer: fine)');
  const visible = usePageVisible();
  const saveData = (navigator as Navigator & {connection?: {saveData?: boolean}}).connection?.saveData === true;
  const compact = useMediaQuery('(max-width: 700px), (max-width: 1100px) and (max-height: 600px), (pointer: coarse)');
  const mobileLayout = useMediaQuery('(max-width: 700px), (max-width: 1100px) and (max-height: 600px)');
  const stageRef = useRef<HTMLDivElement>(null);
  const sceneVisible = useSceneVisible(stageRef);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const pointer = useRef<[number, number]>([0, 0]);
  const animate = shouldAnimate(reduced, visible && sceneVisible);
  const tilt = usePhoneTilt(compact && !reduced && ready && !failed && !saveData, visible && sceneVisible, pointer);
  const onReady = useCallback(() => setReady(true), []);
  const onError = useCallback(() => { setFailed(true); setReady(false); }, []);

  return <main className="landing" data-mobile-layout={mobileLayout}
    onPointerMove={(event) => {
      if (compact || !finePointer || event.pointerType === 'touch') return;
      const box = event.currentTarget.getBoundingClientRect();
      pointer.current = boundedPointer((event.clientX - box.left) / box.width * 2 - 1, (event.clientY - box.top) / box.height * 2 - 1);
    }}
    onPointerLeave={() => { if (!compact && finePointer) pointer.current = [0, 0]; }}
  >
    <a className="skip-link" href="#welcome">Skip to welcome</a>
    <header className="header">
      <a className="brand" href="#welcome" aria-label="Dhishna 2027 home">
        <span className="brand-symbol"><Spark /></span>
        <span className="brand-name">dhishna<span className="brand-year">/27</span></span>
      </a>
      <div className="header-right">
        <span className="university"><span className="tiny-dot" /> KOCHI</span>
      </div>
    </header>

    <section className="hero-copy" id="welcome" aria-labelledby="hero-title">
      <div className="eyebrow"><span className="eyebrow-line" /> CUSAT’S TECH FEST <span className="eyebrow-year">2027</span></div>
      <h1 id="hero-title">Something's<br /><span className="alive">brewing<Spark className="headline-spark" /></span></h1>
      <div className="date-location">
        <div className="date"><span className="date-month">JANUARY</span><span className="date-year">2027</span></div>
      </div>
    </section>

    <div ref={stageRef} className={'campus-stage' + (ready && !failed ? ' is-ready' : '')}
      role="img"
      aria-label="A low-poly CUSAT campus in warm daylight, with twin pink towers, the arched university gate, a central Kathakali statue, lush gardens, and Dhishna festival preparations."
      data-scene-state={failed || saveData ? 'fallback' : ready ? 'ready' : 'loading'}
      data-tilt-state={tilt.state}
    >
      <picture className="campus-poster">
        <source srcSet="/campus-poster.webp" type="image/webp" />
        <img src="/campus-poster.png" alt="" fetchPriority="high" />
      </picture>
      {!failed && !saveData && <div className="campus-canvas">
        <Suspense fallback={null}>
          <Campus animate={animate} compact={compact} bottomAligned={mobileLayout} pointer={pointer} onReady={onReady} onError={onError} />
        </Suspense>
      </div>}
      <div className="scene-blend" />
    </div>


    <div className="scene-caption" aria-hidden="true">
      <span className="caption-mark">↗</span><span>A FAMILIAR PLACE.<br /><strong>A WHOLE NEW CHAPTER.</strong></span>
    </div>

    {(tilt.state === 'prompt' || tilt.state === 'requesting') && <button
      className="tilt-control" type="button" onClick={tilt.requestPermission}
      disabled={tilt.state === 'requesting'}
    >{tilt.state === 'requesting' ? 'Enabling tilt…' : 'Enable tilt'}</button>}
    {tilt.state === 'denied' && <span className="tilt-control tilt-status" role="status">Tilt is unavailable</span>}

    <footer className="footer">
      <span className="footer-message">Made of curiosity. <span>Rooted in CUSAT.</span></span>
    </footer>
  </main>;
}
