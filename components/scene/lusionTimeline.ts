import {
  Color,
  Euler,
  MathUtils,
  Quaternion,
  Vector3,
} from "three";

type VectorTuple = readonly [number, number, number];

type TimelineKeyframe = {
  progress: number;
  astronaut: {
    position: VectorTuple;
    rotation: VectorTuple;
    scale: number;
  };
  camera: {
    position: VectorTuple;
    lookAt: VectorTuple;
    fov: number;
  };
  station: {
    position: VectorTuple;
    rotation: VectorTuple;
    scale: number;
  };
  background: string;
};

export type MasterTimelineSample = {
  astronautPosition: Vector3;
  astronautQuaternion: Quaternion;
  astronautScale: number;
  cameraPosition: Vector3;
  cameraLookAt: Vector3;
  cameraFov: number;
  stationPosition: Vector3;
  stationQuaternion: Quaternion;
  stationScale: number;
  background: Color;
};

const RAW_TIMELINE: readonly TimelineKeyframe[] = [
  {
    progress: 0,
    astronaut: {
      position: [2.55, -0.34, 0.38],
      rotation: [0.08, -0.12, -0.04],
      scale: 1.34,
    },
    camera: {
      position: [0, 0.05, 8.4],
      lookAt: [0.35, 0.06, -0.25],
      fov: 42,
    },
    station: {
      position: [1.35, 0.08, -2.7],
      rotation: [0.04, -0.18, -0.18],
      scale: 3.45,
    },
    background: "#020508",
  },
  {
    progress: 0.055,
    astronaut: {
      position: [1.72, -0.25, 0.36],
      rotation: [0.07, -0.05, -0.03],
      scale: 1.52,
    },
    camera: {
      position: [0.08, 0.04, 7.35],
      lookAt: [0.18, 0.06, -0.35],
      fov: 45,
    },
    station: {
      position: [0.72, -0.02, -3.05],
      rotation: [0.02, -0.04, -0.08],
      scale: 3.7,
    },
    background: "#020407",
  },
  {
    progress: 0.093,
    astronaut: {
      position: [0.72, -0.36, 0.62],
      rotation: [0.05, 0.06, 0.025],
      scale: 1.55,
    },
    camera: {
      position: [-0.08, 0.04, 6.42],
      lookAt: [0.12, 0.1, -0.42],
      fov: 43,
    },
    station: {
      position: [0.24, -0.22, -3.7],
      rotation: [0.04, 0.12, 0.04],
      scale: 3.9,
    },
    background: "#010306",
  },
  {
    progress: 0.167,
    astronaut: {
      position: [0.14, -0.86, -0.05],
      rotation: [0.28, 0.08, -0.16],
      scale: 1.3,
    },
    camera: {
      position: [-0.16, 0.12, 7.15],
      lookAt: [0.04, 0.12, -1.15],
      fov: 46,
    },
    station: {
      position: [-0.5, -0.46, -4.4],
      rotation: [0.08, 0.42, 0.1],
      scale: 3.5,
    },
    background: "#030407",
  },
  {
    progress: 0.241,
    astronaut: {
      position: [-0.18, 0.08, -4.1],
      rotation: [0.88, -0.18, -0.92],
      scale: 0.78,
    },
    camera: {
      position: [0.04, 0.12, 9.7],
      lookAt: [0, 0.06, -4.2],
      fov: 50,
    },
    station: {
      position: [2.2, -1.2, -6.4],
      rotation: [0.22, 0.88, -0.18],
      scale: 2.6,
    },
    background: "#050608",
  },
  {
    progress: 0.296,
    astronaut: {
      position: [0.28, -0.1, -5.2],
      rotation: [1.28, -0.38, -1.18],
      scale: 0.64,
    },
    camera: {
      position: [0.04, 0.06, 7.7],
      lookAt: [0, 0, -5.3],
      fov: 54,
    },
    station: {
      position: [3.4, -2.4, -8.5],
      rotation: [0.36, 1.38, -0.28],
      scale: 1.9,
    },
    background: "#05070a",
  },
  {
    progress: 0.37,
    astronaut: {
      position: [-0.42, 0.16, -7.35],
      rotation: [1.62, -0.68, -1.62],
      scale: 0.55,
    },
    camera: {
      position: [0.16, 0.03, 4.5],
      lookAt: [0.02, 0, -8.1],
      fov: 58,
    },
    station: {
      position: [4.8, -3.1, -11],
      rotation: [0.52, 1.9, -0.36],
      scale: 1.1,
    },
    background: "#070a0d",
  },
  {
    progress: 0.444,
    astronaut: {
      position: [0.36, -0.22, -10.1],
      rotation: [2.08, -0.92, -2.18],
      scale: 0.5,
    },
    camera: {
      position: [-0.2, 0.12, 1.1],
      lookAt: [0.02, 0, -11.4],
      fov: 62,
    },
    station: {
      position: [5.4, -4, -14],
      rotation: [0.72, 2.38, -0.42],
      scale: 0.65,
    },
    background: "#0a0f12",
  },
  {
    progress: 0.556,
    astronaut: {
      position: [-0.3, 0.12, -13.25],
      rotation: [2.52, -1.26, -2.72],
      scale: 0.48,
    },
    camera: {
      position: [0.26, -0.08, -2.1],
      lookAt: [-0.02, 0, -14.35],
      fov: 64,
    },
    station: {
      position: [6, -4.8, -17],
      rotation: [0.92, 2.82, -0.5],
      scale: 0.38,
    },
    background: "#16070b",
  },
  {
    progress: 0.63,
    astronaut: {
      position: [0.24, -0.16, -16.15],
      rotation: [2.82, -1.48, -3.06],
      scale: 0.47,
    },
    camera: {
      position: [-0.14, 0.1, -5.2],
      lookAt: [0.02, 0, -17.2],
      fov: 62,
    },
    station: {
      position: [6.5, -5.4, -20],
      rotation: [1.05, 3.16, -0.58],
      scale: 0.24,
    },
    background: "#06150d",
  },
  {
    progress: 0.704,
    astronaut: {
      position: [0.02, 0.02, -19.15],
      rotation: [3.08, -1.7, -3.38],
      scale: 0.52,
    },
    camera: {
      position: [0.02, 0, -8.1],
      lookAt: [0, 0, -20.4],
      fov: 59,
    },
    station: {
      position: [7, -6, -23],
      rotation: [1.16, 3.5, -0.64],
      scale: 0.16,
    },
    background: "#260019",
  },
  {
    progress: 0.759,
    astronaut: {
      position: [0, 0.04, -21.2],
      rotation: [3.2, -1.84, -3.54],
      scale: 0.62,
    },
    camera: {
      position: [0, 0, -10.1],
      lookAt: [0, 0, -22.2],
      fov: 55,
    },
    station: {
      position: [7.4, -6.4, -25],
      rotation: [1.26, 3.72, -0.72],
      scale: 0.1,
    },
    background: "#170617",
  },
  {
    progress: 0.815,
    astronaut: {
      position: [0.32, -0.18, -0.42],
      rotation: [1.68, -0.54, -1.48],
      scale: 0.82,
    },
    camera: {
      position: [0.2, 0.08, 6.65],
      lookAt: [0.04, 0.02, -1.15],
      fov: 50,
    },
    station: {
      position: [6, -6, -25],
      rotation: [1.2, 3.6, -0.7],
      scale: 0.06,
    },
    background: "#0a2d78",
  },
  {
    progress: 0.87,
    astronaut: {
      position: [-0.18, -0.25, -0.18],
      rotation: [0.82, -0.18, -0.62],
      scale: 0.92,
    },
    camera: {
      position: [-0.18, 0.02, 5.82],
      lookAt: [0.02, 0.02, -0.65],
      fov: 55,
    },
    station: {
      position: [5, -6, -25],
      rotation: [1.1, 3.4, -0.68],
      scale: 0.04,
    },
    background: "#04143b",
  },
  {
    progress: 0.926,
    astronaut: {
      position: [0.28, -2.2, 0.36],
      rotation: [0.14, 0.02, -0.06],
      scale: 1.45,
    },
    camera: {
      position: [0.02, 0.08, 7.2],
      lookAt: [0.18, 0.06, -0.32],
      fov: 45,
    },
    station: {
      position: [4.2, -6, -25],
      rotation: [1, 3.2, -0.64],
      scale: 0.03,
    },
    background: "#020306",
  },
  {
    progress: 1,
    astronaut: {
      position: [0.62, -2.5, 0.4],
      rotation: [0.02, 0.04, 0.01],
      scale: 1.48,
    },
    camera: {
      position: [0, 0.08, 8.05],
      lookAt: [0.36, 0.04, -0.42],
      fov: 43,
    },
    station: {
      position: [4, -6, -25],
      rotation: [0.9, 3, -0.62],
      scale: 0.02,
    },
    background: "#010204",
  },
] as const;

const TIMELINE = RAW_TIMELINE.map((keyframe) => ({
  ...keyframe,
  astronautPosition: new Vector3(...keyframe.astronaut.position),
  astronautQuaternion: new Quaternion().setFromEuler(
    new Euler(...keyframe.astronaut.rotation),
  ),
  cameraPosition: new Vector3(...keyframe.camera.position),
  cameraLookAt: new Vector3(...keyframe.camera.lookAt),
  stationPosition: new Vector3(...keyframe.station.position),
  stationQuaternion: new Quaternion().setFromEuler(
    new Euler(...keyframe.station.rotation),
  ),
  backgroundColor: new Color(keyframe.background),
}));

const VECTOR_SCRATCH = {
  p0: new Vector3(),
  p1: new Vector3(),
  p2: new Vector3(),
  p3: new Vector3(),
};

function findSegment(progress: number) {
  const clamped = MathUtils.clamp(progress, 0, 1);
  for (let index = 0; index < TIMELINE.length - 1; index += 1) {
    const current = TIMELINE[index];
    const next = TIMELINE[index + 1];
    if (clamped <= next.progress) {
      return {
        index,
        t: MathUtils.clamp(
          (clamped - current.progress) /
            Math.max(next.progress - current.progress, 0.0001),
          0,
          1,
        ),
      };
    }
  }
  return { index: TIMELINE.length - 2, t: 1 };
}

function sampleVector(
  index: number,
  t: number,
  pick: (keyframe: (typeof TIMELINE)[number]) => Vector3,
  target: Vector3,
) {
  const first = TIMELINE[Math.max(0, index - 1)];
  const current = TIMELINE[index];
  const next = TIMELINE[Math.min(TIMELINE.length - 1, index + 1)];
  const last = TIMELINE[Math.min(TIMELINE.length - 1, index + 2)];
  const { p0, p1, p2, p3 } = VECTOR_SCRATCH;
  p0.copy(pick(first));
  p1.copy(pick(current));
  p2.copy(pick(next));
  p3.copy(pick(last));

  const t2 = t * t;
  const t3 = t2 * t;
  target.set(
    0.5 *
      (2 * p1.x +
        (-p0.x + p2.x) * t +
        (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
        (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3),
    0.5 *
      (2 * p1.y +
        (-p0.y + p2.y) * t +
        (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
        (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3),
    0.5 *
      (2 * p1.z +
        (-p0.z + p2.z) * t +
        (2 * p0.z - 5 * p1.z + 4 * p2.z - p3.z) * t2 +
        (-p0.z + 3 * p1.z - 3 * p2.z + p3.z) * t3),
  );
}

export function createMasterTimelineSample(): MasterTimelineSample {
  return {
    astronautPosition: new Vector3(),
    astronautQuaternion: new Quaternion(),
    astronautScale: 1,
    cameraPosition: new Vector3(),
    cameraLookAt: new Vector3(),
    cameraFov: 42,
    stationPosition: new Vector3(),
    stationQuaternion: new Quaternion(),
    stationScale: 1,
    background: new Color(),
  };
}

export function sampleMasterTimeline(
  progress: number,
  target: MasterTimelineSample,
) {
  const { index, t } = findSegment(progress);
  const easedT = t * t * (3 - 2 * t);
  const current = TIMELINE[index];
  const next = TIMELINE[index + 1];

  sampleVector(
    index,
    easedT,
    (keyframe) => keyframe.astronautPosition,
    target.astronautPosition,
  );
  target.astronautQuaternion
    .copy(current.astronautQuaternion)
    .slerp(next.astronautQuaternion, easedT);
  target.astronautScale = MathUtils.lerp(
    current.astronaut.scale,
    next.astronaut.scale,
    easedT,
  );

  sampleVector(
    index,
    easedT,
    (keyframe) => keyframe.cameraPosition,
    target.cameraPosition,
  );
  sampleVector(
    index,
    easedT,
    (keyframe) => keyframe.cameraLookAt,
    target.cameraLookAt,
  );
  target.cameraFov = MathUtils.lerp(
    current.camera.fov,
    next.camera.fov,
    easedT,
  );

  sampleVector(
    index,
    easedT,
    (keyframe) => keyframe.stationPosition,
    target.stationPosition,
  );
  target.stationQuaternion
    .copy(current.stationQuaternion)
    .slerp(next.stationQuaternion, easedT);
  target.stationScale = MathUtils.lerp(
    current.station.scale,
    next.station.scale,
    easedT,
  );
  target.background
    .copy(current.backgroundColor)
    .lerp(next.backgroundColor, easedT);

  return target;
}

export function sampleTimelineBackground(progress: number, target: Color) {
  const { index, t } = findSegment(progress);
  const easedT = t * t * (3 - 2 * t);
  return target
    .copy(TIMELINE[index].backgroundColor)
    .lerp(TIMELINE[index + 1].backgroundColor, easedT);
}
