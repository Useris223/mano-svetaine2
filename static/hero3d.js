(async function () {
  const canvas = document.getElementById("hero3d");
  if (!canvas) return;

  const THREE = await import("https://unpkg.com/three@0.161.0/build/three.module.js");
  const { OrbitControls } = await import("https://unpkg.com/three@0.161.0/examples/jsm/controls/OrbitControls.js");

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x070a14, 6, 18);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.set(3.2, 1.7, 6.6);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.minDistance = 3.5;
  controls.maxDistance = 10;
  controls.target.set(0, 0.35, 0);

  // Lights
  const key = new THREE.DirectionalLight(0xffffff, 1.15);
  key.position.set(3, 4, 2);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x88aaff, 0.45);
  fill.position.set(-3, 2, 3);
  scene.add(fill);

  const rim = new THREE.PointLight(0xff66ff, 1.15, 20);
  rim.position.set(-2, 1.5, -2);
  scene.add(rim);

  const amb = new THREE.AmbientLight(0x7788aa, 0.28);
  scene.add(amb);

  // Floor
  const floorGeo = new THREE.CircleGeometry(3.4, 96);
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x0b1220, metalness: 0.15, roughness: 0.65 });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.06;
  scene.add(floor);

  // Product group
  const group = new THREE.Group();
  scene.add(group);

  const capsuleGeo = new THREE.CapsuleGeometry(0.55, 1.2, 10, 24);
  const capsuleMat = new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.22,
    metalness: 0.1,
    transmission: 0.55,
    thickness: 0.7,
    clearcoat: 0.9,
    clearcoatRoughness: 0.2
  });
  const capsule = new THREE.Mesh(capsuleGeo, capsuleMat);
  capsule.position.y = 0.72;
  group.add(capsule);

  const ringGeo = new THREE.TorusGeometry(0.92, 0.075, 18, 72);
  const ringMat = new THREE.MeshStandardMaterial({ color: 0x7c3aed, metalness: 0.65, roughness: 0.25 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2.25;
  ring.position.y = 0.42;
  group.add(ring);

  // Subtle particles
  const stars = new THREE.BufferGeometry();
  const N = 700;
  const pos = new Float32Array(N * 3);
  for (let i=0;i<N;i++){
    pos[i*3+0] = (Math.random()-0.5)*18;
    pos[i*3+1] = Math.random()*8;
    pos[i*3+2] = (Math.random()-0.5)*18;
  }
  stars.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.018, opacity: 0.5, transparent: true });
  const points = new THREE.Points(stars, starMat);
  scene.add(points);

  function resize(){
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  // Hover parallax on the card
  const card = document.getElementById("heroCard");
  let mouseX = 0, mouseY = 0;
  if (card) {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      mouseX = ((e.clientX - r.left) / r.width - 0.5);
      mouseY = ((e.clientY - r.top) / r.height - 0.5);
      // Tilt the card
      card.style.transform = `perspective(1100px) rotateX(${(-mouseY*8).toFixed(2)}deg) rotateY(${(mouseX*10).toFixed(2)}deg) translateY(-2px)`;
    });
    card.addEventListener("mouseleave", () => {
      mouseX = mouseY = 0;
      card.style.transform = `perspective(1100px) rotateX(0deg) rotateY(0deg) translateY(0px)`;
    });
  }

  let spin = true;
  document.getElementById("spin3d")?.addEventListener("click", () => {
    spin = !spin;
    window.toast?.(spin ? "3D spin ON 🌀" : "3D spin OFF 🛑");
  });

  function animate(){
    requestAnimationFrame(animate);
    controls.update();

    const t = performance.now() * 0.001;
    capsule.position.y = 0.72 + Math.sin(t*1.15)*0.06;
    ring.rotation.z += 0.004;

    // mouse parallax
    group.rotation.x = THREE.MathUtils.lerp(group.rotation.x, -mouseY * 0.18, 0.05);
    group.rotation.z = THREE.MathUtils.lerp(group.rotation.z,  mouseX * 0.10, 0.05);

    if (spin) group.rotation.y += 0.010;
    else group.rotation.y += (0.30 - group.rotation.y) * 0.03;

    points.rotation.y += 0.00055;

    renderer.render(scene, camera);
  }
  animate();
})();
