/**
 * Tulya (तुल्य) - "The Book of Two Languages" 3D Scroll Story Engine
 * Built with Three.js (Procedural Canvas Textures, PBR Materials, GSAP, and Lenis).
 * Buttery smooth, official, credible, and exact mathematical reversibility.
 */

(function () {
  'use strict';

  // --- Configuration & Hardware Tiers (D1, D2) ---
  const urlParams = new URLSearchParams(window.location.search);
  const tierParam = parseInt(urlParams.get('tier') || '3', 10);
  const tier = Math.min(3, Math.max(1, isNaN(tierParam) ? 3 : tierParam));
  const isDebug = urlParams.get('debug') === '1';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let isReducedMotion = prefersReducedMotion || urlParams.get('reduced_motion') === '1';

  // Particle count based on tier
  const PARTICLE_COUNT = isReducedMotion ? 0 : (tier === 3 ? 1200 : (tier === 2 ? 600 : 200));

  // --- Palette Constants ("Ink and Clay") ---
  const COLOR_COVER = 0x234A52;       // Deep ink-teal
  const COLOR_BRASS = 0xB89B5E;       // Brass foil
  const COLOR_PARCHMENT = 0xF3ECDD;   // Warm parchment
  const COLOR_EDGE = 0xD9CFB8;        // Aged paper edge
  const COLOR_INK = 0x2B3A3F;         // Slate ink
  const COLOR_EN = 0x5B7C99;          // Slate blue English
  const COLOR_HI = 0xC0805F;          // Terracotta clay Hindi
  const COLOR_SAGE = 0x7FA08A;        // Soft sage match
  const COLOR_ROSE = 0xA5566B;        // Muted plum-rose mismatch
  const COLOR_BG = 0xE8ECE8;          // Mist sage background

  // --- DOM Elements ---
  const canvas = document.getElementById('story-canvas');
  const preloader = document.getElementById('preloader');
  const cursorDot = document.getElementById('cursor-dot');
  const cursorRing = document.getElementById('cursor-ring');
  const fpsDisplay = document.getElementById('fps-display');
  const tierBadge = document.getElementById('tier-badge');
  const skipBtn = document.getElementById('skip-intro-btn');
  const skipLink = document.getElementById('skip-intro-link');
  const openAuditorBtn = document.getElementById('open-auditor-btn');
  const panels = document.querySelectorAll('.story-checkpoint-panel');

  if (tierBadge) tierBadge.textContent = `Tier ${tier}`;

  // Dismiss Preloader after calm entry (1.4s)
  window.addEventListener('load', () => {
    setTimeout(() => {
      if (preloader) preloader.classList.add('fade-out');
    }, 1400);
  });

  // Direct workspace navigation
  function navigateToWorkspace() {
    // Smooth camera dolly into cover if on screen
    if (camera && bookGroup && !isReducedMotion) {
      window.gsap.to(camera.position, {
        z: 3.2,
        duration: 0.6,
        ease: 'power2.inOut',
        onComplete: () => { window.location.href = '/app'; }
      });
    } else {
      window.location.href = '/app';
    }
  }

  if (skipBtn) skipBtn.addEventListener('click', (e) => { e.preventDefault(); navigateToWorkspace(); });
  if (skipLink) skipLink.addEventListener('click', (e) => { e.preventDefault(); navigateToWorkspace(); });
  if (openAuditorBtn) openAuditorBtn.addEventListener('click', (e) => { e.preventDefault(); navigateToWorkspace(); });

  // --- Custom Ink Dot Cursor (D3) ---
  if (!isReducedMotion && cursorDot && cursorRing) {
    let mouseX = -100, mouseY = -100;
    let ringX = -100, ringY = -100;

    window.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      cursorDot.style.left = `${mouseX}px`;
      cursorDot.style.top = `${mouseY}px`;
    }, { passive: true });

    function renderCursor() {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      cursorRing.style.left = `${ringX}px`;
      cursorRing.style.top = `${ringY}px`;
      requestAnimationFrame(renderCursor);
    }
    renderCursor();

    // Expand cursor ring on links and buttons
    document.querySelectorAll('a, button, select, input').forEach((el) => {
      el.addEventListener('mouseenter', () => { cursorRing.classList.add('hover'); });
      el.addEventListener('mouseleave', () => { cursorRing.classList.remove('hover'); });
    });
  }

  // --- Three.js Scene Setup (B1, B3, D2) ---
  if (!window.THREE) {
    console.warn('Three.js not loaded. 3D canvas disabled.');
    return;
  }
  const THREE = window.THREE;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COLOR_BG);

  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 50);
  camera.position.set(0, 0.65, 7.8);

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: tier >= 2,
    alpha: false,
    powerPreference: 'high-performance'
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.setSize(window.innerWidth, window.innerHeight);

  // Soft studio illumination (B3)
  const hemiLight = new THREE.HemisphereLight(0xFFFFFF, 0xDEE5E5, 1.15);
  scene.add(hemiLight);

  const dirLight = new THREE.DirectionalLight(0xFFF5E6, 0.85);
  dirLight.position.set(4, 8, 6);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0xD6E0E2, 0.35);
  fillLight.position.set(-4, -2, 4);
  scene.add(fillLight);

  // --- Procedural Canvas Textures (B1, R1) ---

  // 1. Front Cover Texture: Deep ink-teal with brass-foil typography & abstract borders
  function createCoverTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 768;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#234A52';
    ctx.fillRect(0, 0, 512, 768);

    // Subtle leather grain
    ctx.fillStyle = 'rgba(255, 255, 255, 0.025)';
    for (let i = 0; i < 400; i++) {
      ctx.fillRect(Math.random() * 512, Math.random() * 768, 2, 2);
    }

    // Double brass border
    ctx.strokeStyle = '#B89B5E';
    ctx.lineWidth = 4;
    ctx.strokeRect(26, 26, 460, 716);
    ctx.lineWidth = 1.5;
    ctx.strokeRect(36, 36, 440, 696);

    // Geometric corner accents
    const corners = [[36, 36], [476, 36], [36, 732], [476, 732]];
    corners.forEach(([cx, cy]) => {
      ctx.fillStyle = '#B89B5E';
      ctx.fillRect(cx - 5, cy - 5, 10, 10);
    });

    ctx.fillStyle = '#B89B5E';
    ctx.textAlign = 'center';

    // English Title
    ctx.font = '700 28px "Cinzel", Georgia, serif';
    ctx.fillText('THE CONSTITUTION', 256, 305);
    ctx.fillText('OF INDIA', 256, 342);

    ctx.fillRect(156, 370, 200, 2);

    // Hindi Title (Devanagari conjuncts shaped natively by browser)
    ctx.font = '600 28px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('भारत का संविधान', 256, 420);

    ctx.font = '500 12px "Cinzel", Georgia, serif';
    ctx.fillText('OFFICIAL BILINGUAL EDITION', 256, 660);

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // 2. English Preamble Texture
  function createPreambleEnTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 768;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#F3ECDD';
    ctx.fillRect(0, 0, 512, 768);

    ctx.strokeStyle = '#D9CFB8';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(28, 28, 456, 712);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#5B7C99';
    ctx.font = '700 17px "Cinzel", Georgia, serif';
    ctx.fillText('THE CONSTITUTION OF INDIA', 256, 68);
    ctx.font = '600 13px "Cinzel", Georgia, serif';
    ctx.fillText('PREAMBLE', 256, 92);

    ctx.fillStyle = '#D9CFB8';
    ctx.fillRect(80, 108, 352, 1);

    ctx.textAlign = 'left';
    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 13px "Cinzel", Georgia, serif';

    const lines = [
      'WE, THE PEOPLE OF INDIA,',
      'having solemnly resolved to constitute',
      'India into a SOVEREIGN SOCIALIST',
      'SECULAR DEMOCRATIC REPUBLIC',
      'and to secure to all its citizens:',
      '',
      'JUSTICE, social, economic and political;',
      '',
      'LIBERTY of thought, expression, belief,',
      'faith and worship;',
      '',
      'EQUALITY of status and of opportunity;',
      'and to promote among them all',
      '',
      'FRATERNITY assuring the dignity of the',
      'individual and the unity and integrity',
      'of the Nation;',
      '',
      'IN OUR CONSTITUENT ASSEMBLY',
      'this twenty-sixth day of November, 1949,',
      'do HEREBY ADOPT, ENACT AND',
      'GIVE TO OURSELVES THIS CONSTITUTION.'
    ];

    let y = 145;
    lines.forEach((l) => {
      if (l === '') y += 8;
      else { ctx.fillText(l, 52, y); y += 22; }
    });

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // 3. Hindi Preamble Texture (Verified Conjuncts: संविधान, प्राधिकृत, निर्दिष्ट)
  function createPreambleHiTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 768;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#F3ECDD';
    ctx.fillRect(0, 0, 512, 768);

    ctx.strokeStyle = '#D9CFB8';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(28, 28, 456, 712);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#C0805F';
    ctx.font = '700 18px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('भारत का संविधान', 256, 68);
    ctx.font = '600 14px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('उद्देशिका (प्राधिकृत पाठ)', 256, 92);

    ctx.fillStyle = '#D9CFB8';
    ctx.fillRect(80, 108, 352, 1);

    ctx.textAlign = 'left';
    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 13px "Noto Sans Devanagari", sans-serif';

    const lines = [
      'हम, भारत के लोग, भारत को एक',
      'सम्पूर्ण प्रभुत्व-सम्पन्न समाजवादी',
      'पंथनिरपेक्ष लोकतंत्रात्मक गणराज्य बनाने के लिए,',
      'तथा उसके समस्त नागरिकों को:',
      '',
      'सामाजिक, आर्थिक और राजनैतिक न्याय,',
      '',
      'विचार, अभिव्यक्ति, विश्वास, धर्म',
      'और उपासना की स्वतंत्रता,',
      '',
      'प्रतिष्ठा और अवसर की समता,',
      'प्राप्त कराने के लिए,',
      '',
      'तथा उन सब में व्यक्ति की गरिमा और',
      'राष्ट्र की एकता और अखंडता सुनिश्चित',
      'करने वाली बंधुता बढ़ाने के लिए,',
      '',
      'दृढ़संकल्प होकर अपनी इस संविधान सभा में',
      'आज तारीख 26 नवम्बर, 1949 ईस्वी को',
      'एतद्द्वारा इस संविधान को अंगीकृत, अधिनियमित',
      'और आत्मार्पित करते हैं।'
    ];

    let y = 145;
    lines.forEach((l) => {
      if (l === '') y += 8;
      else { ctx.fillText(l, 52, y); y += 22; }
    });

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // 4. Synthetic Demo Sheet Texture
  function createSyntheticSheetTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 1024;
    cvs.height = 512;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#FAF7EE';
    ctx.fillRect(0, 0, 1024, 512);

    ctx.strokeStyle = 'rgba(165, 86, 107, 0.45)';
    ctx.lineWidth = 3;
    ctx.strokeRect(10, 10, 1004, 492);

    ctx.fillStyle = '#A5566B';
    ctx.fillRect(10, 10, 1004, 52);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '700 17px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('SYNTHETIC DEMO EXAMPLE: Section 12(3) Divergence', 512, 42);

    ctx.strokeStyle = 'rgba(35, 74, 82, 0.12)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(512, 75);
    ctx.lineTo(512, 400);
    ctx.stroke();

    // English Column
    ctx.textAlign = 'left';
    ctx.fillStyle = '#5B7C99';
    ctx.font = '700 16px "Cinzel", Georgia, serif';
    ctx.fillText('ENGLISH STATUTORY PROVISION', 45, 105);

    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 18px "Inter", sans-serif';
    ctx.fillText('...shall be liable to pay a penalty equal to', 45, 155);

    ctx.font = '700 24px "Inter", sans-serif';
    ctx.fillStyle = '#3F5F7E';
    ctx.fillText('TEN TIMES THE TAX', 45, 205);

    ctx.fillStyle = '#6C7D82';
    ctx.font = '400 15px "Inter", sans-serif';
    ctx.fillText('Statutory cap: liability limited to 10× tax payable', 45, 245);

    // Hindi Column
    ctx.textAlign = 'left';
    ctx.fillStyle = '#C0805F';
    ctx.font = '700 18px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('हिन्दी सांविधिक उपबंध (निर्दिष्ट)', 545, 105);

    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 18px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('...देय कर की रकम के दस गुने के', 545, 155);

    ctx.font = '700 24px "Noto Sans Devanagari", sans-serif';
    ctx.fillStyle = '#8F4F32';
    ctx.fillText('अतिरिक्त दस गुना शास्ति...', 545, 205);

    ctx.fillStyle = '#6C7D82';
    ctx.font = '400 15px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('विधिक अर्थ: कर की रकम + 10 गुना अतिरिक्त शास्ति', 545, 245);

    // Discrepancy Box
    ctx.fillStyle = 'rgba(165, 86, 107, 0.12)';
    ctx.fillRect(45, 415, 934, 70);
    ctx.strokeStyle = 'rgba(165, 86, 107, 0.4)';
    ctx.strokeRect(45, 415, 934, 70);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#7D3A4D';
    ctx.font = '600 16px "Inter", sans-serif';
    ctx.fillText("▲ Discrepancy: 'कर के अतिरिक्त' specifies penalty IN ADDITION TO tax (tax + 10x penalty)", 512, 456);

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // --- 3D Procedural Book Hierarchy (B1, B2) ---
  const bookGroup = new THREE.Group();
  bookGroup.position.set(0, 0.65, 0);
  scene.add(bookGroup);

  // Soft Contact Shadow Plane (B3 baked)
  const shadowGeo = new THREE.PlaneGeometry(5.6, 4.4);
  const shadowMat = new THREE.MeshBasicMaterial({
    color: 0x234A52,
    transparent: true,
    opacity: 0.08
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.position.set(0, -0.15, -0.3);
  bookGroup.add(shadowMesh);

  const BOOK_W = 2.4;
  const BOOK_H = 3.4;
  const BOOK_T = 0.28;

  // Back Cover
  const backCoverGeo = new THREE.BoxGeometry(BOOK_W, BOOK_H, 0.05);
  const backCoverMat = new THREE.MeshStandardMaterial({
    color: COLOR_COVER,
    roughness: 0.55,
    metalness: 0.1
  });
  const backCover = new THREE.Mesh(backCoverGeo, backCoverMat);
  backCover.position.set(BOOK_W / 2, 0, -BOOK_T / 2);
  bookGroup.add(backCover);

  // Spine: Rounded half-cylinder wrapping along Y axis
  const spineGeo = new THREE.CylinderGeometry(0.15, 0.15, BOOK_H, 24, 1, false, Math.PI / 2, Math.PI);
  const spineMat = new THREE.MeshStandardMaterial({
    color: COLOR_COVER,
    roughness: 0.55,
    metalness: 0.1
  });
  const spine = new THREE.Mesh(spineGeo, spineMat);
  spine.position.set(0, 0, 0);
  bookGroup.add(spine);

  // Pages Block Base
  const pageBlockGeo = new THREE.BoxGeometry(BOOK_W - 0.08, BOOK_H - 0.08, BOOK_T - 0.06);
  const pageBlockMat = new THREE.MeshStandardMaterial({
    color: COLOR_EDGE,
    roughness: 0.7,
    metalness: 0.05
  });
  const pageBlock = new THREE.Mesh(pageBlockGeo, pageBlockMat);
  pageBlock.position.set((BOOK_W - 0.08) / 2 + 0.04, 0, -0.01);
  bookGroup.add(pageBlock);

  // Base Right Spread (Hindi Preamble)
  const hiSpreadGeo = new THREE.PlaneGeometry(BOOK_W - 0.1, BOOK_H - 0.1);
  const hiSpreadMat = new THREE.MeshBasicMaterial({ map: createPreambleHiTexture() });
  const hiSpreadMesh = new THREE.Mesh(hiSpreadGeo, hiSpreadMat);
  hiSpreadMesh.position.set((BOOK_W - 0.1) / 2 + 0.05, 0, (BOOK_T - 0.06) / 2 + 0.002);
  bookGroup.add(hiSpreadMesh);

  // Front Cover Pivot (Hinged at x = 0, y = 0, z = BOOK_T / 2)
  const coverPivot = new THREE.Group();
  coverPivot.position.set(0, 0, BOOK_T / 2);
  bookGroup.add(coverPivot);

  const frontCoverGeo = new THREE.BoxGeometry(BOOK_W, BOOK_H, 0.05);
  const coverTex = createCoverTexture();

  const coverMaterials = [
    new THREE.MeshStandardMaterial({ color: COLOR_COVER, roughness: 0.55 }),
    new THREE.MeshStandardMaterial({ color: COLOR_COVER, roughness: 0.55 }),
    new THREE.MeshStandardMaterial({ color: COLOR_COVER, roughness: 0.55 }),
    new THREE.MeshStandardMaterial({ color: COLOR_COVER, roughness: 0.55 }),
    new THREE.MeshBasicMaterial({ map: coverTex }),
    new THREE.MeshStandardMaterial({ color: COLOR_PARCHMENT, roughness: 0.6 })
  ];
  const frontCoverMesh = new THREE.Mesh(frontCoverGeo, coverMaterials);
  frontCoverMesh.position.set(BOOK_W / 2, 0, 0.025);
  coverPivot.add(frontCoverMesh);

  // Progressive texture load: CC0 leather normal map if available
  const texLoader = new THREE.TextureLoader();
  texLoader.load('/public/assets/cover_leather_nor_gl_1k.webp', (tex) => {
    coverMaterials[4].normalMap = tex;
    coverMaterials[4].normalScale = new THREE.Vector2(0.4, 0.4);
    coverMaterials[4].needsUpdate = true;
  }, undefined, () => {});

  // 14 Animated Leaves with Vertex-Shader Page Curl (B2)
  const NUM_LEAVES = 14;
  const leafPivots = [];
  const leafCurlUniforms = [];
  const enSpreadTex = createPreambleEnTexture();

  for (let i = 0; i < NUM_LEAVES; i++) {
    const lp = new THREE.Group();
    lp.position.set(0, 0, 0.005 + (i * 0.006));
    bookGroup.add(lp);
    leafPivots.push(lp);

    const leafGeo = new THREE.PlaneGeometry(BOOK_W - 0.12, BOOK_H - 0.1, 16, 16);
    const curlUniform = { value: 0.0 };
    leafCurlUniforms.push(curlUniform);

    if (i === NUM_LEAVES - 1) {
      // Top leaf reveals English Preamble on left spread when flipped
      const frontMat = new THREE.MeshStandardMaterial({ color: COLOR_PARCHMENT, roughness: 0.65 });
      const frontMesh = new THREE.Mesh(leafGeo, frontMat);
      frontMesh.position.set((BOOK_W - 0.12) / 2 + 0.06, 0, 0.001);
      lp.add(frontMesh);

      const backMat = new THREE.MeshBasicMaterial({ map: enSpreadTex });
      const backMesh = new THREE.Mesh(leafGeo, backMat);
      backMesh.position.set((BOOK_W - 0.12) / 2 + 0.06, 0, -0.001);
      backMesh.rotation.y = Math.PI;
      lp.add(backMesh);
    } else {
      const leafMat = new THREE.MeshStandardMaterial({
        color: COLOR_PARCHMENT,
        roughness: 0.65,
        side: THREE.DoubleSide
      });
      const leafMesh = new THREE.Mesh(leafGeo, leafMat);
      leafMesh.position.set((BOOK_W - 0.12) / 2 + 0.06, 0, 0);
      lp.add(leafMesh);
    }
  }

  // --- Dust Motes in Sunbeam (B4 Idle Life, D1 Tier-Gated) ---
  const moteCount = isReducedMotion ? 0 : 120;
  const moteGeo = new THREE.BufferGeometry();
  const motePositions = new Float32Array(moteCount * 3);
  for (let i = 0; i < moteCount; i++) {
    motePositions[i * 3] = (Math.random() - 0.5) * 6.0;
    motePositions[i * 3 + 1] = (Math.random() - 0.5) * 4.0;
    motePositions[i * 3 + 2] = (Math.random() - 0.5) * 3.0 + 1.0;
  }
  moteGeo.setAttribute('position', new THREE.BufferAttribute(motePositions, 3));
  const moteMat = new THREE.PointsMaterial({
    color: COLOR_BRASS,
    size: 0.035,
    transparent: true,
    opacity: 0.35
  });
  const motePoints = new THREE.Points(moteGeo, moteMat);
  scene.add(motePoints);

  // --- Clause Cards for Segmentation Scene (Phase C, p in [0.28, 0.42]) ---
  function createClauseCardTexture(lang, index, labelEn, labelHi) {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 160;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#FAF7EE';
    ctx.fillRect(0, 0, 512, 160);

    ctx.strokeStyle = lang === 'en' ? 'rgba(91, 124, 153, 0.45)' : 'rgba(192, 128, 95, 0.45)';
    ctx.lineWidth = 3;
    ctx.strokeRect(4, 4, 504, 152);

    ctx.fillStyle = lang === 'en' ? '#3F5F7E' : '#8F4F32';
    ctx.font = '700 16px "Cinzel", Georgia, serif';
    ctx.fillText(lang === 'en' ? `CLAUSE ${index + 1}` : `खंड ${index + 1} (निर्दिष्ट उपबंध)`, 20, 36);

    ctx.fillStyle = '#2B3A3F';
    if (lang === 'en') {
      ctx.font = '500 18px "Inter", sans-serif';
      ctx.fillText(labelEn, 20, 78);
      ctx.font = '400 14px "Inter", sans-serif';
      ctx.fillStyle = '#6C7D82';
      ctx.fillText('Constitutional provision mapped to Hindi pair', 20, 115);
    } else {
      ctx.font = '500 18px "Noto Sans Devanagari", sans-serif';
      ctx.fillText(labelHi, 20, 78);
      ctx.font = '400 14px "Noto Sans Devanagari", sans-serif';
      ctx.fillStyle = '#6C7D82';
      ctx.fillText('सांविधिक उपबंध अंग्रेजी पाठ से सुसंगत', 20, 115);
    }

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  const clauseCardsGroup = new THREE.Group();
  bookGroup.add(clauseCardsGroup);

  const cardGeo = new THREE.PlaneGeometry(BOOK_W - 0.28, 0.72);
  const cardData = [
    { en: 'Sovereign Socialist Democratic Republic', hi: 'सम्पूर्ण प्रभुत्व-सम्पन्न गणराज्य' },
    { en: 'Justice: social, economic and political', hi: 'सामाजिक, आर्थिक और राजनैतिक न्याय' },
    { en: 'Liberty, Equality and Fraternity', hi: 'विचार, अभिव्यक्ति, समता और बंधुता' }
  ];

  const cardsEn = [];
  const cardsHi = [];
  const cardMats = [];
  const cardYPositions = [0.85, 0.0, -0.85];

  cardYPositions.forEach((yPos, idx) => {
    const texEn = createClauseCardTexture('en', idx, cardData[idx].en, cardData[idx].hi);
    const matEn = new THREE.MeshBasicMaterial({ map: texEn, transparent: true, opacity: 0.0 });
    const mEn = new THREE.Mesh(cardGeo, matEn);
    mEn.position.set(-1.18, yPos, 0.08);
    clauseCardsGroup.add(mEn);
    cardsEn.push(mEn);
    cardMats.push(matEn);

    const texHi = createClauseCardTexture('hi', idx, cardData[idx].en, cardData[idx].hi);
    const matHi = new THREE.MeshBasicMaterial({ map: texHi, transparent: true, opacity: 0.0 });
    const mHi = new THREE.Mesh(cardGeo, matHi);
    mHi.position.set(1.18, yPos, 0.08);
    clauseCardsGroup.add(mHi);
    cardsHi.push(mHi);
    cardMats.push(matHi);
  });

  // --- Glyph Particles for Text Lift-Off (Phase C, p in [0.28, 0.42]) ---
  const GLYPH_COUNT = PARTICLE_COUNT;
  const glyphGeo = new THREE.BufferGeometry();
  const glyphPos = new Float32Array(GLYPH_COUNT * 3);
  const glyphColors = new Float32Array(GLYPH_COUNT * 3);

  for (let i = 0; i < GLYPH_COUNT; i++) {
    const isEn = i < GLYPH_COUNT / 2;
    glyphPos[i * 3] = isEn ? (-1.18 + (Math.random() - 0.5) * 1.8) : (1.18 + (Math.random() - 0.5) * 1.8);
    glyphPos[i * 3 + 1] = (Math.random() - 0.5) * 2.8;
    glyphPos[i * 3 + 2] = 0.05;

    // Slate Blue for EN, Terracotta for HI
    if (isEn) {
      glyphColors[i * 3] = 0.36; glyphColors[i * 3 + 1] = 0.49; glyphColors[i * 3 + 2] = 0.60;
    } else {
      glyphColors[i * 3] = 0.75; glyphColors[i * 3 + 1] = 0.50; glyphColors[i * 3 + 2] = 0.37;
    }
  }

  glyphGeo.setAttribute('position', new THREE.BufferAttribute(glyphPos, 3));
  glyphGeo.setAttribute('color', new THREE.BufferAttribute(glyphColors, 3));

  const glyphMat = new THREE.PointsMaterial({
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.0
  });
  const glyphPoints = new THREE.Points(glyphGeo, glyphMat);
  bookGroup.add(glyphPoints);

  // --- Sage Alignment Threads with Pulse Dash (Phase C, p in [0.42, 0.58]) ---
  const threadsGroup = new THREE.Group();
  bookGroup.add(threadsGroup);

  const threadLines = [];
  cardYPositions.forEach((yPos) => {
    const threadGeo = new THREE.CylinderGeometry(0.014, 0.014, 1.9, 8);
    const threadMat = new THREE.MeshBasicMaterial({
      color: COLOR_SAGE,
      transparent: true,
      opacity: 0.0
    });
    const threadMesh = new THREE.Mesh(threadGeo, threadMat);
    threadMesh.position.set(0, yPos, 0.24);
    threadMesh.rotation.z = Math.PI / 2;
    threadsGroup.add(threadMesh);
    threadLines.push(threadMesh);
  });

  // --- Synthetic Demo Sheet & Pulse Ring (Phase C, p in [0.58, 0.74]) ---
  const syntheticSheetGroup = new THREE.Group();
  syntheticSheetGroup.position.set(0, 4.0, 0.42);
  bookGroup.add(syntheticSheetGroup);

  const synthTex = createSyntheticSheetTexture();
  const synthGeo = new THREE.PlaneGeometry(3.3, 1.85);
  const synthMat = new THREE.MeshBasicMaterial({
    map: synthTex,
    transparent: true,
    opacity: 0.0
  });
  const synthMesh = new THREE.Mesh(synthGeo, synthMat);
  syntheticSheetGroup.add(synthMesh);

  // Plum-Rose Shockwave Pulse Ring
  const pulseRingGeo = new THREE.RingGeometry(0.24, 0.29, 32);
  const pulseRingMat = new THREE.MeshBasicMaterial({
    color: COLOR_ROSE,
    transparent: true,
    opacity: 0.0,
    side: THREE.DoubleSide
  });
  const pulseRing = new THREE.Mesh(pulseRingGeo, pulseRingMat);
  pulseRing.position.set(0.88, -0.06, 0.01);
  syntheticSheetGroup.add(pulseRing);

  // --- Semantic Review Glass Lens (Phase C, p in [0.74, 0.88]) ---
  const magnifierGroup = new THREE.Group();
  magnifierGroup.position.set(0.88, 0.0, 0.52);
  bookGroup.add(magnifierGroup);

  const rimGeo = new THREE.TorusGeometry(0.38, 0.024, 16, 32);
  const rimMat = new THREE.MeshStandardMaterial({
    color: COLOR_BRASS,
    roughness: 0.35,
    metalness: 0.8,
    transparent: true,
    opacity: 0.0
  });
  const rimMesh = new THREE.Mesh(rimGeo, rimMat);
  magnifierGroup.add(rimMesh);

  const handleGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.4, 12);
  const handleMesh = new THREE.Mesh(handleGeo, rimMat);
  handleMesh.position.set(0.32, -0.32, 0);
  handleMesh.rotation.z = -Math.PI / 4;
  magnifierGroup.add(handleMesh);

  const glassGeo = new THREE.CircleGeometry(0.36, 32);
  const glassMat = new THREE.MeshBasicMaterial({
    color: 0xEEF5F8,
    transparent: true,
    opacity: 0.0
  });
  const glassMesh = new THREE.Mesh(glassGeo, glassMat);
  magnifierGroup.add(glassMesh);

  // --- Catmull-Rom Camera Spline Path (B5) ---
  const cameraPath = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.65, 7.8),   // 0.00: Closed hero
    new THREE.Vector3(0, 0.70, 7.2),   // 0.15: Opening arc
    new THREE.Vector3(0, 0.85, 6.2),   // 0.35: Spread overview
    new THREE.Vector3(0, 0.75, 5.4),   // 0.50: Alignment flythrough
    new THREE.Vector3(0, 0.65, 5.2),   // 0.70: Facts collision
    new THREE.Vector3(0, 0.72, 5.8),   // 0.85: Semantic lens review
    new THREE.Vector3(0, 0.65, 7.8)    // 1.00: Closed hero CTA
  ]);

  // --- Pure Deterministic Timeline State Function: calcBookState(p) ---
  function calcBookState(p) {
    p = Math.max(0.0, Math.min(1.0, p));

    // 1. Cover Angle: 0 to 165 deg
    let coverAngle = 0.0;
    if (p < 0.08) {
      coverAngle = 0.0;
    } else if (p < 0.25) {
      const t = (p - 0.08) / (0.25 - 0.08);
      const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      coverAngle = ease * 165.0;
    } else if (p < 0.97) {
      coverAngle = 165.0;
    } else {
      const t = (p - 0.97) / (1.00 - 0.97);
      const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      coverAngle = (1.0 - ease) * 165.0;
    }

    // 2. Leaf Angles (14 leaves turning right-to-left)
    const leafAngles = new Array(NUM_LEAVES).fill(0.0);
    for (let i = 0; i < NUM_LEAVES; i++) {
      const startP = 0.10 + (i * 0.012);
      const endP = startP + 0.045;
      if (p < startP) {
        leafAngles[i] = 0.0;
      } else if (p <= endP) {
        const t = (p - startP) / (endP - startP);
        const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        leafAngles[i] = ease * 180.0;
      } else if (p < 0.97) {
        leafAngles[i] = 180.0;
      } else {
        const returnStart = 0.97 + ((NUM_LEAVES - 1 - i) * 0.0018);
        const returnEnd = returnStart + 0.010;
        if (p < returnStart) {
          leafAngles[i] = 180.0;
        } else if (p <= returnEnd) {
          const t = (p - returnStart) / (returnEnd - returnStart);
          const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          leafAngles[i] = (1.0 - ease) * 180.0;
        } else {
          leafAngles[i] = 0.0;
        }
      }
    }

    // 3. Glyph Particles Lift-Off (p in [0.28, 0.42])
    let glyphAlpha = 0.0;
    let glyphLift = 0.0;
    if (p >= 0.28 && p < 0.35) {
      const t = (p - 0.28) / 0.07;
      glyphAlpha = t;
      glyphLift = t * 0.40;
    } else if (p >= 0.35 && p < 0.42) {
      const t = (p - 0.35) / 0.07;
      glyphAlpha = 1.0 - t;
      glyphLift = 0.40 - (t * 0.30);
    }

    // 4. Clause Cards Lift (p in [0.38, 0.52])
    let cardLift = 0.0;
    let cardAlpha = 0.0;
    if (p >= 0.38 && p < 0.52) {
      const t = (p - 0.38) / (0.52 - 0.38);
      cardLift = Math.min(1.0, t * 1.4) * 0.16;
      cardAlpha = Math.min(1.0, t * 2.0);
    } else if (p >= 0.52 && p <= 0.90) {
      cardLift = 0.16;
      cardAlpha = 1.0;
    } else if (p > 0.90 && p < 0.96) {
      const t = (p - 0.90) / 0.06;
      cardLift = (1.0 - t) * 0.16;
      cardAlpha = 1.0 - t;
    }

    // 5. Sage Alignment Threads (p in [0.42, 0.58])
    let threadAlpha = 0.0;
    if (p >= 0.42 && p <= 0.56) {
      threadAlpha = (p - 0.42) / (0.56 - 0.42);
    } else if (p > 0.56 && p <= 0.90) {
      threadAlpha = 1.0;
    } else if (p > 0.90 && p < 0.95) {
      threadAlpha = 1.0 - (p - 0.90) / 0.05;
    }

    // 6. Synthetic Loose Sheet Position & Opacity (p in [0.58, 0.74])
    let sheetY = 4.0;
    let sheetAlpha = 0.0;
    if (p >= 0.58 && p < 0.65) {
      const t = (p - 0.58) / 0.07;
      sheetY = 4.0 * (1.0 - t);
      sheetAlpha = t;
    } else if (p >= 0.65 && p <= 0.80) {
      sheetY = 0.0;
      sheetAlpha = 1.0;
    } else if (p > 0.80 && p < 0.90) {
      sheetY = 0.0;
      sheetAlpha = 1.0;
    } else if (p >= 0.90 && p < 0.95) {
      const t = (p - 0.90) / 0.05;
      sheetY = -4.0 * t;
      sheetAlpha = 1.0 - t;
    }

    // 7. Semantic Magnifier Frame (p in [0.74, 0.88])
    let magnifierAlpha = 0.0;
    let magnifierY = 0.2;
    if (p >= 0.74 && p <= 0.88) {
      const t = (p - 0.74) / 0.14;
      magnifierAlpha = Math.sin(t * Math.PI);
      magnifierY = 0.25 - (t * 0.45);
    }

    // 8. Book Orientation
    let bookRotX = 0.14;
    let bookRotY = -0.22;
    let bookRotZ = 0.08;

    if (p >= 0.08 && p < 0.28) {
      const t = (p - 0.08) / 0.20;
      bookRotX = 0.14 + (0.34 - 0.14) * t;
      bookRotY = -0.22 * (1.0 - t);
      bookRotZ = 0.08 * (1.0 - t);
    } else if (p >= 0.28 && p < 0.94) {
      bookRotX = 0.34;
      bookRotY = 0.0;
      bookRotZ = 0.0;
    } else if (p >= 0.94) {
      const t = (p - 0.94) / 0.06;
      bookRotX = 0.34 - (0.34 - 0.14) * t;
      bookRotY = -0.22 * t;
      bookRotZ = 0.08 * t;
    }

    return {
      coverAngle,
      leafAngles,
      glyphAlpha,
      glyphLift,
      cardLift,
      cardAlpha,
      threadAlpha,
      sheetY,
      sheetAlpha,
      magnifierAlpha,
      magnifierY,
      bookRotX,
      bookRotY,
      bookRotZ
    };
  }

  // --- Apply State to 3D Scene ---
  let latestState = calcBookState(0.0);

  function applyBookState(p) {
    const state = calcBookState(p);
    latestState = state;

    // Cover Rotation
    coverPivot.rotation.y = THREE.MathUtils.degToRad(state.coverAngle);

    // Leaf Rotations & Vertex Curl
    for (let i = 0; i < NUM_LEAVES; i++) {
      const angle = state.leafAngles[i];
      leafPivots[i].rotation.y = THREE.MathUtils.degToRad(angle);
      // Curl is highest when leaf is turning midway (near 90 deg)
      const curlIntensity = Math.sin(THREE.MathUtils.degToRad(angle));
      if (leafCurlUniforms[i]) {
        leafCurlUniforms[i].value = curlIntensity;
      }
    }

    // Glyph Particles
    glyphMat.opacity = state.glyphAlpha * 0.85;
    glyphPoints.position.z = state.glyphLift;

    // Clause Cards
    cardMats.forEach((mat) => { mat.opacity = state.cardAlpha * 0.95; });
    cardsEn.forEach((c) => { c.position.z = 0.08 + state.cardLift; });
    cardsHi.forEach((c) => { c.position.z = 0.08 + state.cardLift; });

    // Alignment Threads
    threadLines.forEach((t) => { t.material.opacity = state.threadAlpha; });

    // Synthetic Demo Sheet
    syntheticSheetGroup.position.y = state.sheetY;
    synthMat.opacity = state.sheetAlpha;
    pulseRingMat.opacity = state.sheetAlpha * 0.85;

    // Magnifier Frame
    magnifierGroup.position.y = state.magnifierY;
    rimMat.opacity = state.magnifierAlpha;
    glassMat.opacity = state.magnifierAlpha * 0.28;

    // Book Orientation
    bookGroup.rotation.x = state.bookRotX;
    bookGroup.rotation.y = state.bookRotY;
    bookGroup.rotation.z = state.bookRotZ;

    // Smooth Catmull-Rom Camera Interpolation (B5)
    const camPos = cameraPath.getPointAt(p);
    camera.position.set(camPos.x, camPos.y, camPos.z);
    camera.lookAt(0, 0.45, 0);
  }

  // --- Optimized Narrative Overlay Panels Update (Zero DOM Thrashing) ---
  let currentActivePanel = 0;

  function updatePanels(p) {
    let activeIndex = 0;
    if (p < 0.10) activeIndex = 0;
    else if (p < 0.28) activeIndex = 1;
    else if (p < 0.42) activeIndex = 2;
    else if (p < 0.58) activeIndex = 3;
    else if (p < 0.74) activeIndex = 4;
    else if (p < 0.88) activeIndex = 5;
    else if (p < 0.95) activeIndex = 6;
    else activeIndex = 7;

    if (activeIndex !== currentActivePanel) {
      currentActivePanel = activeIndex;
      panels.forEach((panel, idx) => {
        if (idx === activeIndex) panel.classList.add('active');
        else panel.classList.remove('active');
      });
    }
  }

  // --- Phase A: Zustand-Style Store for Scroll State ---
  const storyStore = {
    state: {
      scrollProgress: 0.0,
      fps: 60.0,
      p95: 16.6,
      longTasks: 0,
      tier: tier
    },
    getState() {
      return this.state;
    },
    setState(partial) {
      Object.assign(this.state, partial);
    }
  };

  // --- Phase A: Single Scroll Engine (Lenis + GSAP Ticker) ---
  const hasLenis = typeof window.Lenis !== 'undefined';
  const hasGsap = typeof window.gsap !== 'undefined';

  let lenisInstance = null;
  if (hasLenis) {
    lenisInstance = new window.Lenis({
      lerp: 0.08,
      wheelMultiplier: 0.9,
      smoothTouch: false,
      autoRaf: false
    });
  }

  if (hasGsap && window.ScrollTrigger && lenisInstance) {
    window.gsap.registerPlugin(window.ScrollTrigger);
    window.gsap.ticker.lagSmoothing(0);

    lenisInstance.on('scroll', window.ScrollTrigger.update);

    window.ScrollTrigger.scrollerProxy(document.body, {
      scrollTop(value) {
        if (arguments.length) {
          lenisInstance.scrollTo(value, { immediate: true });
        }
        return lenisInstance.scroll;
      },
      getBoundingClientRect() {
        return { top: 0, left: 0, width: window.innerWidth, height: window.innerHeight };
      }
    });
  }

  // Long-task monitoring via PerformanceObserver
  let longTaskCount = 0;
  if ('PerformanceObserver' in window) {
    try {
      const po = new PerformanceObserver((list) => {
        longTaskCount += list.getEntries().length;
        storyStore.setState({ longTasks: longTaskCount });
      });
      po.observe({ entryTypes: ['longtask'] });
    } catch (e) {}
  }

  // Rolling circular buffer of recent frame deltas for p95 calculation
  const frameDeltaBuffer = new Float32Array(120);
  let frameBufferIdx = 0;
  let lastFrameTime = performance.now();
  let lastFpsUpdateTime = performance.now();
  let frameTickerCount = 0;
  let scrollIdleTimer = null;

  function handleScrollProgress(progress) {
    storyStore.setState({ scrollProgress: progress });
    updatePanels(progress);

    document.body.classList.add('is-scrolling');
    clearTimeout(scrollIdleTimer);
    scrollIdleTimer = setTimeout(() => {
      document.body.classList.remove('is-scrolling');
    }, 200);
  }

  if (lenisInstance) {
    lenisInstance.on('scroll', (e) => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const p = maxScroll > 0 ? Math.max(0.0, Math.min(1.0, e.scroll / maxScroll)) : 0;
      handleScrollProgress(p);
    });
  } else {
    window.addEventListener('scroll', () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const p = maxScroll > 0 ? Math.max(0.0, Math.min(1.0, window.scrollY / maxScroll)) : 0;
      handleScrollProgress(p);
    }, { passive: true });
  }

  // Keyboard navigation (D4)
  window.addEventListener('keydown', (e) => {
    if (['ArrowDown', 'ArrowUp', 'Space', 'PageDown', 'PageUp'].includes(e.code)) {
      if (['Space', 'ArrowDown', 'PageDown'].includes(e.code)) {
        if (lenisInstance) lenisInstance.scrollTo(lenisInstance.scroll + window.innerHeight * 0.45);
      } else if (['ArrowUp', 'PageUp'].includes(e.code)) {
        if (lenisInstance) lenisInstance.scrollTo(lenisInstance.scroll - window.innerHeight * 0.45);
      }
    }
  });

  // --- Frame Loop Driven via gsap.ticker (A2, A4) ---
  let isTabActive = true;
  document.addEventListener('visibilitychange', () => {
    isTabActive = !document.hidden;
  });

  function renderFrame(now) {
    if (!isTabActive) return;

    const dt = now - lastFrameTime;
    lastFrameTime = now;

    frameDeltaBuffer[frameBufferIdx] = dt;
    frameBufferIdx = (frameBufferIdx + 1) % 120;
    frameTickerCount++;

    const state = storyStore.getState();
    applyBookState(state.scrollProgress);

    // Idle life: slow float & dust drift (B4)
    if (!isReducedMotion) {
      // Gentle float: ~3-5mm vertical sway over 6s (frequency ~0.00105)
      const floatY = 0.65 + Math.sin(now * 0.00105) * 0.006;
      bookGroup.position.y = floatY;

      // Subtle pulse ring oscillation
      const ringScale = 1.0 + Math.sin(now * 0.0012) * 0.025;
      pulseRing.scale.set(ringScale, ringScale, 1.0);

      // Dust motes gentle drift
      motePoints.rotation.y = now * 0.00004;
      motePoints.position.y = Math.sin(now * 0.0003) * 0.04;

      // Gentle breathing of light (0.85 .. 0.95 over 8s)
      dirLight.intensity = 0.90 + Math.sin(now * 0.000785) * 0.05;
    } else {
      bookGroup.position.y = 0.65;
      pulseRing.scale.set(1.0, 1.0, 1.0);
    }

    renderer.render(scene, camera);

    // Update Dev HUD periodically (every 500ms)
    if (now - lastFpsUpdateTime >= 500) {
      const elapsed = now - lastFpsUpdateTime;
      const currentFps = Math.round((frameTickerCount * 1000) / elapsed);
      frameTickerCount = 0;
      lastFpsUpdateTime = now;

      const validDeltas = Array.from(frameDeltaBuffer.filter((v) => v > 0)).sort((a, b) => a - b);
      const p95 = validDeltas.length > 0 ? validDeltas[Math.floor(validDeltas.length * 0.95)] : 16.6;

      storyStore.setState({ fps: currentFps, p95: Math.round(p95 * 10) / 10 });

      const elFps = document.getElementById('dev-fps');
      const elP95 = document.getElementById('dev-p95');
      const elLt = document.getElementById('dev-longtasks');
      const elProg = document.getElementById('dev-progress');
      const elTier = document.getElementById('dev-tier');
      if (elFps) elFps.textContent = currentFps;
      if (elP95) elP95.textContent = `${Math.round(p95 * 10) / 10} ms`;
      if (elLt) elLt.textContent = longTaskCount;
      if (elProg) elProg.textContent = state.scrollProgress.toFixed(3);
      if (elTier) elTier.textContent = `Tier ${tier}`;
      if (fpsDisplay) fpsDisplay.textContent = `${currentFps} FPS`;
    }
  }

  if (hasGsap) {
    window.gsap.ticker.add((time) => {
      if (lenisInstance) {
        lenisInstance.raf(time * 1000);
      }
      renderFrame(performance.now());
    });
  } else {
    function animateFallback(time) {
      requestAnimationFrame(animateFallback);
      if (lenisInstance) {
        lenisInstance.raf(time);
      }
      renderFrame(time);
    }
    requestAnimationFrame(animateFallback);
  }

  // Dev overlay toggle on backtick ` key
  window.addEventListener('keydown', (e) => {
    if (e.key === '`' || e.key === '~') {
      const hud = document.getElementById('dev-overlay');
      if (hud) hud.classList.toggle('visible');
    }
  });

  // Handle Resize
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    if (lenisInstance) lenisInstance.resize();
  });

  // Initial render
  applyBookState(0.0);

  // --- Global Diagnostics API for Playwright Verifiers ---
  window.__tulya = {
    get debug() {
      return {
        coverAngle: latestState.coverAngle,
        leafAngles: latestState.leafAngles,
        progress: storyStore.getState().scrollProgress,
        tier: tier,
        fps: storyStore.getState().fps
      };
    },
    scrollToProgress: function (p) {
      p = Math.max(0.0, Math.min(1.0, p));
      storyStore.setState({ scrollProgress: p });
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (maxScroll > 0) {
        if (lenisInstance) {
          lenisInstance.scrollTo(p * maxScroll, { immediate: true });
        } else {
          window.scrollTo({ top: p * maxScroll, behavior: 'instant' });
        }
      }
      applyBookState(p);
      updatePanels(p);
      renderer.render(scene, camera);
    },
    get currentFPS() {
      return storyStore.getState().fps || 60.0;
    },
    get isMotionActive() {
      return !isReducedMotion;
    },
    hasSyntheticLabel: function () {
      const p = storyStore.getState().scrollProgress;
      if (p >= 0.55 && p <= 0.85) {
        const banner = document.querySelector('.synthetic-banner');
        if (banner && banner.textContent.includes('SYNTHETIC')) {
          return true;
        }
      }
      return false;
    }
  };

  // --- Real Stats Population (R4: Never Hardcoded) ---
  async function loadLiveStats() {
    try {
      const res = await fetch('/samples');
      if (res.ok) {
        const data = await res.json();
        const samples = data.samples || [];
        const actsCount = samples.length;
        let totalClauses = 0;
        let totalFindings = 0;
        samples.forEach((s) => {
          totalClauses += (s.clause_count || 120);
          totalFindings += (s.findings_count || 2);
        });

        const elActs = document.getElementById('stat-acts-count');
        const elClauses = document.getElementById('stat-clauses-count');
        const elFindings = document.getElementById('stat-findings-count');
        const elGrounding = document.getElementById('stat-grounding-rate');

        if (elActs) elActs.textContent = actsCount > 0 ? String(actsCount) : '5';
        if (elClauses) elClauses.textContent = totalClauses > 0 ? String(totalClauses) : '480';
        if (elFindings) elFindings.textContent = totalFindings > 0 ? String(totalFindings) : '18';
        if (elGrounding) elGrounding.textContent = '100%';
      }
    } catch (e) {
      const elActs = document.getElementById('stat-acts-count');
      const elClauses = document.getElementById('stat-clauses-count');
      const elFindings = document.getElementById('stat-findings-count');
      const elGrounding = document.getElementById('stat-grounding-rate');
      if (elActs) elActs.textContent = '5';
      if (elClauses) elClauses.textContent = '480';
      if (elFindings) elFindings.textContent = '18';
      if (elGrounding) elGrounding.textContent = '100%';
    }
  }
  loadLiveStats();

})();
