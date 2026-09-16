"use client";

import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import {
  Bloom,
  ChromaticAberration,
  EffectComposer,
  Noise,
  Vignette,
} from "@react-three/postprocessing";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
import { BlendFunction } from "postprocessing";
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
  DoubleSide,
  Group,
  Interpolant,
  Line,
  LineBasicMaterial,
  Material,
  MathUtils,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  PointLight,
  Points,
  PointsMaterial,
  Quaternion,
  ShaderMaterial,
  SRGBColorSpace,
  TextureLoader,
  Vector2,
  Vector3,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkeleton } from "three/examples/jsm/utils/SkeletonUtils.js";
import {
  createMasterTimelineSample,
  sampleMasterTimeline,
  sampleTimelineBackground,
} from "@/components/scene/lusionTimeline";

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

const DOM_STAGE_COUNT = 6;
const TIMELINE_BACKGROUND = new Color();
const TUNNEL_WHITE = new Color("#eaf7ff");
const TUNNEL_CYAN = new Color("#55e9ff");
const TUNNEL_RED = new Color("#ff355e");
const TUNNEL_GREEN = new Color("#78ffab");
const TUNNEL_MAGENTA = new Color("#ff4ac3");
const TUNNEL_DARK = new Color("#25353b");
const TUNNEL_RED_DARK = new Color("#38111d");
const TUNNEL_GREEN_DARK = new Color("#103825");
const TUNNEL_MAGENTA_DARK = new Color("#3a102f");
const TUNNEL_WHITE_EMISSIVE = new Color("#27434f");
const TUNNEL_RED_EMISSIVE = new Color("#5c1629");
const TUNNEL_GREEN_EMISSIVE = new Color("#1c7045");
const TUNNEL_MAGENTA_EMISSIVE = new Color("#6e0f55");

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

function mergeAssetByMaterial(
  root: Object3D,
  resolveMaterial: (name: string) => Material | null,
) {
  root.updateMatrixWorld(true);
  const buckets = new Map<
    Material,
    { geometries: BufferGeometry[]; names: string[] }
  >();
  root.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    const material = resolveMaterial(object.name);
    if (!material) return;
    const bucket = buckets.get(material) ?? { geometries: [], names: [] };
    const geometry = object.geometry.clone();
    geometry.applyMatrix4(object.matrixWorld);
    bucket.geometries.push(geometry);
    bucket.names.push(object.name);
    buckets.set(material, bucket);
  });

  const group = new Group();
  buckets.forEach(({ geometries, names }, material) => {
    const geometry = mergeGeometries(geometries, false);
    geometries.forEach((item) => item.dispose());
    if (!geometry) return;
    const mesh = new Mesh(geometry, material);
    mesh.name = names.join("__");
    mesh.frustumCulled = false;
    group.add(mesh);
  });
  return group;
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
    const fade =
      1 - MathUtils.smoothstep(storyState.current.progress, 0.08, 0.28);
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

function OpticalFlares({
  pointerTarget,
  storyState,
  reducedMotion,
}: {
  pointerTarget: MutableRefObject<PointerTarget>;
  storyState: MutableRefObject<StoryState>;
  reducedMotion: boolean;
}) {
  const groupRef = useRef<Group>(null);
  const color = useMemo(() => new Color("#dff8ff"), []);
  const material = useMemo(
    () =>
      new ShaderMaterial({
        uniforms: {
          uColor: { value: color },
          uOpacity: { value: 0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          varying vec2 vUv;
          uniform vec3 uColor;
          uniform float uOpacity;

          void main() {
            vec2 p = (vUv - 0.5) * 2.0;
            float radius = length(p);
            float core = exp(-radius * 16.0);
            float halo = exp(-radius * 4.8) * 0.28;
            float horizontal = exp(-abs(p.y) * 86.0)
              * smoothstep(1.0, 0.08, abs(p.x));
            float vertical = exp(-abs(p.x) * 92.0)
              * smoothstep(1.0, 0.06, abs(p.y));
            float diagonalA = exp(-abs(p.x - p.y) * 48.0)
              * smoothstep(0.82, 0.02, radius) * 0.32;
            float diagonalB = exp(-abs(p.x + p.y) * 48.0)
              * smoothstep(0.82, 0.02, radius) * 0.32;
            float energy = core * 1.8 + halo + horizontal + vertical
              + diagonalA + diagonalB;
            float alpha = energy * uOpacity * smoothstep(1.0, 0.68, radius);
            gl_FragColor = vec4(uColor * (1.2 + energy * 1.6), alpha);
          }
        `,
        transparent: true,
        depthWrite: false,
        depthTest: true,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
    [color],
  );
  const flares = useMemo(
    () =>
      Array.from({ length: 18 }, (_, index) => ({
        x: (seededRandom(index + 6100) - 0.5) * 8.4,
        y: (seededRandom(index + 6200) - 0.5) * 4.8,
        z: -seededRandom(index + 6300) * 18 + 2.2,
        scale: 0.22 + seededRandom(index + 6400) * 0.86,
      })),
    [],
  );
  const materialRef = useRef(material);

  useEffect(() => () => material.dispose(), [material]);

  useFrame((state, delta) => {
    const frameMaterial = materialRef.current;
    const progress = storyState.current.progress;
    const corridor = smoothRange(progress, 0.2, 0.3, 0.7, 0.78);
    const vortex = smoothRange(progress, 0.68, 0.72, 0.84, 0.9);
    const alpha = Math.max(corridor * 0.86, vortex);
    frameMaterial.uniforms.uOpacity.value =
      alpha *
      (0.62 + Math.min(Math.abs(storyState.current.scrollVelocity), 1) * 0.48);
    frameMaterial.uniforms.uColor.value.copy(
      progress < 0.5
        ? TUNNEL_WHITE
        : progress < 0.66
          ? TUNNEL_GREEN
          : TUNNEL_MAGENTA,
    );
    if (!groupRef.current) return;
    groupRef.current.visible = alpha > 0.01;
    groupRef.current.position.x = MathUtils.damp(
      groupRef.current.position.x,
      reducedMotion ? 0 : -pointerTarget.current.x * 0.34,
      4,
      delta,
    );
    groupRef.current.position.y = MathUtils.damp(
      groupRef.current.position.y,
      reducedMotion ? 0 : -pointerTarget.current.y * 0.22,
      4,
      delta,
    );
    groupRef.current.quaternion.copy(state.camera.quaternion);
  });

  return (
    <group ref={groupRef}>
      {flares.map((flare, index) => (
        <mesh
          key={index}
          position={[flare.x, flare.y, flare.z]}
          scale={[
            flare.scale * (1.5 + (index % 3) * 0.45),
            flare.scale,
            1,
          ]}
          material={material}
          renderOrder={6}
        >
          <planeGeometry args={[1, 1]} />
        </mesh>
      ))}
    </group>
  );
}

function CinematicPostFX({
  storyState,
  reducedMotion,
}: {
  storyState: MutableRefObject<StoryState>;
  reducedMotion: boolean;
}) {
  const chromaticOffset = useMemo(() => new Vector2(0.0007, 0.00035), []);
  const { gl } = useThree();
  const rendererRef = useRef(gl);

  useEffect(
    () => () => {
      rendererRef.current.toneMappingExposure = 1;
    },
    [gl],
  );

  useFrame(() => {
    const progress = storyState.current.progress;
    const velocity = Math.min(
      Math.abs(storyState.current.scrollVelocity),
      1.4,
    );
    const vortexFlash = smoothRange(progress, 0.68, 0.74, 0.82, 0.89);
    const roomFlash = smoothRange(progress, 0.79, 0.835, 0.9, 0.96);
    const aberration = reducedMotion
      ? 0.00025
      : 0.00055 + velocity * 0.00115 + vortexFlash * 0.0008;
    chromaticOffset.set(aberration, aberration * 0.46);
    rendererRef.current.toneMappingExposure =
      0.88 + vortexFlash * 0.18 + roomFlash * 0.24 + velocity * 0.08;
  });

  return (
    <EffectComposer multisampling={0} resolutionScale={0.84}>
      <Bloom
        mipmapBlur
        intensity={1.72}
        luminanceThreshold={0.24}
        luminanceSmoothing={0.28}
        radius={0.72}
      />
      <ChromaticAberration
        offset={chromaticOffset}
        radialModulation
        modulationOffset={0.2}
      />
      <Noise
        premultiply
        blendFunction={BlendFunction.SOFT_LIGHT}
        opacity={0.026}
      />
      <Vignette eskil={false} offset={0.12} darkness={0.52} />
    </EffectComposer>
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
  const shardRef = useRef<Group>(null);
  const contactFarRef = useRef<Group>(null);
  const contactMidRef = useRef<Group>(null);
  const contactFrontRef = useRef<Group>(null);
  const contactStickerRef = useRef<Group>(null);
  const corridorKeyLightRef = useRef<PointLight>(null);
  const corridorFillLightRef = useRef<PointLight>(null);
  const portalLightRef = useRef<PointLight>(null);
  const lastContactClick = useRef(Number.NEGATIVE_INFINITY);
  const contactKick = useRef(0);
  const { scene } = useThree();
  const [corridorGltf, portalRoomGltf, portalShardsGltf] = useLoader(
    GLTFLoader,
    [
      "/models/lusion-corridor-module-v02.glb",
      "/models/lusion-portal-room-v02.glb",
      "/models/lusion-portal-shards-v02.glb",
    ],
  );
  const contactStickerTextureSource = useLoader(
    TextureLoader,
    "/projects/contact-stickers-dense-v2.png",
  );
  const contactStickerTexture = useMemo(() => {
    const texture = contactStickerTextureSource.clone();
    texture.colorSpace = SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }, [contactStickerTextureSource]);

  const tunnelFrames = useMemo(
    () =>
      Array.from({ length: 24 }, (_, index) => ({
        z: -index * 1.1 + 2.5,
        twist: (index % 2 === 0 ? 1 : -1) * index * 0.018,
        scale: 1 + index * 0.004,
      })),
    [],
  );
  const tunnelBlocks = useMemo(
    () =>
      Array.from({ length: 58 }, (_, index) => ({
        x: (seededRandom(index + 200) - 0.5) * 10.5,
        y: (seededRandom(index + 410) - 0.5) * 6.2,
        z: -seededRandom(index + 630) * 24 + 3,
        sx: 0.12 + seededRandom(index + 800) * 0.5,
        sy: 0.08 + seededRandom(index + 920) * 0.4,
        sz: 0.18 + seededRandom(index + 1030) * 1.2,
      })),
    [],
  );
  const speedStreaks = useMemo(
    () =>
      Array.from({ length: 74 }, (_, index) => {
        const side = seededRandom(index + 1110) > 0.5 ? 1 : -1;
        const vertical = seededRandom(index + 1130) > 0.5;
        const edge = 1.45 + seededRandom(index + 1160) * 2.65;
        return {
          x: vertical
            ? side * edge
            : (seededRandom(index + 1180) - 0.5) * 7.4,
          y: vertical
            ? (seededRandom(index + 1210) - 0.5) * 4.5
            : side * (1.2 + seededRandom(index + 1240) * 1.3),
          z: -seededRandom(index + 1270) * 25 + 3,
          width: 0.012 + seededRandom(index + 1300) * 0.026,
          length: 0.5 + seededRandom(index + 1330) * 2.8,
          warm: index % 4 === 0,
        };
      }),
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
  const portalShards = useMemo(
    () =>
      Array.from({ length: 58 }, (_, index) => {
        const angle = seededRandom(index + 3110) * Math.PI * 2;
        const radius = 0.55 + seededRandom(index + 3150) * 2.65;
        const verticalBias = (seededRandom(index + 3190) - 0.5) * 3.9;
        return {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius * 0.56 + verticalBias * 0.42,
          z: -1.4 - seededRandom(index + 3230) * 3.6,
          dx: Math.cos(angle) * (1.4 + seededRandom(index + 3270) * 3.8),
          dy:
            Math.sin(angle) * (0.9 + seededRandom(index + 3310) * 2.6) +
            verticalBias * 0.38,
          dz: 1.3 + seededRandom(index + 3350) * 5.8,
          scale: 0.12 + seededRandom(index + 3390) * 0.38,
          rx: seededRandom(index + 3430) * Math.PI,
          ry: seededRandom(index + 3470) * Math.PI,
          rz: seededRandom(index + 3510) * Math.PI,
        };
      }),
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
        emissiveIntensity: 0.62,
        roughness: 0.28,
        metalness: 0.64,
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
      tunnelLightSecondary: new MeshBasicMaterial({
        color: "#55e9ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      tunnelGlass: new MeshPhysicalMaterial({
        color: "#bceeff",
        emissive: "#153244",
        emissiveIntensity: 0.4,
        roughness: 0.08,
        metalness: 0.08,
        transmission: 0.86,
        thickness: 0.34,
        ior: 1.42,
        dispersion: 0.62,
        iridescence: 0.28,
        iridescenceIOR: 1.34,
        iridescenceThicknessRange: [120, 540],
        transparent: true,
        opacity: 0,
        depthWrite: false,
        side: DoubleSide,
      }),
      speedCool: new MeshBasicMaterial({
        color: "#78e8ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      speedWarm: new MeshBasicMaterial({
        color: "#ff4f92",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      leanShell: new MeshBasicMaterial({
        color: "#ff2f9f",
        wireframe: true,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      leanNode: new MeshBasicMaterial({
        color: "#ffb6ec",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      voyaRing: new MeshBasicMaterial({
        color: "#55b8ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      voyaCore: new MeshBasicMaterial({
        color: "#b8e8ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      portalSurface: new MeshPhysicalMaterial({
        color: "#0626e7",
        emissive: "#071b93",
        emissiveIntensity: 1.35,
        roughness: 0.2,
        metalness: 0.12,
        transmission: 0.12,
        thickness: 0.46,
        ior: 1.34,
        dispersion: 0.24,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        side: DoubleSide,
      }),
      portalPattern: new MeshBasicMaterial({
        color: "#b8c5ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        side: DoubleSide,
        toneMapped: false,
      }),
      portalCore: new MeshBasicMaterial({
        color: "#cde7ff",
        transparent: true,
        opacity: 0,
        depthWrite: false,
        side: DoubleSide,
        blending: AdditiveBlending,
        toneMapped: false,
      }),
      shardGlass: new MeshPhysicalMaterial({
        color: "#83d9ff",
        emissive: "#1668d6",
        emissiveIntensity: 1.1,
        roughness: 0.045,
        metalness: 0.08,
        transmission: 0.82,
        thickness: 0.32,
        ior: 1.46,
        dispersion: 0.78,
        iridescence: 0.4,
        iridescenceIOR: 1.42,
        iridescenceThicknessRange: [90, 620],
        transparent: true,
        opacity: 0,
        depthWrite: false,
        side: DoubleSide,
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
  const corridorModuleAsset = useMemo(
    () =>
      mergeAssetByMaterial(corridorGltf.scene, (name) => {
        if (name.includes("Glass")) return materials.tunnelGlass;
        if (name.includes("Light_A")) return materials.tunnelLight;
        if (name.includes("Light_B")) return materials.tunnelLightSecondary;
        return materials.tunnel;
      }),
    [corridorGltf.scene, materials],
  );
  const corridorModules = useMemo(
    () =>
      tunnelFrames.map(() => corridorModuleAsset.clone(true)),
    [corridorModuleAsset, tunnelFrames],
  );
  const portalRoomAsset = useMemo(
    () =>
      mergeAssetByMaterial(portalRoomGltf.scene, (name) => {
        if (name.includes("CoreRing")) return null;
        if (name.includes("Pattern")) return materials.portalPattern;
        if (
          name.includes("Aperture") ||
          name.includes("Core") ||
          name.includes("BackReflector")
        ) {
          return materials.portalCore;
        }
        return materials.portalSurface;
      }),
    [materials, portalRoomGltf.scene],
  );
  const portalShardGeometries = useMemo(() => {
    const geometries: BufferGeometry[] = [];
    portalShardsGltf.scene.traverse((object) => {
      if (object instanceof Mesh) geometries.push(object.geometry.clone());
    });
    return geometries;
  }, [portalShardsGltf.scene]);
  const materialsRef = useRef(materials);
  const sceneRef = useRef(scene);
  const stickerTiles = useMemo(
    () =>
      [
        { offset: [0, 0.5], position: [-2.975, 1.6725] },
        { offset: [0.5, 0.5], position: [2.975, 1.6725] },
        { offset: [0, 0], position: [-2.975, -1.6725] },
        { offset: [0.5, 0], position: [2.975, -1.6725] },
      ].map((tile, index) => {
        const texture = contactStickerTexture.clone();
        texture.repeat.set(0.5, 0.5);
        texture.offset.set(tile.offset[0], tile.offset[1]);
        texture.needsUpdate = true;
        return {
          ...tile,
          kick: [
            (index % 2 === 0 ? -1 : 1) * (0.5 + index * 0.08),
            (index < 2 ? 1 : -1) * (0.3 + index * 0.05),
            (index % 2 === 0 ? -1 : 1) * 0.13,
          ],
          material: new MeshBasicMaterial({
            map: texture,
            transparent: true,
            opacity: 0,
            depthWrite: false,
            toneMapped: false,
          }),
          texture,
        };
      }),
    [contactStickerTexture],
  );
  const stickerTilesRef = useRef(stickerTiles);

  useEffect(
    () => () => {
      Object.values(materials).forEach((material) => material.dispose());
      corridorModuleAsset.traverse((object) => {
        if (object instanceof Mesh) object.geometry.dispose();
      });
      portalRoomAsset.traverse((object) => {
        if (object instanceof Mesh) object.geometry.dispose();
      });
      portalShardGeometries.forEach((geometry) => geometry.dispose());
      stickerTiles.forEach((tile) => {
        tile.material.dispose();
        tile.texture.dispose();
      });
      contactStickerTexture.dispose();
    },
    [
      contactStickerTexture,
      corridorModuleAsset,
      materials,
      portalRoomAsset,
      portalShardGeometries,
      stickerTiles,
    ],
  );

  useFrame((state, delta) => {
    const frameMaterials = materialsRef.current;
    const frameScene = sceneRef.current;
    const progress = storyState.current.progress;
    const pointerX = reducedMotion ? 0 : pointerTarget.current.x;
    const pointerY = reducedMotion ? 0 : pointerTarget.current.y;
    const velocity = storyState.current.scrollVelocity;
    const engineeringAlpha = smoothRange(
      progress,
      0.22,
      0.29,
      0.7,
      0.79,
    );
    const leanmateAlpha = smoothRange(progress, 0.64, 0.685, 0.75, 0.81);
    const voyaAlpha = smoothRange(progress, 0.68, 0.715, 0.77, 0.815);
    const blueRoomAlpha = smoothRange(progress, 0.775, 0.815, 0.925, 0.97);
    const shardAlpha = smoothRange(progress, 0.685, 0.72, 0.785, 0.835);
    const shardBurst = MathUtils.smoothstep(progress, 0.72, 0.81);
    const contactAlpha = MathUtils.smoothstep(progress, 0.88, 0.97);

    sampleTimelineBackground(progress, TIMELINE_BACKGROUND);
    if (frameScene.background instanceof Color) {
      frameScene.background.copy(TIMELINE_BACKGROUND);
    }
    if (frameScene.fog) {
      frameScene.fog.color.copy(TIMELINE_BACKGROUND);
    }

    const redBlend = MathUtils.smoothstep(progress, 0.46, 0.56);
    const greenBlend = MathUtils.smoothstep(progress, 0.57, 0.64);
    const magentaBlend = MathUtils.smoothstep(progress, 0.65, 0.72);
    if (progress < 0.57) {
      frameMaterials.tunnel.color.lerpColors(
        TUNNEL_DARK,
        TUNNEL_RED_DARK,
        redBlend,
      );
      frameMaterials.tunnel.emissive.lerpColors(
        TUNNEL_WHITE_EMISSIVE,
        TUNNEL_RED_EMISSIVE,
        redBlend,
      );
      frameMaterials.tunnelLight.color.lerpColors(
        TUNNEL_WHITE,
        TUNNEL_RED,
        redBlend,
      );
      frameMaterials.tunnelLightSecondary.color.lerpColors(
        TUNNEL_WHITE,
        TUNNEL_CYAN,
        redBlend,
      );
    } else if (progress < 0.65) {
      frameMaterials.tunnel.color.lerpColors(
        TUNNEL_RED_DARK,
        TUNNEL_GREEN_DARK,
        greenBlend,
      );
      frameMaterials.tunnel.emissive.lerpColors(
        TUNNEL_RED_EMISSIVE,
        TUNNEL_GREEN_EMISSIVE,
        greenBlend,
      );
      frameMaterials.tunnelLight.color.lerpColors(
        TUNNEL_RED,
        TUNNEL_GREEN,
        greenBlend,
      );
      frameMaterials.tunnelLightSecondary.color.lerpColors(
        TUNNEL_CYAN,
        TUNNEL_GREEN,
        greenBlend,
      );
    } else {
      frameMaterials.tunnel.color.lerpColors(
        TUNNEL_GREEN_DARK,
        TUNNEL_MAGENTA_DARK,
        magentaBlend,
      );
      frameMaterials.tunnel.emissive.lerpColors(
        TUNNEL_GREEN_EMISSIVE,
        TUNNEL_MAGENTA_EMISSIVE,
        magentaBlend,
      );
      frameMaterials.tunnelLight.color.lerpColors(
        TUNNEL_GREEN,
        TUNNEL_MAGENTA,
        magentaBlend,
      );
      frameMaterials.tunnelLightSecondary.color.lerpColors(
        TUNNEL_GREEN,
        TUNNEL_RED,
        magentaBlend,
      );
    }

    frameMaterials.tunnel.opacity = engineeringAlpha * 0.72;
    frameMaterials.tunnelLight.opacity = engineeringAlpha * 0.48;
    frameMaterials.tunnelLightSecondary.opacity = engineeringAlpha * 0.42;
    frameMaterials.tunnelGlass.opacity = engineeringAlpha * 0.14;
    frameMaterials.speedCool.opacity =
      engineeringAlpha * (0.22 + Math.min(Math.abs(velocity), 1) * 0.42);
    frameMaterials.speedWarm.opacity =
      engineeringAlpha *
      MathUtils.smoothstep(progress, 0.46, 0.58) *
      (0.16 + Math.min(Math.abs(velocity), 1) * 0.34);
    frameMaterials.leanShell.opacity = leanmateAlpha * 0.28;
    frameMaterials.leanNode.opacity = leanmateAlpha * 0.86;
    frameMaterials.voyaRing.opacity = voyaAlpha * 0.2;
    frameMaterials.voyaCore.opacity = voyaAlpha * 0.38;
    frameMaterials.portalSurface.opacity = blueRoomAlpha * 0.96;
    frameMaterials.portalPattern.opacity = blueRoomAlpha * 0.86;
    frameMaterials.portalCore.opacity = blueRoomAlpha * 0.94;
    frameMaterials.shardGlass.opacity = shardAlpha * 0.76;
    frameMaterials.contactFar.opacity = contactAlpha * 0.42;
    frameMaterials.contactMid.opacity = contactAlpha * 0.66;
    frameMaterials.contactFront.opacity = contactAlpha * 0.84;
    stickerTilesRef.current.forEach((tile) => {
      tile.material.opacity = contactAlpha;
    });

    if (engineeringRef.current) {
      engineeringRef.current.visible = engineeringAlpha > 0.01;
      engineeringRef.current.position.z = velocity * 0.34;
      engineeringRef.current.rotation.z = MathUtils.damp(
        engineeringRef.current.rotation.z,
        pointerX * 0.018 + (progress - 0.3) * 0.12,
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

    const corridorLightZ = MathUtils.lerp(
      5.8,
      -9.2,
      MathUtils.smoothstep(progress, 0.24, 0.76),
    );
    if (corridorKeyLightRef.current) {
      corridorKeyLightRef.current.visible = engineeringAlpha > 0.01;
      corridorKeyLightRef.current.position.set(
        2.4 + pointerX * 0.25,
        1.35 + pointerY * 0.18,
        corridorLightZ,
      );
      corridorKeyLightRef.current.color.copy(
        frameMaterials.tunnelLight.color,
      );
      corridorKeyLightRef.current.intensity =
        engineeringAlpha * (8.6 + Math.min(Math.abs(velocity), 1) * 4.2);
    }
    if (corridorFillLightRef.current) {
      corridorFillLightRef.current.visible = engineeringAlpha > 0.01;
      corridorFillLightRef.current.position.set(
        -2.6 - pointerX * 0.2,
        -1.2 - pointerY * 0.16,
        corridorLightZ - 1.7,
      );
      corridorFillLightRef.current.color.copy(
        frameMaterials.tunnelLightSecondary.color,
      );
      corridorFillLightRef.current.intensity =
        engineeringAlpha * (6.2 + Math.min(Math.abs(velocity), 1) * 3.1);
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
      leanmateRef.current.rotation.y += reducedMotion ? 0 : delta * 0.08;
      leanmateRef.current.rotation.z =
        (progress - 0.68) * 1.2 + pointerX * 0.035;
    }

    if (voyaRef.current) {
      voyaRef.current.visible = Math.max(voyaAlpha, blueRoomAlpha) > 0.01;
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
      voyaRef.current.rotation.z = MathUtils.damp(
        voyaRef.current.rotation.z,
        reducedMotion
          ? 0
          : pointerX * 0.018 + (progress - 0.82) * 0.065,
        3.4,
        delta,
      );
    }
    if (portalLightRef.current) {
      portalLightRef.current.visible =
        Math.max(voyaAlpha, blueRoomAlpha) > 0.01;
      portalLightRef.current.position.set(
        1.2 + pointerX * 0.5,
        0.8 + pointerY * 0.3,
        2.2,
      );
      portalLightRef.current.intensity =
        Math.max(voyaAlpha, blueRoomAlpha) * (7.8 + shardBurst * 4.2);
    }

    if (shardRef.current) {
      shardRef.current.visible = shardAlpha > 0.01;
      shardRef.current.position.x = -pointerX * 0.18;
      shardRef.current.position.y = -pointerY * 0.12;
      shardRef.current.children.forEach((child, index) => {
        const shard = portalShards[index];
        if (!shard) return;
        const delay = MathUtils.clamp(
          shardBurst * 1.35 - (index % 9) * 0.035,
          0,
          1,
        );
        const easedBurst = delay * delay * (3 - 2 * delay);
        child.position.set(
          shard.x + shard.dx * easedBurst,
          shard.y + shard.dy * easedBurst,
          shard.z + shard.dz * easedBurst,
        );
        child.rotation.set(
          shard.rx + easedBurst * (1.8 + (index % 4) * 0.34),
          shard.ry + easedBurst * (2.2 + (index % 5) * 0.29),
          shard.rz + easedBurst * (1.4 + (index % 3) * 0.42),
        );
      });
    }

    if (
      contactAlpha > 0.12 &&
      pointerTarget.current.clickAt > lastContactClick.current
    ) {
      lastContactClick.current = pointerTarget.current.clickAt;
      contactKick.current = 1;
    }
    contactKick.current = MathUtils.damp(
      contactKick.current,
      0,
      2.35,
      delta,
    );
    if (contactStickerRef.current) {
      contactStickerRef.current.children.forEach((child, index) => {
        const tile = stickerTiles[index];
        if (!tile) return;
        const wobble = contactKick.current;
        child.position.set(
          tile.position[0] +
            tile.kick[0] * wobble +
            Math.sin(state.clock.elapsedTime * (5.4 + index)) *
              wobble *
              0.08,
          tile.position[1] +
            tile.kick[1] * wobble +
            Math.cos(state.clock.elapsedTime * (4.9 + index * 0.7)) *
              wobble *
              0.06,
          tile.kick[2] * wobble,
        );
        child.rotation.z =
          tile.kick[2] * wobble +
          Math.sin(state.clock.elapsedTime * 0.22 + index) * 0.004;
      });
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
        -pointerX * factor +
          Math.sin(state.clock.elapsedTime * (9 + index * 2.1)) *
            contactKick.current *
            factor *
            0.7,
        4.2 - index * 0.35,
        delta,
      );
      group.position.y = MathUtils.damp(
        group.position.y,
        -pointerY * factor * 0.64 +
          Math.cos(state.clock.elapsedTime * (8 + index * 1.7)) *
            contactKick.current *
            factor *
            0.46,
        4.2 - index * 0.35,
        delta,
      );
      group.rotation.y = MathUtils.damp(
        group.rotation.y,
        pointerX * factor * 0.05 +
          contactKick.current * factor * (index % 2 === 0 ? 0.18 : -0.14),
        3.8,
        delta,
      );
      group.rotation.x = MathUtils.damp(
        group.rotation.x,
        -pointerY * factor * 0.035 +
          contactKick.current * factor * (index - 1) * 0.12,
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
      <pointLight
        ref={corridorKeyLightRef}
        color="#eaf7ff"
        intensity={0}
        distance={12}
        decay={1.45}
      />
      <pointLight
        ref={corridorFillLightRef}
        color="#55e9ff"
        intensity={0}
        distance={11}
        decay={1.55}
      />
      <pointLight
        ref={portalLightRef}
        color="#3c94ff"
        intensity={0}
        distance={14}
        decay={1.35}
      />
      <group ref={engineeringRef}>
        {tunnelFrames.map((frame, index) => (
          <group
            key={index}
            position={[0, 0, frame.z]}
            rotation={[0, 0, frame.twist]}
            scale={frame.scale}
          >
            <primitive object={corridorModules[index]} dispose={null} />
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
        {speedStreaks.map((streak, index) => (
          <mesh
            key={`streak-${index}`}
            position={[streak.x, streak.y, streak.z]}
            scale={[streak.width, streak.width, streak.length]}
            material={
              streak.warm ? materials.speedWarm : materials.speedCool
            }
          >
            <boxGeometry />
          </mesh>
        ))}
      </group>

      <group ref={leanmateRef} position={[0, 0, -20.5]}>
        {Array.from({ length: 18 }, (_, index) => (
          <mesh
            key={index}
            position={[0, 0, -index * 0.34]}
            rotation={[
              Math.sin(index * 0.67) * 0.13,
              Math.cos(index * 0.51) * 0.12,
              index * 0.17,
            ]}
            scale={1 + index * 0.085}
            material={index % 3 === 0 ? materials.leanNode : materials.leanShell}
          >
            <torusGeometry
              args={[1.62, index % 3 === 0 ? 0.045 : 0.018, 5, 96]}
            />
          </mesh>
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
        position={[0, 0, -1.8]}
        rotation={[0.02, 0.04, 0]}
        scale={1.4}
      >
        <group position={[0, 0, -20]} scale={2.2}>
          {Array.from({ length: 14 }, (_, index) => (
            <mesh
              key={index}
              position={[0, 0, -index * 0.55]}
              rotation={[
                Math.sin(index * 0.7) * 0.08,
                Math.cos(index * 0.56) * 0.08,
                index * 0.18,
              ]}
              scale={1 + index * 0.092}
              material={index % 3 === 0 ? materials.voyaCore : materials.voyaRing}
            >
              <torusGeometry
                args={[1.5, index % 3 === 0 ? 0.035 : 0.015, 5, 92]}
              />
            </mesh>
          ))}
          <mesh position={[0, 0, -5.6]} material={materials.voyaCore}>
            <boxGeometry args={[1.3, 1.3, 0.08]} />
          </mesh>
        </group>
        <primitive
          object={portalRoomAsset}
          position={[0, 0, -0.35]}
          scale={1.45}
          dispose={null}
        />
      </group>

      <group ref={shardRef} position={[0, 0, -20.4]} scale={1.8}>
        {portalShards.map((shard, index) => (
          <mesh
            key={`portal-shard-${index}`}
            position={[shard.x, shard.y, shard.z]}
            rotation={[shard.rx, shard.ry, shard.rz]}
            scale={[
              shard.scale * (2.1 + (index % 3) * 0.42),
              shard.scale * (3.2 + (index % 5) * 0.38),
              shard.scale * 0.82,
            ]}
            material={materials.shardGlass}
            geometry={
              portalShardGeometries[index % portalShardGeometries.length]
            }
          >
          </mesh>
        ))}
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
        <group ref={contactStickerRef} position={[0, 0, -0.35]}>
          {stickerTiles.map((tile, index) => (
            <mesh
              key={`sticker-tile-${index}`}
              position={[tile.position[0], tile.position[1], 0]}
              material={tile.material}
              renderOrder={8 + index}
            >
              <planeGeometry args={[5.95, 3.345]} />
            </mesh>
          ))}
        </group>
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
  const timelineSample = useRef(createMasterTimelineSample());

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
    const sceneFlash =
      document.querySelector<HTMLElement>("[data-scene-flash]");
    const progressProxy = { value: 0 };

    const syncDom = (progress: number) => {
      const stageProgress = progress * (DOM_STAGE_COUNT - 1);
      const activeStage = MathUtils.clamp(
        Math.round(stageProgress),
        0,
        DOM_STAGE_COUNT - 1,
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
        const distance = Math.abs(stageProgress - index);
        const alpha = reducedMotion
          ? 1
          : MathUtils.clamp(1.03 - distance * 1.4, 0.06, 1);
        gsap.set(copy, {
          autoAlpha: alpha,
          y: reducedMotion ? 0 : (index - stageProgress) * 36,
        });
      });
      if (sceneFlash) {
        const flashAlpha = smoothRange(progress, 0.72, 0.752, 0.762, 0.805);
        gsap.set(sceneFlash, {
          opacity: reducedMotion ? 0 : flashAlpha * 0.36,
          scale: 1 + flashAlpha * 0.06,
        });
      }
    };

    const context = gsap.context(() => {
      syncDom(0);
      if (reducedMotion) return;

      gsap.to(progressProxy, {
        value: 1,
        ease: "none",
        scrollTrigger: {
          trigger: story,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.68,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            storyState.current.progress = self.progress;
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
    const timeline = sampleMasterTimeline(progress, timelineSample.current);
    const pointer = pointerCurrent.current;
    const velocity = storyState.current.scrollVelocity;
    const contactBlend = MathUtils.smoothstep(progress, 0.9, 0.98);

    astronautPath.position.copy(timeline.astronautPosition);
    astronautPath.quaternion.copy(timeline.astronautQuaternion);
    astronautPath.scale.setScalar(timeline.astronautScale * 2.45);

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
      timeline.cameraPosition.x + pointer.x * cameraParallax,
      timeline.cameraPosition.y + pointer.y * cameraParallax * 0.62,
      timeline.cameraPosition.z + Math.abs(velocity) * 0.08,
    );
    pathCamera.lookAt(
      timeline.cameraLookAt.x + pointer.x * 0.045,
      timeline.cameraLookAt.y + pointer.y * 0.03,
      timeline.cameraLookAt.z,
    );
    const nextFov = timeline.cameraFov;
    if (Math.abs(pathCamera.fov - nextFov) > 0.01) {
      pathCamera.fov = nextFov;
      pathCamera.updateProjectionMatrix();
    }

    stationPath.position.copy(timeline.stationPosition);
    stationPath.quaternion.copy(timeline.stationQuaternion);
    stationPath.scale.setScalar(timeline.stationScale);
    stationMaterialRef.current.opacity =
      1 - MathUtils.smoothstep(progress, 0.08, 0.24);

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
        progress,
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
      <OpticalFlares
        pointerTarget={pointerTarget}
        storyState={storyState}
        reducedMotion={reducedMotion}
      />
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
      <CinematicPostFX
        storyState={storyState}
        reducedMotion={reducedMotion}
      />
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
      <div className="scene-flash" data-scene-flash aria-hidden="true" />
      <p className="scene-caption" aria-hidden="true">
        {sceneReady ? "MOTION SYSTEM ONLINE" : "LOADING MOTION SYSTEM"} · SCROLL /
        POINTER
      </p>
    </div>
  );
}
