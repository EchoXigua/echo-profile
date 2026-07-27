"use client";

import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
import {
  Suspense,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from "react";
import {
  AdditiveBlending,
  AnimationClip,
  BufferAttribute,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  Group,
  Interpolant,
  Line,
  LineBasicMaterial,
  MathUtils,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Quaternion,
  SRGBColorSpace,
  TextureLoader,
  Vector3,
} from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkeleton } from "three/examples/jsm/utils/SkeletonUtils.js";

type PointerTarget = {
  x: number;
  y: number;
  speed: number;
  lastMove: number;
  clickAt: number;
};

type StoryState = {
  activeStage: number;
  progress: number;
  scrollVelocity: number;
};

type PoseAnimationBinding = {
  interpolant: Interpolant;
  neutral: Float32Array;
  node: Object3D;
  property: "position" | "quaternion" | "scale";
};

type PoseAnimationLayer = {
  bindings: PoseAnimationBinding[];
  duration: number;
};

type PoseAnimationScratch = {
  neutral: Quaternion;
  sample: Quaternion;
  delta: Quaternion;
  weighted: Quaternion;
};

function createPoseAnimationLayer(
  root: Object3D,
  clip: AnimationClip,
  neutralProgress = 0,
  allowedNodeNames?: ReadonlySet<string>,
): PoseAnimationLayer {
  const bindings = clip.tracks.flatMap((track) => {
    const separator = track.name.lastIndexOf(".");
    if (separator < 1) return [];
    const nodeName = track.name.slice(0, separator);
    if (allowedNodeNames && !allowedNodeNames.has(nodeName)) return [];
    const property = track.name.slice(separator + 1);
    if (
      property !== "position" &&
      property !== "quaternion" &&
      property !== "scale"
    ) {
      return [];
    }
    const node = root.getObjectByName(nodeName);
    if (!node) return [];
    const interpolant = (
      track as typeof track & {
        createInterpolant: (result: Float32Array) => Interpolant;
      }
    ).createInterpolant(new Float32Array(track.getValueSize()));
    const neutral = Float32Array.from(
      interpolant.evaluate(
        MathUtils.clamp(neutralProgress, 0, 1) * clip.duration,
      ),
    );
    return [
      {
        node,
        property,
        interpolant,
        neutral,
      } satisfies PoseAnimationBinding,
    ];
  });
  return { bindings, duration: clip.duration };
}

function applyPoseAnimationLayer(
  layer: PoseAnimationLayer,
  progress: number,
  weight: number,
  scratch: PoseAnimationScratch,
) {
  if (weight <= 0.0001) return;
  const time =
    MathUtils.clamp(progress, 0, 0.99999) * Math.max(layer.duration, 0.0001);
  layer.bindings.forEach((binding) => {
    const value = binding.interpolant.evaluate(time);
    if (binding.property === "quaternion") {
      scratch.neutral.fromArray(binding.neutral);
      scratch.sample.fromArray(value);
      scratch.delta
        .copy(scratch.neutral)
        .invert()
        .multiply(scratch.sample)
        .normalize();
      scratch.weighted.identity().slerp(scratch.delta, weight);
      binding.node.quaternion.multiply(scratch.weighted).normalize();
      return;
    }
    if (binding.property === "position") {
      binding.node.position.x += (value[0] - binding.neutral[0]) * weight;
      binding.node.position.y += (value[1] - binding.neutral[1]) * weight;
      binding.node.position.z += (value[2] - binding.neutral[2]) * weight;
      return;
    }
    binding.node.scale.x *= MathUtils.lerp(
      1,
      value[0] / Math.max(binding.neutral[0], 0.0001),
      weight,
    );
    binding.node.scale.y *= MathUtils.lerp(
      1,
      value[1] / Math.max(binding.neutral[1], 0.0001),
      weight,
    );
    binding.node.scale.z *= MathUtils.lerp(
      1,
      value[2] / Math.max(binding.neutral[2], 0.0001),
      weight,
    );
  });
}

function applyAbsolutePoseAnimationLayer(
  layer: PoseAnimationLayer,
  progress: number,
) {
  const time =
    MathUtils.clamp(progress, 0, 0.99999) * Math.max(layer.duration, 0.0001);
  layer.bindings.forEach((binding) => {
    const value = binding.interpolant.evaluate(time);
    if (binding.property === "quaternion") {
      binding.node.quaternion
        .set(value[0], value[1], value[2], value[3])
        .normalize();
      return;
    }
    if (binding.property === "position") {
      binding.node.position.set(value[0], value[1], value[2]);
      return;
    }
    binding.node.scale.set(value[0], value[1], value[2]);
  });
}

type StagePose = {
  astronaut: {
    x: number;
    y: number;
    z: number;
    rx: number;
    ry: number;
    rz: number;
    scale: number;
  };
  camera: {
    x: number;
    y: number;
    z: number;
    lookX: number;
    lookY: number;
    lookZ: number;
    fov: number;
  };
  station: {
    x: number;
    y: number;
    z: number;
    rx: number;
    ry: number;
    rz: number;
    scale: number;
  };
};

const STAGE_COUNT = 6;
const STAGE_POSES: readonly StagePose[] = [
  {
    astronaut: {
      x: 2.55,
      y: -0.34,
      z: 0.38,
      rx: 0.08,
      ry: -0.12,
      rz: -0.04,
      scale: 1.34,
    },
    camera: {
      x: 0,
      y: 0.05,
      z: 8.4,
      lookX: 0.35,
      lookY: 0.06,
      lookZ: -0.25,
      fov: 42,
    },
    station: {
      x: 1.35,
      y: 0.08,
      z: -2.7,
      rx: 0.04,
      ry: -0.18,
      rz: -0.18,
      scale: 3.45,
    },
  },
  {
    astronaut: {
      x: 0.95,
      y: -0.26,
      z: 1.08,
      rx: 0.04,
      ry: 0.12,
      rz: 0.08,
      scale: 1.82,
    },
    camera: {
      x: -0.54,
      y: 0.2,
      z: 7.5,
      lookX: 0.18,
      lookY: 0.18,
      lookZ: -0.52,
      fov: 39,
    },
    station: {
      x: 0.55,
      y: -0.08,
      z: -3.4,
      rx: 0.05,
      ry: 0.16,
      rz: 0.06,
      scale: 3.8,
    },
  },
  {
    astronaut: {
      x: -0.72,
      y: -0.1,
      z: -0.18,
      rx: 1.38,
      ry: -0.45,
      rz: -1.12,
      scale: 1.28,
    },
    camera: {
      x: 0.54,
      y: 0.1,
      z: 7.05,
      lookX: 0.24,
      lookY: 0,
      lookZ: -0.9,
      fov: 41,
    },
    station: {
      x: 2.9,
      y: -1.1,
      z: -4.8,
      rx: 0.32,
      ry: 1.16,
      rz: -0.26,
      scale: 3.05,
    },
  },
  {
    astronaut: {
      x: 1.08,
      y: 0.02,
      z: -0.52,
      rx: 1.22,
      ry: 0.2,
      rz: -1.42,
      scale: 1.1,
    },
    camera: {
      x: -0.72,
      y: 0.46,
      z: 6.65,
      lookX: 0.22,
      lookY: 0.16,
      lookZ: -1.35,
      fov: 40,
    },
    station: {
      x: -3.3,
      y: -0.8,
      z: -5.2,
      rx: -0.18,
      ry: 1.72,
      rz: 0.12,
      scale: 2.6,
    },
  },
  {
    astronaut: {
      x: -1.2,
      y: 0.25,
      z: -0.44,
      rx: 1.5,
      ry: -0.25,
      rz: -1.24,
      scale: 1.18,
    },
    camera: {
      x: 0.84,
      y: 0.58,
      z: 6.9,
      lookX: -0.08,
      lookY: 0.2,
      lookZ: -1.05,
      fov: 42,
    },
    station: {
      x: 3.4,
      y: 0.4,
      z: -5.5,
      rx: 0.16,
      ry: 2.25,
      rz: -0.16,
      scale: 2.2,
    },
  },
  {
    astronaut: {
      x: 0.62,
      y: -0.44,
      z: 0.4,
      rx: 0.02,
      ry: 0.04,
      rz: 0.01,
      scale: 1.7,
    },
    camera: {
      x: 0,
      y: 0.08,
      z: 8.05,
      lookX: 0.36,
      lookY: 0.04,
      lookZ: -0.42,
      fov: 43,
    },
    station: {
      x: 0,
      y: -3.6,
      z: -7,
      rx: 0,
      ry: 2.8,
      rz: 0,
      scale: 1.8,
    },
  },
] as const;

const PALETTE = {
  hero: new Color("#020508"),
  about: new Color("#05070a"),
  engineering: new Color("#071008"),
  leanmate: new Color("#03130d"),
  voya: new Color("#060814"),
  contact: new Color("#080a10"),
};

const TMP_COLOR_A = new Color();
const TMP_COLOR_B = new Color();

function seededRandom(seed: number) {
  const value = Math.sin(seed * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function smoothRange(
  value: number,
  start: number,
  peakStart: number,
  peakEnd: number,
  end: number,
) {
  const fadeIn = MathUtils.smoothstep(value, start, peakStart);
  const fadeOut = 1 - MathUtils.smoothstep(value, peakEnd, end);
  return Math.min(fadeIn, fadeOut);
}

function sampleStagePose(progress: number) {
  const lowerIndex = Math.min(
    STAGE_POSES.length - 2,
    Math.max(0, Math.floor(progress)),
  );
  const upperIndex = lowerIndex + 1;
  const rawT = MathUtils.clamp(progress - lowerIndex, 0, 1);
  const t = rawT * rawT * (3 - 2 * rawT);
  return {
    lower: STAGE_POSES[lowerIndex],
    upper: STAGE_POSES[upperIndex],
    t,
  };
}

function usePrefersReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return reducedMotion;
}

function LoadingGeometry() {
  return (
    <group rotation={[0.05, 0.1, -0.06]} position={[1.65, -0.6, 0]}>
      <mesh>
        <capsuleGeometry args={[0.3, 1.08, 8, 16]} />
        <meshStandardMaterial color="#6f7780" wireframe />
      </mesh>
      <mesh position={[0, 0.92, 0]}>
        <sphereGeometry args={[0.38, 18, 12]} />
        <meshStandardMaterial color="#a9b0b7" wireframe />
      </mesh>
    </group>
  );
}

function SpaceDust({
  pointerTarget,
  storyState,
  reducedMotion,
}: {
  pointerTarget: MutableRefObject<PointerTarget>;
  storyState: MutableRefObject<StoryState>;
  reducedMotion: boolean;
}) {
  const farRef = useRef<Points>(null);
  const nearRef = useRef<Points>(null);
  const { size } = useThree();
  const count = size.width < 900 ? 520 : 1150;

  const geometries = useMemo(() => {
    const create = (amount: number, seedOffset: number, spread: number) => {
      const positions = new Float32Array(amount * 3);
      for (let index = 0; index < amount; index += 1) {
        positions[index * 3] =
          (seededRandom(index + 3 + seedOffset) - 0.5) * spread;
        positions[index * 3 + 1] =
          (seededRandom(index + 17 + seedOffset) - 0.5) * spread * 0.62;
        positions[index * 3 + 2] =
          -seededRandom(index + 31 + seedOffset) * 16 + 4;
      }
      const geometry = new BufferGeometry();
      geometry.setAttribute("position", new BufferAttribute(positions, 3));
      return geometry;
    };
    return {
      far: create(count, 0, 20),
      near: create(Math.floor(count * 0.18), 902, 14),
    };
  }, [count]);

  const materials = useMemo(
    () => ({
      far: new PointsMaterial({
        color: "#8db3c7",
        size: 1.1,
        transparent: true,
        opacity: 0.42,
        depthWrite: false,
        blending: AdditiveBlending,
        sizeAttenuation: false,
      }),
      near: new PointsMaterial({
        color: "#d4edf2",
        size: 1.45,
        transparent: true,
        opacity: 0.32,
        depthWrite: false,
        blending: AdditiveBlending,
        sizeAttenuation: false,
      }),
    }),
    [],
  );
  useEffect(
    () => () => {
      geometries.far.dispose();
      geometries.near.dispose();
      materials.far.dispose();
      materials.near.dispose();
    },
    [geometries, materials],
  );

  useFrame((state, delta) => {
    if (!farRef.current || !nearRef.current) return;
    const pointerX = reducedMotion ? 0 : pointerTarget.current.x;
    const pointerY = reducedMotion ? 0 : pointerTarget.current.y;
    const velocity = storyState.current.scrollVelocity;

    farRef.current.position.x = MathUtils.damp(
      farRef.current.position.x,
      -pointerX * 0.08,
      3.2,
      delta,
    );
    farRef.current.position.y = MathUtils.damp(
      farRef.current.position.y,
      -pointerY * 0.05,
      3.2,
      delta,
    );
    nearRef.current.position.x = MathUtils.damp(
      nearRef.current.position.x,
      -pointerX * 0.34,
      3.8,
      delta,
    );
    nearRef.current.position.y = MathUtils.damp(
      nearRef.current.position.y,
      -pointerY * 0.22,
      3.8,
      delta,
    );
    nearRef.current.position.z = MathUtils.damp(
      nearRef.current.position.z,
      velocity * 0.18,
      4,
      delta,
    );

    if (!reducedMotion) {
      farRef.current.rotation.y += delta * 0.003;
      nearRef.current.rotation.z =
        Math.sin(state.clock.elapsedTime * 0.07) * 0.008;
    }
  });

  return (
    <>
      <points
        ref={farRef}
        geometry={geometries.far}
        material={materials.far}
      />
      <points
        ref={nearRef}
        geometry={geometries.near}
        material={materials.near}
      />
    </>
  );
}

function OrbitalLines({
  storyState,
}: {
  storyState: MutableRefObject<StoryState>;
}) {
  const groupRef = useRef<Group>(null);
  const lines = useMemo(() => {
    const startPoints = [
      new Vector3(-5.8, -2.5, 0.6),
      new Vector3(-3.8, -2.0, 0.22),
      new Vector3(-1.4, -1.1, -0.12),
      new Vector3(0.7, -0.05, -0.7),
      new Vector3(2.75, 0.75, -1.5),
      new Vector3(4.9, 1.65, -2.8),
    ];

    return Array.from({ length: 5 }, (_, index) => {
      const offset = (index - 2) * 0.15;
      const points = startPoints.map(
        (point, pointIndex) =>
          new Vector3(
            point.x,
            point.y + offset * (1 - pointIndex * 0.08),
            point.z + offset * 0.45,
          ),
      );
      const geometry = new BufferGeometry().setFromPoints(
        new CatmullRomCurve3(points, false, "catmullrom", 0.4).getPoints(180),
      );
      const material = new LineBasicMaterial({
        color: index === 2 ? "#bcd5df" : "#648fa2",
        transparent: true,
        opacity: index === 2 ? 0.32 : 0.1,
        depthWrite: false,
        blending: AdditiveBlending,
      });
      return new Line(geometry, material);
    });
  }, []);

  useEffect(
    () => () => {
      lines.forEach((line) => {
        line.geometry.dispose();
        (line.material as LineBasicMaterial).dispose();
      });
    },
    [lines],
  );

  useFrame(() => {
    if (!groupRef.current) return;
    const fade = 1 - MathUtils.smoothstep(storyState.current.progress, 0.75, 1.9);
    groupRef.current.visible = fade > 0.01;
    lines.forEach((line, index) => {
      (line.material as LineBasicMaterial).opacity =
        fade * (index === 2 ? 0.32 : 0.1);
    });
  });

  return (
    <group ref={groupRef}>
      {lines.map((line, index) => (
        <primitive key={index} object={line} />
      ))}
    </group>
  );
}

function StageBackgrounds({
  pointerTarget,
  storyState,
  reducedMotion,
}: {
  pointerTarget: MutableRefObject<PointerTarget>;
  storyState: MutableRefObject<StoryState>;
  reducedMotion: boolean;
}) {
  const engineeringRef = useRef<Group>(null);
  const leanmateRef = useRef<Group>(null);
  const voyaRef = useRef<Group>(null);
  const contactFarRef = useRef<Group>(null);
  const contactMidRef = useRef<Group>(null);
  const contactFrontRef = useRef<Group>(null);
  const { scene } = useThree();
  const contactStickerTextureSource = useLoader(
    TextureLoader,
    "/projects/contact-stickers-foreground.png",
  );
  const contactStickerTexture = useMemo(() => {
    const texture = contactStickerTextureSource.clone();
    texture.colorSpace = SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }, [contactStickerTextureSource]);

  const tunnelFrames = useMemo(
    () =>
      Array.from({ length: 18 }, (_, index) => ({
        z: -index * 1.1 + 2.5,
        twist: (index % 2 === 0 ? 1 : -1) * index * 0.018,
        scale: 1 + index * 0.028,
      })),
    [],
  );
  const tunnelBlocks = useMemo(
    () =>
      Array.from({ length: 42 }, (_, index) => ({
        x: (seededRandom(index + 200) - 0.5) * 10.5,
        y: (seededRandom(index + 410) - 0.5) * 6.2,
        z: -seededRandom(index + 630) * 16 + 3,
        sx: 0.12 + seededRandom(index + 800) * 0.5,
        sy: 0.08 + seededRandom(index + 920) * 0.4,
        sz: 0.18 + seededRandom(index + 1030) * 1.2,
      })),
    [],
  );
  const constellation = useMemo(
    () =>
      Array.from({ length: 34 }, (_, index) => ({
        x: (seededRandom(index + 1410) - 0.5) * 8,
        y: (seededRandom(index + 1540) - 0.5) * 5.2,
        z: -seededRandom(index + 1680) * 7 - 0.5,
        size: 0.025 + seededRandom(index + 1820) * 0.07,
      })),
    [],
  );
  const contactObjects = useMemo(
    () =>
      Array.from({ length: 25 }, (_, index) => ({
        x: (seededRandom(index + 2100) - 0.5) * 10.5,
        y: (seededRandom(index + 2240) - 0.5) * 6.5,
        z: -seededRandom(index + 2380) * 6 + 1,
        scale: 0.09 + seededRandom(index + 2520) * 0.34,
        rx: seededRandom(index + 2660) * Math.PI,
        ry: seededRandom(index + 2800) * Math.PI,
        type: index % 3,
      })),
    [],
  );

  const materials = useMemo(
    () => ({
      tunnel: new MeshStandardMaterial({
        color: "#11181a",
        emissive: "#101d13",
        emissiveIntensity: 0.44,
        roughness: 0.62,
        metalness: 0.58,
        transparent: true,
      }),
      tunnelLight: new MeshBasicMaterial({
        color: "#b8f05b",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      leanShell: new MeshBasicMaterial({
        color: "#61dda0",
        wireframe: true,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      leanNode: new MeshBasicMaterial({
        color: "#9ff2c5",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      voyaRing: new MeshBasicMaterial({
        color: "#8b64ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      voyaCore: new MeshBasicMaterial({
        color: "#3e9dff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      contactFar: new MeshStandardMaterial({
        color: "#70808c",
        emissive: "#26364a",
        emissiveIntensity: 0.28,
        roughness: 0.42,
        metalness: 0.72,
        transparent: true,
        opacity: 0,
      }),
      contactMid: new MeshStandardMaterial({
        color: "#c6d0d7",
        emissive: "#38506a",
        emissiveIntensity: 0.22,
        roughness: 0.34,
        metalness: 0.68,
        transparent: true,
        opacity: 0,
      }),
      contactFront: new MeshStandardMaterial({
        color: "#e1e7ea",
        emissive: "#473f72",
        emissiveIntensity: 0.18,
        roughness: 0.3,
        metalness: 0.7,
        transparent: true,
        opacity: 0,
      }),
    }),
    [],
  );
  const materialsRef = useRef(materials);
  const sceneRef = useRef(scene);
  const stickerMaterial = useMemo(
    () =>
      new MeshBasicMaterial({
        map: contactStickerTexture,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        toneMapped: false,
      }),
    [contactStickerTexture],
  );
  const stickerMaterialRef = useRef(stickerMaterial);

  useEffect(
    () => () => {
      Object.values(materials).forEach((material) => material.dispose());
      stickerMaterial.dispose();
      contactStickerTexture.dispose();
    },
    [contactStickerTexture, materials, stickerMaterial],
  );

  useFrame((state, delta) => {
    const frameMaterials = materialsRef.current;
    const frameScene = sceneRef.current;
    const progress = storyState.current.progress;
    const pointerX = reducedMotion ? 0 : pointerTarget.current.x;
    const pointerY = reducedMotion ? 0 : pointerTarget.current.y;
    const velocity = storyState.current.scrollVelocity;
    const engineeringAlpha = smoothRange(progress, 1.12, 1.75, 2.3, 2.92);
    const leanmateAlpha = smoothRange(progress, 2.15, 2.7, 3.3, 3.92);
    const voyaAlpha = smoothRange(progress, 3.12, 3.7, 4.3, 4.9);
    const contactAlpha = MathUtils.smoothstep(progress, 4.16, 4.88);

    const paletteIndex = Math.min(4, Math.floor(progress));
    const paletteT = MathUtils.clamp(progress - paletteIndex, 0, 1);
    const colors = [
      PALETTE.hero,
      PALETTE.about,
      PALETTE.engineering,
      PALETTE.leanmate,
      PALETTE.voya,
      PALETTE.contact,
    ];
    TMP_COLOR_A.copy(colors[paletteIndex]);
    TMP_COLOR_B.copy(colors[paletteIndex + 1]);
    if (frameScene.background instanceof Color) {
      frameScene.background.lerpColors(TMP_COLOR_A, TMP_COLOR_B, paletteT);
    }
    if (frameScene.fog) {
      frameScene.fog.color.lerpColors(TMP_COLOR_A, TMP_COLOR_B, paletteT);
    }

    frameMaterials.tunnel.opacity = engineeringAlpha;
    frameMaterials.tunnelLight.opacity = engineeringAlpha * 0.78;
    frameMaterials.leanShell.opacity = leanmateAlpha * 0.28;
    frameMaterials.leanNode.opacity = leanmateAlpha * 0.86;
    frameMaterials.voyaRing.opacity = voyaAlpha * 0.34;
    frameMaterials.voyaCore.opacity = voyaAlpha * 0.6;
    frameMaterials.contactFar.opacity = contactAlpha * 0.42;
    frameMaterials.contactMid.opacity = contactAlpha * 0.66;
    frameMaterials.contactFront.opacity = contactAlpha * 0.84;
    stickerMaterialRef.current.opacity = contactAlpha * 0.96;

    if (engineeringRef.current) {
      engineeringRef.current.visible = engineeringAlpha > 0.01;
      engineeringRef.current.position.z =
        (progress - 2) * 3.8 + velocity * 0.38;
      engineeringRef.current.rotation.z = MathUtils.damp(
        engineeringRef.current.rotation.z,
        pointerX * 0.025 + (progress - 2) * 0.08,
        3,
        delta,
      );
      engineeringRef.current.position.x = MathUtils.damp(
        engineeringRef.current.position.x,
        -pointerX * 0.22,
        3,
        delta,
      );
      engineeringRef.current.position.y = MathUtils.damp(
        engineeringRef.current.position.y,
        -pointerY * 0.14,
        3,
        delta,
      );
    }

    if (leanmateRef.current) {
      leanmateRef.current.visible = leanmateAlpha > 0.01;
      leanmateRef.current.position.x = MathUtils.damp(
        leanmateRef.current.position.x,
        -pointerX * 0.34,
        3.5,
        delta,
      );
      leanmateRef.current.position.y = MathUtils.damp(
        leanmateRef.current.position.y,
        -pointerY * 0.24,
        3.5,
        delta,
      );
      leanmateRef.current.rotation.y += reducedMotion ? 0 : delta * 0.06;
      leanmateRef.current.rotation.z =
        (progress - 3) * 0.22 + pointerX * 0.035;
    }

    if (voyaRef.current) {
      voyaRef.current.visible = voyaAlpha > 0.01;
      voyaRef.current.position.x = MathUtils.damp(
        voyaRef.current.position.x,
        -pointerX * 0.42,
        4,
        delta,
      );
      voyaRef.current.position.y = MathUtils.damp(
        voyaRef.current.position.y,
        -pointerY * 0.28,
        4,
        delta,
      );
      voyaRef.current.position.z = (progress - 4) * 4.5;
      voyaRef.current.rotation.z +=
        reducedMotion ? 0 : delta * (0.08 + Math.abs(velocity) * 0.12);
    }

    const parallaxTargets = [
      {
        ref: contactFarRef,
        factor: 0.12,
      },
      {
        ref: contactMidRef,
        factor: 0.34,
      },
      {
        ref: contactFrontRef,
        factor: 0.72,
      },
    ];
    parallaxTargets.forEach(({ ref, factor }, index) => {
      const group = ref.current;
      if (!group) return;
      group.visible = contactAlpha > 0.01;
      group.position.x = MathUtils.damp(
        group.position.x,
        -pointerX * factor,
        4.2 - index * 0.35,
        delta,
      );
      group.position.y = MathUtils.damp(
        group.position.y,
        -pointerY * factor * 0.64,
        4.2 - index * 0.35,
        delta,
      );
      group.rotation.y = MathUtils.damp(
        group.rotation.y,
        pointerX * factor * 0.05,
        3.8,
        delta,
      );
      group.rotation.x = MathUtils.damp(
        group.rotation.x,
        -pointerY * factor * 0.035,
        3.8,
        delta,
      );
      if (!reducedMotion) {
        group.rotation.z += delta * (index - 1) * 0.006;
      }
    });

    if (!reducedMotion && contactFrontRef.current) {
      contactFrontRef.current.position.z =
        Math.sin(state.clock.elapsedTime * 0.28) * 0.08;
    }
  });

  return (
    <>
      <group ref={engineeringRef}>
        {tunnelFrames.map((frame, index) => (
          <group
            key={index}
            position={[0, 0, frame.z]}
            rotation={[0, 0, frame.twist]}
            scale={frame.scale}
          >
            <mesh position={[0, 2.55, 0]} material={materials.tunnel}>
              <boxGeometry args={[8.6, 0.1, 0.08]} />
            </mesh>
            <mesh position={[0, -2.55, 0]} material={materials.tunnel}>
              <boxGeometry args={[8.6, 0.1, 0.08]} />
            </mesh>
            <mesh position={[-4.25, 0, 0]} material={materials.tunnel}>
              <boxGeometry args={[0.1, 5.2, 0.08]} />
            </mesh>
            <mesh position={[4.25, 0, 0]} material={materials.tunnel}>
              <boxGeometry args={[0.1, 5.2, 0.08]} />
            </mesh>
            {index % 2 === 0 && (
              <>
                <mesh
                  position={[-3.1, 2.42, 0.08]}
                  material={materials.tunnelLight}
                >
                  <boxGeometry args={[0.52, 0.03, 0.03]} />
                </mesh>
                <mesh
                  position={[3.1, -2.42, 0.08]}
                  material={materials.tunnelLight}
                >
                  <boxGeometry args={[0.52, 0.03, 0.03]} />
                </mesh>
              </>
            )}
          </group>
        ))}
        {tunnelBlocks.map((block, index) => (
          <mesh
            key={`block-${index}`}
            position={[block.x, block.y, block.z]}
            scale={[block.sx, block.sy, block.sz]}
            material={index % 5 === 0 ? materials.tunnelLight : materials.tunnel}
          >
            <boxGeometry />
          </mesh>
        ))}
      </group>

      <group ref={leanmateRef} position={[0.5, 0, -1.8]}>
        {[0, 1, 2].map((index) => (
          <group
            key={index}
            position={[(index - 1) * 2.35, (index % 2) * 0.35 - 0.18, -index * 0.8]}
            scale={1 - index * 0.12}
          >
            <mesh material={materials.leanShell}>
              <sphereGeometry args={[1.42, 26, 18]} />
            </mesh>
            <mesh
              rotation={[Math.PI / 2.55, index * 0.3, 0]}
              material={materials.leanShell}
            >
              <torusGeometry args={[1.55, 0.012, 4, 80]} />
            </mesh>
            <mesh
              rotation={[0.2, Math.PI / 2.4, index * 0.4]}
              material={materials.leanShell}
            >
              <torusGeometry args={[1.1, 0.008, 4, 64]} />
            </mesh>
          </group>
        ))}
        {constellation.map((node, index) => (
          <mesh
            key={`node-${index}`}
            position={[node.x, node.y, node.z]}
            scale={node.size}
            material={materials.leanNode}
          >
            <icosahedronGeometry args={[1, 0]} />
          </mesh>
        ))}
      </group>

      <group
        ref={voyaRef}
        position={[-0.3, 0, -1.8]}
        rotation={[0.15, 0.2, 0]}
        scale={1.4}
      >
        {Array.from({ length: 14 }, (_, index) => (
          <mesh
            key={index}
            position={[0, 0, -index * 0.55]}
            rotation={[
              Math.PI / 2 + Math.sin(index * 0.7) * 0.2,
              Math.cos(index * 0.56) * 0.3,
              index * 0.24,
            ]}
            scale={1 + index * 0.075}
            material={index % 3 === 0 ? materials.voyaCore : materials.voyaRing}
          >
            <torusGeometry args={[1.5, index % 3 === 0 ? 0.035 : 0.015, 5, 92]} />
          </mesh>
        ))}
        <mesh position={[0, 0, -6.5]} material={materials.voyaCore}>
          <sphereGeometry args={[0.34, 18, 12]} />
        </mesh>
      </group>

      <group ref={contactFarRef} position={[0.2, 0, -3]}>
        {contactObjects.slice(0, 10).map((item, index) => (
          <mesh
            key={index}
            position={[item.x, item.y, item.z]}
            rotation={[item.rx, item.ry, item.rx * 0.4]}
            scale={item.scale}
            material={materials.contactFar}
          >
            {item.type === 0 ? (
              <octahedronGeometry args={[1, 0]} />
            ) : item.type === 1 ? (
              <torusGeometry args={[0.72, 0.16, 8, 20]} />
            ) : (
              <dodecahedronGeometry args={[0.85, 0]} />
            )}
          </mesh>
        ))}
      </group>
      <group ref={contactMidRef} position={[0, 0, -1]}>
        {contactObjects.slice(10, 20).map((item, index) => (
          <mesh
            key={index}
            position={[item.x, item.y, item.z]}
            rotation={[item.rx, item.ry, item.rx * 0.25]}
            scale={item.scale * 1.35}
            material={materials.contactMid}
          >
            {item.type === 0 ? (
              <icosahedronGeometry args={[1, 1]} />
            ) : item.type === 1 ? (
              <coneGeometry args={[0.72, 1.4, 5]} />
            ) : (
              <torusKnotGeometry args={[0.52, 0.12, 48, 6]} />
            )}
          </mesh>
        ))}
      </group>
      <group ref={contactFrontRef} position={[0, 0, 1.4]}>
        <mesh position={[0, 0, -0.35]} material={stickerMaterial}>
          <planeGeometry args={[10.35, 5.175]} />
        </mesh>
        {contactObjects.slice(20).map((item, index) => (
          <mesh
            key={index}
            position={[item.x * 1.12, item.y * 1.08, item.z + 1.6]}
            rotation={[item.rx, item.ry, item.rx * 0.55]}
            scale={item.scale * 2.35}
            material={materials.contactFront}
          >
            {item.type === 0 ? (
              <dodecahedronGeometry args={[1, 0]} />
            ) : item.type === 1 ? (
              <torusKnotGeometry args={[0.58, 0.14, 56, 7]} />
            ) : (
              <octahedronGeometry args={[1.1, 0]} />
            )}
          </mesh>
        ))}
      </group>
    </>
  );
}

function prepareAstronaut(root: Object3D) {
  const materials: MeshStandardMaterial[] = [];
  root.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.frustumCulled = false;
    object.castShadow = false;
    object.receiveShadow = false;
    const sourceMaterials = Array.isArray(object.material)
      ? object.material
      : [object.material];
    const cloned = sourceMaterials.map((material) => {
      const next = material.clone() as MeshStandardMaterial;
      if ("roughness" in next) next.roughness = Math.max(0.34, next.roughness);
      if ("metalness" in next) next.metalness = Math.max(0.12, next.metalness);
      materials.push(next);
      return next;
    });
    object.material = Array.isArray(object.material) ? cloned : cloned[0];
  });
  return materials;
}

function prepareStation(root: Object3D) {
  const material = new MeshStandardMaterial({
    color: "#151b20",
    emissive: "#17242b",
    emissiveIntensity: 0.2,
    metalness: 0.84,
    roughness: 0.34,
    transparent: true,
  });
  root.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.material = material;
    object.castShadow = false;
    object.receiveShadow = false;
  });
  return material;
}

function ExperienceModels({
  onReady,
  pointerTarget,
  reducedMotion,
}: {
  onReady: () => void;
  pointerTarget: MutableRefObject<PointerTarget>;
  reducedMotion: boolean;
}) {
  const astronautPathRef = useRef<Group>(null);
  const astronautPointerRef = useRef<Group>(null);
  const astronautFloatRef = useRef<Group>(null);
  const stationPathRef = useRef<Group>(null);
  const stationFloatRef = useRef<Group>(null);
  const pointerCurrent = useRef(new Vector3());
  const pointerActivity = useRef(0);
  const poseScratch = useRef<PoseAnimationScratch>({
    neutral: new Quaternion(),
    sample: new Quaternion(),
    delta: new Quaternion(),
    weighted: new Quaternion(),
  });
  const storyState = useRef<StoryState>({
    activeStage: 0,
    progress: 0,
    scrollVelocity: 0,
  });
  const actionsRef = useRef<{
    story: PoseAnimationLayer;
    pointerWave: PoseAnimationLayer;
    pointerSweep: PoseAnimationLayer;
    pointerClick: PoseAnimationLayer;
    zeroGIdle: PoseAnimationLayer;
  } | null>(null);
  const { camera, size } = useThree();
  const cameraRef = useRef(camera);

  const [astronautGltf, stationGltf] = useLoader(GLTFLoader, [
    "/models/astronaut-lusion-animated.glb",
    "/models/space-station-greybox.glb",
  ]);

  const astronautAsset = useMemo(() => {
    const root = cloneSkeleton(astronautGltf.scene);
    const materials = prepareAstronaut(root);
    const storyClip = astronautGltf.animations.find(
      (clip) => clip.name === "EchoScrollStory",
    );
    const pointerWaveClip = astronautGltf.animations.find(
      (clip) => clip.name === "EchoPointerWave",
    );
    const pointerSweepClip = astronautGltf.animations.find(
      (clip) => clip.name === "EchoPointerSweep",
    );
    const pointerClickClip = astronautGltf.animations.find(
      (clip) => clip.name === "EchoPointerClick",
    );
    const zeroGIdleClip = astronautGltf.animations.find(
      (clip) => clip.name === "EchoZeroGIdle",
    );
    if (
      !storyClip ||
      !pointerWaveClip ||
      !pointerSweepClip ||
      !pointerClickClip ||
      !zeroGIdleClip
    ) {
      throw new Error(
        "Astronaut GLB is missing one or more Echo motion actions",
      );
    }
    return {
      root,
      materials,
      story: createPoseAnimationLayer(root, storyClip),
      pointerWave: createPoseAnimationLayer(root, pointerWaveClip),
      pointerSweep: createPoseAnimationLayer(root, pointerSweepClip, 0.5),
      pointerClick: createPoseAnimationLayer(root, pointerClickClip),
      zeroGIdle: createPoseAnimationLayer(
        root,
        zeroGIdleClip,
        0,
        new Set([
          "Waist",
          "Spine01",
          "Spine02",
          "NeckTwist01",
          "NeckTwist02",
          "Head",
        ]),
      ),
    };
  }, [astronautGltf]);

  const stationAsset = useMemo(() => {
    const root = stationGltf.scene.clone(true);
    const material = prepareStation(root);
    return { root, material };
  }, [stationGltf.scene]);
  const stationMaterialRef = useRef(stationAsset.material);

  useEffect(() => {
    actionsRef.current = {
      story: astronautAsset.story,
      pointerWave: astronautAsset.pointerWave,
      pointerSweep: astronautAsset.pointerSweep,
      pointerClick: astronautAsset.pointerClick,
      zeroGIdle: astronautAsset.zeroGIdle,
    };
    onReady();
    return () => {
      actionsRef.current = null;
      astronautAsset.materials.forEach((material) => material.dispose());
      stationAsset.material.dispose();
    };
  }, [astronautAsset, onReady, stationAsset.material]);

  useLayoutEffect(() => {
    const story = document.querySelector<HTMLElement>("#scroll-story");
    if (!story) return;

    gsap.registerPlugin(ScrollTrigger);
    const stageCopies = gsap.utils.toArray<HTMLElement>("[data-stage-copy]");
    const markers = Array.from(
      document.querySelectorAll<HTMLElement>("[data-stage-marker]"),
    );
    const orbitLabels = Array.from(
      document.querySelectorAll<HTMLElement>("[data-orbit-label]"),
    );
    const progressProxy = { value: 0 };

    const syncDom = (progress: number) => {
      const activeStage = MathUtils.clamp(
        Math.round(progress),
        0,
        STAGE_COUNT - 1,
      );
      storyState.current.activeStage = activeStage;
      markers.forEach((marker, index) => {
        marker.classList.toggle("is-active", index === activeStage);
      });
      orbitLabels.forEach((label) => {
        const labelStage = Number(label.dataset.orbitLabel);
        label.classList.toggle("is-active", labelStage === activeStage);
      });
      stageCopies.forEach((copy, index) => {
        const distance = Math.abs(progress - index);
        const alpha = reducedMotion
          ? 1
          : MathUtils.clamp(1.03 - distance * 1.4, 0.06, 1);
        gsap.set(copy, {
          autoAlpha: alpha,
          y: reducedMotion ? 0 : (index - progress) * 36,
        });
      });
    };

    const context = gsap.context(() => {
      syncDom(0);
      if (reducedMotion) return;

      gsap.to(progressProxy, {
        value: STAGE_COUNT - 1,
        ease: "none",
        scrollTrigger: {
          trigger: story,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.68,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            storyState.current.progress =
              self.progress * (STAGE_COUNT - 1);
            storyState.current.scrollVelocity = MathUtils.clamp(
              self.getVelocity() / 1450,
              -1.65,
              1.65,
            );
            syncDom(storyState.current.progress);
          },
        },
      });

      requestAnimationFrame(() => ScrollTrigger.refresh());
    }, story);

    return () => context.revert();
  }, [reducedMotion]);

  useFrame((state, delta) => {
    const astronautPath = astronautPathRef.current;
    const astronautPointer = astronautPointerRef.current;
    const astronautFloat = astronautFloatRef.current;
    const stationPath = stationPathRef.current;
    const stationFloat = stationFloatRef.current;
    const pathCamera = cameraRef.current as PerspectiveCamera;
    if (
      !astronautPath ||
      !astronautPointer ||
      !astronautFloat ||
      !stationPath ||
      !stationFloat
    ) {
      return;
    }

    const targetX = reducedMotion ? 0 : pointerTarget.current.x;
    const targetY = reducedMotion ? 0 : pointerTarget.current.y;
    pointerCurrent.current.x = MathUtils.damp(
      pointerCurrent.current.x,
      targetX,
      4.1,
      delta,
    );
    pointerCurrent.current.y = MathUtils.damp(
      pointerCurrent.current.y,
      targetY,
      4.1,
      delta,
    );
    const pointerImpulse =
      pointerTarget.current.speed *
      Math.exp(
        -Math.max(0, performance.now() - pointerTarget.current.lastMove) / 180,
      );
    pointerActivity.current = MathUtils.damp(
      pointerActivity.current,
      reducedMotion ? 0 : pointerImpulse,
      3.5,
      delta,
    );
    storyState.current.scrollVelocity = MathUtils.damp(
      storyState.current.scrollVelocity,
      0,
      2.8,
      delta,
    );

    const progress = reducedMotion ? 0 : storyState.current.progress;
    const pose = sampleStagePose(progress);
    const { lower, upper, t } = pose;
    const pointer = pointerCurrent.current;
    const velocity = storyState.current.scrollVelocity;
    const contactBlend = MathUtils.smoothstep(progress, 4.45, 4.95);

    astronautPath.position.set(
      MathUtils.lerp(lower.astronaut.x, upper.astronaut.x, t),
      MathUtils.lerp(lower.astronaut.y, upper.astronaut.y, t),
      MathUtils.lerp(lower.astronaut.z, upper.astronaut.z, t),
    );
    astronautPath.rotation.set(
      MathUtils.lerp(lower.astronaut.rx, upper.astronaut.rx, t),
      MathUtils.lerp(lower.astronaut.ry, upper.astronaut.ry, t),
      MathUtils.lerp(lower.astronaut.rz, upper.astronaut.rz, t),
    );
    const astronautScale = MathUtils.lerp(
      lower.astronaut.scale,
      upper.astronaut.scale,
      t,
    );
    astronautPath.scale.setScalar(astronautScale);

    astronautPointer.position.x = MathUtils.damp(
      astronautPointer.position.x,
      pointer.x * (0.13 + contactBlend * 0.05) + velocity * 0.045,
      4.4,
      delta,
    );
    astronautPointer.position.y = MathUtils.damp(
      astronautPointer.position.y,
      pointer.y * (0.09 + contactBlend * 0.04),
      4.4,
      delta,
    );
    astronautPointer.rotation.x = MathUtils.damp(
      astronautPointer.rotation.x,
      pointer.y * 0.035,
      4.2,
      delta,
    );
    astronautPointer.rotation.y = MathUtils.damp(
      astronautPointer.rotation.y,
      -pointer.x * 0.055,
      4.2,
      delta,
    );
    astronautPointer.rotation.z = MathUtils.damp(
      astronautPointer.rotation.z,
      -pointer.x * 0.025 - velocity * 0.035,
      4.2,
      delta,
    );

    const cameraParallax = size.width < 900 ? 0.12 : 0.22;
    pathCamera.position.set(
      MathUtils.lerp(lower.camera.x, upper.camera.x, t) +
        pointer.x * cameraParallax,
      MathUtils.lerp(lower.camera.y, upper.camera.y, t) +
        pointer.y * cameraParallax * 0.62,
      MathUtils.lerp(lower.camera.z, upper.camera.z, t) +
        Math.abs(velocity) * 0.08,
    );
    pathCamera.lookAt(
      MathUtils.lerp(lower.camera.lookX, upper.camera.lookX, t) +
        pointer.x * 0.045,
      MathUtils.lerp(lower.camera.lookY, upper.camera.lookY, t) +
        pointer.y * 0.03,
      MathUtils.lerp(lower.camera.lookZ, upper.camera.lookZ, t),
    );
    const nextFov = MathUtils.lerp(lower.camera.fov, upper.camera.fov, t);
    if (Math.abs(pathCamera.fov - nextFov) > 0.01) {
      pathCamera.fov = nextFov;
      pathCamera.updateProjectionMatrix();
    }

    stationPath.position.set(
      MathUtils.lerp(lower.station.x, upper.station.x, t),
      MathUtils.lerp(lower.station.y, upper.station.y, t),
      MathUtils.lerp(lower.station.z, upper.station.z, t),
    );
    stationPath.rotation.set(
      MathUtils.lerp(lower.station.rx, upper.station.rx, t),
      MathUtils.lerp(lower.station.ry, upper.station.ry, t),
      MathUtils.lerp(lower.station.rz, upper.station.rz, t),
    );
    const stationScale = MathUtils.lerp(
      lower.station.scale,
      upper.station.scale,
      t,
    );
    stationPath.scale.setScalar(stationScale);
    stationMaterialRef.current.opacity =
      1 - MathUtils.smoothstep(progress, 1.2, 2.45);

    if (!reducedMotion) {
      const elapsed = state.clock.elapsedTime;
      astronautFloat.position.y = Math.sin(elapsed * 0.64) * 0.035;
      astronautFloat.position.z = Math.cos(elapsed * 0.47) * 0.022;
      stationFloat.rotation.y += delta * 0.018;
      stationFloat.position.x = MathUtils.damp(
        stationFloat.position.x,
        -pointer.x * 0.055,
        2.6,
        delta,
      );
      stationFloat.position.y = MathUtils.damp(
        stationFloat.position.y,
        -pointer.y * 0.035,
        2.6,
        delta,
      );
    }

    const actions = actionsRef.current;
    if (actions) {
      const waveProgress = MathUtils.clamp(
        0.18 +
          (pointer.y + 1) * 0.34 +
          pointerActivity.current * 0.25,
        0,
        1,
      );
      applyAbsolutePoseAnimationLayer(
        actions.story,
        progress / (STAGE_COUNT - 1),
      );

      const idleProgress =
        (state.clock.elapsedTime % actions.zeroGIdle.duration) /
        actions.zeroGIdle.duration;
      applyPoseAnimationLayer(
        actions.zeroGIdle,
        idleProgress,
        reducedMotion ? 0 : 0.34,
        poseScratch.current,
      );

      const pointerWeight = reducedMotion ? 0 : contactBlend;
      applyPoseAnimationLayer(
        actions.pointerWave,
        waveProgress,
        pointerWeight,
        poseScratch.current,
      );
      applyPoseAnimationLayer(
        actions.pointerSweep,
        (pointer.x + 1) * 0.5,
        pointerWeight * 0.72,
        poseScratch.current,
      );

      const clickElapsed = performance.now() - pointerTarget.current.clickAt;
      const clickProgress =
        clickElapsed >= 0
          ? clickElapsed / Math.max(actions.pointerClick.duration * 1000, 1)
          : 2;
      applyPoseAnimationLayer(
        actions.pointerClick,
        clickProgress,
        clickProgress <= 1 ? pointerWeight : 0,
        poseScratch.current,
      );
    }
  });

  return (
    <>
      <SpaceDust
        pointerTarget={pointerTarget}
        storyState={storyState}
        reducedMotion={reducedMotion}
      />
      <OrbitalLines storyState={storyState} />
      <StageBackgrounds
        pointerTarget={pointerTarget}
        storyState={storyState}
        reducedMotion={reducedMotion}
      />
      <group ref={stationPathRef}>
        <group ref={stationFloatRef}>
          <primitive object={stationAsset.root} dispose={null} />
        </group>
      </group>
      <group ref={astronautPathRef}>
        <group ref={astronautPointerRef}>
          <group ref={astronautFloatRef}>
            <primitive object={astronautAsset.root} dispose={null} />
          </group>
        </group>
      </group>
    </>
  );
}

export function EchoScene() {
  const reducedMotion = usePrefersReducedMotion();
  const [sceneReady, setSceneReady] = useState(false);
  const pointerTarget = useRef<PointerTarget>({
    x: 0,
    y: 0,
    speed: 0,
    lastMove: 0,
    clickAt: Number.NEGATIVE_INFINITY,
  });
  const lastPointer = useRef({ x: 0, y: 0, time: 0 });
  const handleSceneReady = useCallback(() => setSceneReady(true), []);

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      const x = (event.clientX / window.innerWidth - 0.5) * 2;
      const y = (0.5 - event.clientY / window.innerHeight) * 2;
      const now = performance.now();
      const elapsed = Math.max(12, now - lastPointer.current.time);
      const distance = Math.hypot(
        x - lastPointer.current.x,
        y - lastPointer.current.y,
      );
      pointerTarget.current = {
        x,
        y,
        speed: MathUtils.clamp((distance / elapsed) * 160, 0, 1),
        lastMove: now,
        clickAt: pointerTarget.current.clickAt,
      };
      lastPointer.current = { x, y, time: now };
    };
    const onPointerDown = () => {
      pointerTarget.current = {
        ...pointerTarget.current,
        speed: 1,
        lastMove: performance.now(),
        clickAt: performance.now(),
      };
    };
    const resetPointer = () => {
      pointerTarget.current = {
        x: 0,
        y: 0,
        speed: 0,
        lastMove: performance.now(),
        clickAt: Number.NEGATIVE_INFINITY,
      };
      lastPointer.current = { x: 0, y: 0, time: performance.now() };
    };

    resetPointer();
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", onPointerDown, { passive: true });
    window.addEventListener("pointerleave", resetPointer);
    window.addEventListener("blur", resetPointer);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointerleave", resetPointer);
      window.removeEventListener("blur", resetPointer);
    };
  }, []);

  return (
    <div
      className="experience-scene"
      data-scene-state={sceneReady ? "ready" : "loading"}
      role="img"
      aria-label="宇航员沿独立飞行路径穿越工程隧道、绿色数据空间、蓝紫航行入口和多层联系场景；骨骼姿态、镜头、背景与 DOM 文案随滚动同步并支持反向播放"
    >
      <Canvas
        aria-hidden="true"
        camera={{ position: [0, 0.05, 8.4], fov: 42, near: 0.08, far: 48 }}
        dpr={[1, 1.55]}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
        }}
        performance={{ min: 0.58 }}
      >
        <color attach="background" args={["#020508"]} />
        <fog attach="fog" args={["#020508", 8.8, 23]} />
        <hemisphereLight args={["#d8e8ee", "#05080b", 1.2]} />
        <directionalLight
          position={[4.5, 6.5, 7]}
          intensity={3.8}
          color="#f4f7f7"
        />
        <directionalLight
          position={[-4.5, 1.5, 4]}
          intensity={1.65}
          color="#63d9b8"
        />
        <pointLight position={[3.8, 1.8, 2]} intensity={3.2} color="#508dff" />
        <pointLight
          position={[-2.4, -1.8, 3]}
          intensity={1.3}
          color="#b8f05b"
        />
        <Suspense fallback={<LoadingGeometry />}>
          <ExperienceModels
            onReady={handleSceneReady}
            pointerTarget={pointerTarget}
            reducedMotion={reducedMotion}
          />
        </Suspense>
      </Canvas>
      <p className="scene-caption" aria-hidden="true">
        {sceneReady ? "MOTION SYSTEM ONLINE" : "LOADING MOTION SYSTEM"} · SCROLL /
        POINTER
      </p>
    </div>
  );
}
