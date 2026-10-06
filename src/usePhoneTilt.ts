import { useCallback, useEffect, useState } from 'react';
import type { RefObject } from 'react';
import { tiltPointer } from './scene-policy';
import type { TiltSample } from './scene-policy';

type OrientationAPI = typeof DeviceOrientationEvent & {
  requestPermission?: () => Promise<'granted' | 'denied'>;
};
type Permission = 'unavailable' | 'prompt' | 'requesting' | 'granted' | 'denied';

function orientationAPI(): OrientationAPI | null {
  if (!window.isSecureContext || typeof window.DeviceOrientationEvent === 'undefined') return null;
  return window.DeviceOrientationEvent as OrientationAPI;
}

export function usePhoneTilt(enabled: boolean, active: boolean, pointer: RefObject<[number, number]>) {
  const [permission, setPermission] = useState<Permission>(() => {
    const api = orientationAPI();
    return !api ? 'unavailable' : typeof api.requestPermission === 'function' ? 'prompt' : 'granted';
  });

  const requestPermission = useCallback(async () => {
    const api = orientationAPI();
    if (!enabled || permission !== 'prompt' || !api?.requestPermission) return;
    setPermission('requesting');
    try {
      // Call directly from the tap handler: Safari requires user activation.
      setPermission(await api.requestPermission());
    } catch {
      setPermission('denied');
    }
  }, [enabled, permission]);

  useEffect(() => {
    if (!enabled || !active || permission !== 'granted') return;
    let origin: TiltSample | null = null;
    let initialAngle: number | null = null;
    const recenter = () => { origin = null; initialAngle = null; pointer.current = [0, 0]; };
    const onOrientation = (event: DeviceOrientationEvent) => {
      if (event.beta === null || event.gamma === null || !Number.isFinite(event.beta) || !Number.isFinite(event.gamma)) return;
      const legacyAngle = (window as Window & { orientation?: number }).orientation;
      const angle = window.screen.orientation?.angle ?? legacyAngle ?? 0;
      const sample = { beta: event.beta, gamma: event.gamma };
      if (!origin || initialAngle !== angle) { origin = sample; initialAngle = angle; }
      pointer.current = tiltPointer(sample, origin, angle);
    };
    window.addEventListener('deviceorientation', onOrientation, { passive: true });
    window.addEventListener('orientationchange', recenter);
    window.screen.orientation?.addEventListener('change', recenter);
    return () => {
      window.removeEventListener('deviceorientation', onOrientation);
      window.removeEventListener('orientationchange', recenter);
      window.screen.orientation?.removeEventListener('change', recenter);
      pointer.current = [0, 0];
    };
  }, [enabled, active, permission, pointer]);

  return {
    state: !enabled ? 'off' : permission === 'granted' ? (active ? 'listening' : 'idle') : permission,
    requestPermission,
  };
}
