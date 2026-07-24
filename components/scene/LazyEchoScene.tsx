"use client";

import dynamic from "next/dynamic";

const EchoScene = dynamic(
  () => import("@/components/scene/EchoScene").then((module) => module.EchoScene),
  {
    ssr: false,
    loading: () => <div className="scene-shell" aria-label="3D 场景正在准备" />,
  },
);

export function LazyEchoScene() {
  return <EchoScene />;
}
