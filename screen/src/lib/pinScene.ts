// All the three.js for the 10,000-pin bed: one InstancedMesh (one draw call for every pin), orbit controls,
// and pins that slide toward their new heights each frame.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { reducedMotion } from "./motion";
import type { PinField } from "./pins";

const BED = 10;        // world units across the bed, whatever the resolution
const MAX = 100 * 100; // instance capacity
const STUB = 0.06;     // a pin at height 0 still shows as a short stub
const RISE = 2.2;      // world height of a fully raised pin
const EASE = 0.12;     // share of the remaining distance a pin moves per frame

export interface PinScene { show(field: PinField): void; dispose(): void }

export function createPinScene(host: HTMLElement): PinScene {
  const still = reducedMotion();
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#08090b");
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  camera.position.set(0, 10, 12);
  scene.add(new THREE.AmbientLight("#ffffff", 0.7));
  const sun = new THREE.DirectionalLight("#fff1dc", 1.8);
  sun.position.set(4, 12, 6);
  scene.add(sun);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.6, 0);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 6;
  controls.maxDistance = 26;
  controls.maxPolarAngle = Math.PI / 2.1; // never look from under the bed
  controls.autoRotate = !still;
  controls.autoRotateSpeed = 0.6;
  controls.addEventListener("start", () => { controls.autoRotate = false; }); // a visitor took over

  const geometry = new THREE.BoxGeometry(1, 1, 1);
  geometry.translate(0, 0.5, 0); // scale.y grows the pin up from the bed, not both ways
  const material = new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.1 });
  const mesh = new THREE.InstancedMesh(geometry, material, MAX);
  mesh.count = 0;
  mesh.frustumCulled = false;
  scene.add(mesh);

  let size = 0;
  let target = new Float32Array(0);
  let current = new Float32Array(0);
  const m = new THREE.Matrix4();
  const color = new THREE.Color();

  function place() {
    const pitch = BED / size;
    const w = pitch * 0.82;
    for (let r = 0; r < size; r++)
      for (let c = 0; c < size; c++) {
        const i = r * size + c;
        // row 0 at -z (far from the visitor), column 0 at -x (visitor's left)
        m.makeScale(w, STUB + current[i] * RISE, w);
        m.setPosition((c - (size - 1) / 2) * pitch, 0, (r - (size - 1) / 2) * pitch);
        mesh.setMatrixAt(i, m);
      }
    mesh.instanceMatrix.needsUpdate = true;
  }

  function show(field: PinField) {
    if (field.size !== size) {
      size = field.size;
      current = new Float32Array(size * size); // a new resolution rises from flat
      mesh.count = size * size;
    }
    target = field.heights;
    if (still) current = Float32Array.from(target);
    for (let i = 0; i < size * size; i++) {
      color.setRGB(field.colors[i * 3], field.colors[i * 3 + 1], field.colors[i * 3 + 2], THREE.SRGBColorSpace);
      mesh.setColorAt(i, color);
    }
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    place();
  }

  function resize() {
    const w = host.clientWidth || 1;
    const h = host.clientHeight || 1;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();

  let frame = 0;
  function tick() {
    frame = requestAnimationFrame(tick);
    let moving = false;
    for (let i = 0; i < size * size; i++) {
      const d = target[i] - current[i];
      if (Math.abs(d) > 0.001) { current[i] += d * EASE; moving = true; }
    }
    if (moving) place();
    controls.update();
    renderer.render(scene, camera);
  }
  tick();

  return {
    show,
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      mesh.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
