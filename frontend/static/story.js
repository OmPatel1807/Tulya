/**
 * Tulya (तुल्य) - Immersive 3D Story Engine
 * Visualizes Bilingual Statutory Drift with Three.js
 * Hardware Tier Scalability & Reduced-Motion Certified
 */

(function () {
  'use strict';

  // --- Configuration & State ---
  const urlParams = new URLSearchParams(window.location.search);
  const tierParam = parseInt(urlParams.get('tier') || '3', 10);
  const tier = Math.min(3, Math.max(1, isNaN(tierParam) ? 3 : tierParam));
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let isReducedMotion = prefersReducedMotion || urlParams.get('reduced_motion') === '1';

  let currentFPS = 60.0;
  let frameCount = 0;
  let lastTime = performance.now();
  let scrollProgress = 0.0;

  // Global diagnostics for automated Playwright verification
  window.__tier = tier;
  window.__currentFPS = 60.0;
  window.__storyProgress = 0.0;
  window.__isMotionActive = !isReducedMotion;
  window.__setReducedMotion = function(val) {
    isReducedMotion = !!val;
    window.__isMotionActive = !isReducedMotion;
  };

  // --- DOM Elements ---
  const canvas = document.getElementById('story-canvas');
  const fpsDisplay = document.getElementById('fps-display');
  const tierBadge = document.getElementById('tier-badge');
  const skipBtn = document.getElementById('skip-intro-btn');

  if (tierBadge) tierBadge.textContent = `Tier ${tier}`;
  if (skipBtn) {
    skipBtn.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = '/app';
    });
  }

  // --- Three.js Setup ---
  if (!window.THREE) {
    console.warn('Three.js not loaded. Falling back to 2D canvas mode.');
    return;
  }

  const THREE = window.THREE;
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x07090e, 0.04);

  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 0, 7.5);

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: tier >= 2,
    alpha: true,
    powerPreference: tier === 3 ? 'high-performance' : 'default'
  });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(tier === 3 ? Math.min(window.devicePixelRatio, 2) : 1);

  // --- Lights ---
  const ambientLight = new THREE.AmbientLight(0xffffff, tier === 1 ? 1.0 : 0.6);
  scene.add(ambientLight);

  const goldLight = new THREE.PointLight(0xf59e0b, 1.8, 15);
  goldLight.position.set(-3.5, 3, 3);
  scene.add(goldLight);

  const cyanLight = new THREE.PointLight(0x06b6d4, 1.8, 15);
  cyanLight.position.set(3.5, 3, 3);
  scene.add(cyanLight);

  const crimsonLight = new THREE.PointLight(0xef4444, 0.0, 10);
  crimsonLight.position.set(0, 0, 2);
  scene.add(crimsonLight);

  // --- 3D Objects: The Scales of Bilingual Justice ---
  const scalesGroup = new THREE.Group();
  scene.add(scalesGroup);

  // Central Pillar
  const pillarGeo = new THREE.CylinderGeometry(0.12, 0.22, 4.2, tier === 1 ? 8 : 24);
  const pillarMat = new THREE.MeshStandardMaterial({
    color: 0x222d42,
    roughness: 0.35,
    metalness: 0.8
  });
  const pillar = new THREE.Mesh(pillarGeo, pillarMat);
  scalesGroup.add(pillar);

  // Base Pedestal
  const baseGeo = new THREE.CylinderGeometry(1.2, 1.4, 0.3, tier === 1 ? 12 : 32);
  const baseMesh = new THREE.Mesh(baseGeo, pillarMat);
  baseMesh.position.y = -2.1;
  scalesGroup.add(baseMesh);

  // Balance Beam (Pivots as scroll progresses)
  const beamGroup = new THREE.Group();
  beamGroup.position.y = 1.6;
  scalesGroup.add(beamGroup);

  const beamGeo = new THREE.BoxGeometry(4.4, 0.08, 0.12);
  const beamMat = new THREE.MeshStandardMaterial({
    color: 0xf59e0b,
    metalness: 0.9,
    roughness: 0.2
  });
  const beamMesh = new THREE.Mesh(beamGeo, beamMat);
  beamGroup.add(beamMesh);

  // Left Pan (English side)
  const panGeo = new THREE.CylinderGeometry(0.8, 0.6, 0.1, tier === 1 ? 10 : 24);
  const panMatEn = new THREE.MeshStandardMaterial({
    color: 0x06b6d4,
    metalness: 0.8,
    roughness: 0.3,
    wireframe: tier === 1
  });
  const leftPan = new THREE.Mesh(panGeo, panMatEn);
  leftPan.position.set(-2.0, -1.2, 0);
  beamGroup.add(leftPan);

  // Right Pan (Hindi side)
  const panMatHi = new THREE.MeshStandardMaterial({
    color: 0xf59e0b,
    metalness: 0.8,
    roughness: 0.3,
    wireframe: tier === 1
  });
  const rightPan = new THREE.Mesh(panGeo, panMatHi);
  rightPan.position.set(2.0, -1.2, 0);
  beamGroup.add(rightPan);

  // Central Statutory Tablet (Cracks form as scroll increases)
  const tabletGeo = new THREE.BoxGeometry(1.4, 1.8, 0.18);
  const tabletMat = new THREE.MeshStandardMaterial({
    color: 0x111827,
    roughness: 0.6,
    metalness: 0.2
  });
  const tabletMesh = new THREE.Mesh(tabletGeo, tabletMat);
  tabletMesh.position.set(0, -0.2, 0.5);
  scalesGroup.add(tabletMesh);

  // Fissure / Crack Line Segments across Tablet
  const crackPoints = [
    new THREE.Vector3(-0.6, 0.7, 0.1),
    new THREE.Vector3(-0.2, 0.4, 0.1),
    new THREE.Vector3(-0.2, 0.4, 0.1),
    new THREE.Vector3(0.1, 0.1, 0.1),
    new THREE.Vector3(0.1, 0.1, 0.1),
    new THREE.Vector3(-0.1, -0.3, 0.1),
    new THREE.Vector3(-0.1, -0.3, 0.1),
    new THREE.Vector3(0.5, -0.7, 0.1),
    new THREE.Vector3(0.1, 0.1, 0.1),
    new THREE.Vector3(0.6, 0.3, 0.1),
    new THREE.Vector3(-0.2, 0.4, 0.1),
    new THREE.Vector3(-0.5, 0.1, 0.1)
  ];
  const crackGeo = new THREE.BufferGeometry().setFromPoints(crackPoints);
  const crackMat = new THREE.LineBasicMaterial({
    color: 0xef4444,
    linewidth: 3,
    transparent: true,
    opacity: 0.0
  });
  const crackLines = new THREE.LineSegments(crackGeo, crackMat);
  crackLines.position.copy(tabletMesh.position);
  crackLines.position.z += 0.01;
  scalesGroup.add(crackLines);

  // --- Ambient Particle System ---
  const particleCount = tier === 3 ? 800 : (tier === 2 ? 300 : 80);
  const particleGeo = new THREE.BufferGeometry();
  const particlePositions = new Float32Array(particleCount * 3);
  const particleVelocities = [];

  for (let i = 0; i < particleCount * 3; i += 3) {
    particlePositions[i] = (Math.random() - 0.5) * 12;
    particlePositions[i + 1] = (Math.random() - 0.5) * 10;
    particlePositions[i + 2] = (Math.random() - 0.5) * 8;
    particleVelocities.push({
      y: 0.003 + Math.random() * 0.006,
      x: (Math.random() - 0.5) * 0.002
    });
  }
  particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

  const particleMat = new THREE.PointsMaterial({
    color: 0xf59e0b,
    size: tier === 3 ? 0.04 : 0.06,
    transparent: true,
    opacity: tier === 1 ? 0.4 : 0.65
  });
  const particleSystem = new THREE.Points(particleGeo, particleMat);
  scene.add(particleSystem);

  // --- Scroll Tracking & Narrative Updates ---
  function updateScrollProgress() {
    const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
    scrollProgress = totalHeight > 0 ? Math.min(1.0, Math.max(0.0, window.scrollY / totalHeight)) : 0.0;
    window.__storyProgress = scrollProgress;

    // Apply scroll transformations to 3D scene
    // Beam tilt: reaches max asymmetric tilt at p=0.8
    const maxTilt = -0.32; // Radians tilt
    const tilt = scrollProgress < 0.8 
      ? (scrollProgress / 0.8) * maxTilt 
      : maxTilt + (scrollProgress - 0.8) * 5.0 * (-maxTilt * 0.8); // slight recovery at p=1.0

    beamGroup.rotation.z = tilt;

    // Crack opacity & crimson light intensity
    const crackOpacity = Math.min(1.0, Math.max(0.0, (scrollProgress - 0.15) / 0.65));
    crackMat.opacity = crackOpacity;
    crimsonLight.intensity = crackOpacity * 2.2;

    // Tablet slight forward rotation / crack separation
    tabletMesh.rotation.y = scrollProgress * 0.25;
    crackLines.rotation.y = tabletMesh.rotation.y;

    // Camera subtle dolly
    camera.position.z = 7.5 - scrollProgress * 1.5;
    camera.position.y = -scrollProgress * 0.4;
  }

  window.addEventListener('scroll', updateScrollProgress, { passive: true });
  updateScrollProgress();

  // --- Real Data Loading from Backend API ---
  async function loadRealDataCounters() {
    try {
      const res = await fetch('/api/samples');
      if (res.ok) {
        const data = await res.json();
        const sampleCount = data.total || (data.samples ? data.samples.length : 7);
        const sampleEl = document.getElementById('stat-acts-count');
        if (sampleEl) sampleEl.textContent = sampleCount;
      }
    } catch (err) {
      console.warn('API samples load non-critical fallback:', err);
    }
  }
  loadRealDataCounters();

  // --- Resize Handler ---
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // --- Render & FPS Loop ---
  function animate(now) {
    requestAnimationFrame(animate);

    // Calculate FPS
    frameCount++;
    if (now - lastTime >= 500) {
      currentFPS = Math.round((frameCount * 1000) / (now - lastTime));
      window.__currentFPS = currentFPS;
      if (fpsDisplay) fpsDisplay.textContent = `${currentFPS} FPS`;
      frameCount = 0;
      lastTime = now;
    }

    // Animation updates (if not reduced motion)
    if (!isReducedMotion) {
      // Gentle floating sway
      scalesGroup.rotation.y = Math.sin(now * 0.0008) * 0.12;

      // Particle upward drift
      const positions = particleGeo.attributes.position.array;
      for (let i = 1; i < particleCount * 3; i += 3) {
        const velIndex = Math.floor(i / 3);
        positions[i] += particleVelocities[velIndex].y;
        positions[i - 1] += particleVelocities[velIndex].x;

        if (positions[i] > 5) {
          positions[i] = -5;
        }
      }
      particleGeo.attributes.position.needsUpdate = true;
    } else {
      // Freeze particle motion and rotations in reduced-motion mode
      scalesGroup.rotation.y = 0;
    }

    renderer.render(scene, camera);
  }

  requestAnimationFrame(animate);

})();

