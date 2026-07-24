"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";

function EchoCore() {
  const coreRef = useRef<Mesh>(null);

  useFrame((state, delta) => {
    if (!coreRef.current) return;
    coreRef.current.rotation.x += delta * 0.12;
    coreRef.current.rotation.y += delta * 0.18;
    coreRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.65) * 0.08;
  });

  return (
    <mesh ref={coreRef}>
      <icosahedronGeometry args={[1.45, 3]} />
      <meshPhysicalMaterial
        color="#a7ff5f"
        emissive="#335f18"
        emissiveIntensity={0.7}
        metalness={0.35}
        roughness={0.22}
        transmission={0.18}
        wireframe
      />
    </mesh>
  );
}

export function EchoScene() {
  return (
    <div className="scene-shell" aria-label="Echo 智能核心 3D 场景占位">
      <Canvas camera={{ position: [0, 0, 5], fov: 42 }} dpr={[1, 1.5]}>
        <ambientLight intensity={1.5} />
        <directionalLight position={[3, 4, 5]} intensity={2.5} color="#ffffff" />
        <pointLight position={[-3, -2, 2]} intensity={3} color="#63a8ff" />
        <EchoCore />
      </Canvas>
    </div>
  );
}
