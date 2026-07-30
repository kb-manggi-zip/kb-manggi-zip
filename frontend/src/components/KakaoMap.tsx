// 카카오맵 SDK 연동 — npm 패키지 추가 없이 스크립트 동적 로드(공식 권장 방식).
// VITE_KAKAO_KEY 없으면 조용히 null 반환(기존 placeholder 자리에 아무것도 안 그림, 에러 아님).
import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    kakao: any;
  }
}

let loadPromise: Promise<void> | null = null;

function loadKakaoSdk(appkey: string): Promise<void> {
  if (window.kakao?.maps) return Promise.resolve();
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appkey}&autoload=false`;
    script.onload = () => window.kakao.maps.load(() => resolve());
    script.onerror = () => reject(new Error("카카오맵 SDK 로드 실패"));
    document.head.appendChild(script);
  });
  return loadPromise;
}

export type MapPin = { id: string; name: string; lat: number; lng: number };

/** 여러 동네 후보를 마커로 보여주는 지도. 좌표들이 다 보이게 자동으로 범위를 맞춘다. */
export function KakaoMap({
  pins,
  height = 130,
  className,
}: {
  pins: MapPin[];
  height?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<
    "loading" | "ready" | "error" | "no-key"
  >("loading");
  const key = import.meta.env.VITE_KAKAO_KEY as string | undefined;

  useEffect(() => {
    if (!key) {
      setStatus("no-key");
      return;
    }
    if (!ref.current || pins.length === 0) return;
    let cancelled = false;
    loadKakaoSdk(key)
      .then(() => {
        if (cancelled || !ref.current) return;
        const { kakao } = window;
        const center = new kakao.maps.LatLng(pins[0].lat, pins[0].lng);
        const map = new kakao.maps.Map(ref.current, { center, level: 5 });
        const bounds = new kakao.maps.LatLngBounds();
        pins.forEach((p) => {
          const pos = new kakao.maps.LatLng(p.lat, p.lng);
          // 카카오 기본 마커 핀이 이 작은 지도엔 너무 커서, 작은 점으로 대체.
          const dot = new kakao.maps.CustomOverlay({
            position: pos,
            yAnchor: 0.5,
            content: `<div style="width:9px;height:9px;border-radius:50%;background:#3B82F6;border:1.5px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></div>`,
          });
          dot.setMap(map);
          const info = new kakao.maps.CustomOverlay({
            position: pos,
            yAnchor: 1.3,
            content: `<div style="background:#fff;border-radius:5px;padding:0px 4px;font-size:9px;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,0.15);white-space:nowrap;line-height:1.6;">${p.name}</div>`,
          });
          info.setMap(map);
          bounds.extend(pos);
        });
        if (pins.length > 1) {
          map.setBounds(bounds);
          // 후보 동네가 가까이 모여있으면 너무 확대돼서 이름표가 겹침 — 최소 축소 레벨 보장(숫자 클수록 축소).
          const MIN_LEVEL = 3;
          if (map.getLevel() < MIN_LEVEL) map.setLevel(MIN_LEVEL);
        }
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [key, pins.map((p) => `${p.id}:${p.lat}:${p.lng}`).join(",")]);

  if (status === "no-key" || status === "error") {
    // 키 없거나 로드 실패 시 기존 placeholder 스타일로 조용히 대체(에러 화면 노출 금지)
    return (
      <div
        className={className}
        style={{ height, background: "#E8EDF5", borderRadius: 16 }}
      />
    );
  }
  return (
    <div
      ref={ref}
      className={className}
      style={{ height, borderRadius: 16, overflow: "hidden" }}
    />
  );
}
