"use client";

import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { Group, Object3D } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const MODEL_PATH = "/models/echo-core-v1.glb";

function usePrefersReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReducedMotion(mediaQuery.matches);

    updatePreference();
    mediaQuery.addEventListener("change", updatePreference);

    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  return reducedMotion;
}

function LoadingCore() {
  return (
    <mesh>
      <icosahedronGeometry args={[1.05, 2]} />
      <meshBasicMaterial color="#78ead6" wireframe transparent opacity={0.28} />
    </mesh>
  );
}

function EchoCoreModel({ reducedMotion }: { reducedMotion: boolean }) {
  const presentationRef = useRef<Group>(null);
  const animatedPartsRef = useRef<{
    core: Object3D | null;
    shell: Object3D | null;
    nodes: Object3D | null;
    orbits: Object3D[];
  }>({
    core: null,
    shell: null,
    nodes: null,
    orbits: [],
  });
  const gltf = useLoader(GLTFLoader, MODEL_PATH);
  const model = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  useEffect(() => {
    animatedPartsRef.current = {
      core: model.getObjectByName("GRP_Core") ?? null,
      shell: model.getObjectByName("GRP_Shell") ?? null,
      nodes: model.getObjectByName("GRP_Nodes") ?? null,
      orbits: [
        model.getObjectByName("Orbit_01"),
        model.getObjectByName("Orbit_02"),
        model.getObjectByName("Orbit_03"),
      ].filter((object): object is Object3D => Boolean(object)),
    };

    return () => {
      animatedPartsRef.current = {
        core: null,
        shell: null,
        nodes: null,
        orbits: [],
      };
    };
  }, [model]);

  useFrame((state, delta) => {
    if (reducedMotion || !presentationRef.current) return;

    const elapsed = state.clock.elapsedTime;
    const animatedParts = animatedPartsRef.current;
    presentationRef.current.rotation.y += delta * 0.055;
    presentationRef.current.position.y = Math.sin(elapsed * 0.58) * 0.08;

    if (animatedParts.core) {
      animatedParts.core.rotation.y += delta * 0.1;
      animatedParts.core.rotation.z = Math.sin(elapsed * 0.38) * 0.035;
    }

    if (animatedParts.shell) {
      animatedParts.shell.rotation.z = Math.sin(elapsed * 0.3) * 0.025;
    }

    if (animatedParts.nodes) {
      animatedParts.nodes.rotation.y -= delta * 0.035;
    }

    animatedParts.orbits.forEach((orbit, index) => {
      orbit.rotation.z += delta * (0.035 + index * 0.018) * (index === 1 ? -1 : 1);
    });
  });

  return (
    <group
      ref={presentationRef}
      position={[0, -0.04, 0]}
      rotation={[0.18, -0.58, -0.08]}
      scale={0.96}
    >
      <primitive object={model} dispose={null} />
    </group>
  );
}

export function EchoScene() {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <div
      className="scene-shell"
      role="img"
      aria-label="Echo Core 立体装置：发光核心、界面外壳与三条回声轨道组成的 AI 协作系统"
    >
      <Canvas
        aria-hidden="true"
        camera={{ position: [0, 0.12, 7.2], fov: 42 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        performance={{ min: 0.5 }}
      >
        <ambientLight intensity={1.25} />
        <directionalLight position={[4, 5, 6]} intensity={2.3} color="#d7f8ff" />
        <directionalLight position={[-4, -2, 3]} intensity={1.1} color="#63a8ff" />
        <pointLight position={[2.6, -2.2, 2.4]} intensity={2.8} color="#66e0a3" />
        <Suspense fallback={<LoadingCore />}>
          <EchoCoreModel reducedMotion={reducedMotion} />
        </Suspense>
      </Canvas>
    </div>
  );
}
