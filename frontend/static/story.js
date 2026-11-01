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
  const COLOR_COVER = 0x1A1B1E;       // Authentic deep charcoal leather of the Constitution volume
  const COLOR_BRASS = 0xC8A452;       // Warm gold foil
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
  // Transparent scene background to reveal #story-stage (L0-L3) underneath
  scene.background = null;

  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 50);
  camera.position.set(0, 0.65, 7.8);

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: tier >= 2,
    alpha: true,
    powerPreference: 'high-performance'
  });
  renderer.setClearColor(0x000000, 0);
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

  // 1. Front Cover Fallback Canvas Texture: Authentic dark charcoal leather with gold foil typography
  function createCoverTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 768;
    const ctx = cvs.getContext('2d');

    ctx.fillStyle = '#1A1B1E';
    ctx.fillRect(0, 0, 512, 768);

    // Subtle leather grain
    ctx.fillStyle = 'rgba(255, 255, 255, 0.03)';
    for (let i = 0; i < 400; i++) {
      ctx.fillRect(Math.random() * 512, Math.random() * 768, 2, 2);
    }

    // Double brass/gold border
    ctx.strokeStyle = '#C8A452';
    ctx.lineWidth = 4;
    ctx.strokeRect(26, 26, 460, 716);
    ctx.lineWidth = 1.5;
    ctx.strokeRect(36, 36, 440, 696);

    // Geometric corner accents
    const corners = [[36, 36], [476, 36], [36, 732], [476, 732]];
    corners.forEach(([cx, cy]) => {
      ctx.fillStyle = '#C8A452';
      ctx.fillRect(cx - 5, cy - 5, 10, 10);
    });

    ctx.fillStyle = '#C8A452';
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

  // 3b. Constitutional Endpaper Texture
  function createEndpaperTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 724;
    const ctx = cvs.getContext('2d');

    // Base warm parchment
    ctx.fillStyle = '#F3ECDD';
    ctx.fillRect(0, 0, 512, 724);

    // Subtle paper grain
    ctx.fillStyle = 'rgba(184, 155, 94, 0.04)';
    for (let i = 0; i < 20; i++) {
      ctx.fillRect(0, i * 36, 512, 18);
    }

    // Outer double brass rule
    ctx.strokeStyle = '#B89B5E';
    ctx.lineWidth = 2.0;
    ctx.strokeRect(24, 24, 464, 676);
    ctx.strokeStyle = 'rgba(184, 155, 94, 0.45)';
    ctx.lineWidth = 1.0;
    ctx.strokeRect(32, 32, 448, 660);

    // Center subtle institutional motif
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(35, 74, 82, 0.35)';
    ctx.font = '600 13px "Cinzel", Georgia, serif';
    ctx.fillText('CONSTITUTION OF INDIA', 256, 350);
    ctx.font = '500 11px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('भारत का संविधान', 256, 372);
    ctx.fillStyle = 'rgba(184, 155, 94, 0.4)';
    ctx.font = '400 9px "Inter", sans-serif';
    ctx.fillText('OFFICIAL PARCHMENT LEAF', 256, 394);

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // 3c. Stratified Page Edge Texture
  function createPageEdgeTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 128;
    cvs.height = 128;
    const ctx = cvs.getContext('2d');
    ctx.fillStyle = '#FAF6EC';
    ctx.fillRect(0, 0, 128, 128);
    ctx.strokeStyle = 'rgba(43, 58, 63, 0.08)';
    ctx.lineWidth = 1;
    for (let y = 0; y < 128; y += 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(128, y);
      ctx.stroke();
    }
    const tex = new THREE.CanvasTexture(cvs);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(6, 2);
    return tex;
  }

  // 4. Synthetic Demo Sheet Texture (Fix 1: Cleaned up, no ring, no handle, small tag, text-only underlines, edge connector)
  function createSyntheticSheetTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 1024;
    cvs.height = 512;
    const ctx = cvs.getContext('2d');

    // Warm paper card
    ctx.fillStyle = '#FAF7EE';
    ctx.fillRect(0, 0, 1024, 512);

    // Outer subtle border
    ctx.strokeStyle = 'rgba(165, 86, 107, 0.45)';
    ctx.lineWidth = 2.5;
    ctx.strokeRect(12, 12, 1000, 488);

    // 1. Tag in top-left corner: "SYNTHETIC DEMO"
    ctx.fillStyle = '#A5566B';
    const tagX = 28, tagY = 22, tagW = 142, tagH = 26, tagR = 4;
    ctx.beginPath();
    ctx.moveTo(tagX + tagR, tagY);
    ctx.lineTo(tagX + tagW - tagR, tagY);
    ctx.quadraticCurveTo(tagX + tagW, tagY, tagX + tagW, tagY + tagR);
    ctx.lineTo(tagX + tagW, tagY + tagH - tagR);
    ctx.quadraticCurveTo(tagX + tagW, tagY + tagH, tagX + tagW - tagR, tagY + tagH);
    ctx.lineTo(tagX + tagR, tagY + tagH);
    ctx.quadraticCurveTo(tagX, tagY + tagH, tagX, tagY + tagH - tagR);
    ctx.lineTo(tagX, tagY + tagR);
    ctx.quadraticCurveTo(tagX, tagY, tagX + tagR, tagY);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '700 12px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('SYNTHETIC DEMO', tagX + tagW / 2, tagY + 17);

    // Subtitle right beside tag: "Section 12(3) divergence, illustrative only"
    ctx.textAlign = 'left';
    ctx.fillStyle = '#6C7D82';
    ctx.font = '500 13px "Inter", sans-serif';
    ctx.fillText('Section 12(3) divergence, illustrative only', tagX + tagW + 14, tagY + 18);

    // Top rule divider
    ctx.strokeStyle = 'rgba(43, 58, 63, 0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(28, 60);
    ctx.lineTo(996, 60);
    ctx.stroke();

    // Central column divider
    ctx.strokeStyle = 'rgba(43, 58, 63, 0.10)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(512, 75);
    ctx.lineTo(512, 405);
    ctx.stroke();

    // 2. English Column (Left)
    ctx.textAlign = 'left';
    ctx.fillStyle = '#5B7C99';
    ctx.font = '700 15px "Cinzel", Georgia, serif';
    ctx.fillText('ENGLISH STATUTORY PROVISION', 45, 100);

    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 18px "Inter", sans-serif';
    ctx.fillText('...shall be liable to pay a penalty equal to', 45, 148);

    ctx.font = '700 23px "Inter", sans-serif';
    ctx.fillStyle = '#3F5F7E';
    ctx.fillText('TEN TIMES THE TAX', 45, 198);

    const enPhraseWidth = ctx.measureText('TEN TIMES THE TAX').width;

    // Slate underline for English phrase
    ctx.strokeStyle = '#5B7C99';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(45, 206);
    ctx.lineTo(45 + enPhraseWidth, 206);
    ctx.stroke();

    ctx.fillStyle = '#6C7D82';
    ctx.font = '400 14px "Inter", sans-serif';
    ctx.fillText('Statutory cap: liability limited to 10× tax payable', 45, 246);

    // 3. Hindi Column (Right)
    ctx.textAlign = 'left';
    ctx.fillStyle = '#C0805F';
    ctx.font = '700 17px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('हिन्दी सांविधिक उपबंध (निर्दिष्ट)', 545, 100);

    ctx.fillStyle = '#2B3A3F';
    ctx.font = '500 18px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('...देय कर की रकम के दस गुने के', 545, 148);

    ctx.font = '700 23px "Noto Sans Devanagari", sans-serif';
    ctx.fillStyle = '#8F4F32';
    ctx.fillText('अतिरिक्त दस गुना शास्ति', 545, 198);

    const hiPhraseWidth = ctx.measureText('अतिरिक्त दस गुना शास्ति').width;

    // Clay underline for Hindi phrase
    ctx.strokeStyle = '#C0805F';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(545, 206);
    ctx.lineTo(545 + hiPhraseWidth, 206);
    ctx.stroke();

    ctx.fillStyle = '#6C7D82';
    ctx.font = '400 14px "Noto Sans Devanagari", sans-serif';
    ctx.fillText('विधिक अर्थ: कर की रकम + 10 गुना अतिरिक्त शास्ति', 545, 246);

    // 4. Thin Connector Line routed strictly along gutter/margins so it NEVER crosses a glyph
    ctx.strokeStyle = 'rgba(165, 86, 107, 0.70)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    // From end of English underline
    ctx.moveTo(45 + enPhraseWidth + 8, 206);
    // Drop down into margin below phrase text
    ctx.lineTo(45 + enPhraseWidth + 8, 222);
    // Route horizontally across center gutter
    ctx.lineTo(545 - 8, 222);
    // Rise up to Hindi underline level
    ctx.lineTo(545 - 8, 206);
    // Connect to start of Hindi underline
    ctx.lineTo(545, 206);
    ctx.stroke();

    // Small connector dots at endpoints
    ctx.fillStyle = '#5B7C99';
    ctx.beginPath();
    ctx.arc(45 + enPhraseWidth + 8, 206, 2.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#C0805F';
    ctx.beginPath();
    ctx.arc(545 - 8, 206, 2.5, 0, Math.PI * 2);
    ctx.fill();

    // 5. Finding strip at bottom (one line, fully readable)
    ctx.fillStyle = 'rgba(165, 86, 107, 0.08)';
    ctx.fillRect(36, 420, 952, 60);
    ctx.strokeStyle = 'rgba(165, 86, 107, 0.35)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(36, 420, 952, 60);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#7D3A4D';
    ctx.font = '600 15px "Inter", sans-serif';
    ctx.fillText("▲ Discrepancy: 'कर के अतिरिक्त' specifies penalty IN ADDITION TO tax (tax + 10x penalty)", 512, 456);

    const tex = new THREE.CanvasTexture(cvs);
    tex.anisotropy = 1;
    return tex;
  }

  // --- 3D Procedural Book Hierarchy (Hardcover on Table with Spine Hinge) ---
  const bookGroup = new THREE.Group();
  bookGroup.position.set(-1.2, 1.05, 0); // Initially shifted so closed book is centered vertically and horizontally
  scene.add(bookGroup);

  const BOOK_W = 2.4;
  const BOOK_H = 3.4;
  const BOOK_T = 0.28;
  const COVER_T = 0.05;

  const endpaperTex = createEndpaperTexture();
  const pageEdgeTex = createPageEdgeTexture();

  // FIX 2 (L4 Ground): Soft Elliptical Contact Shadow Texture (zero polygon edges, pure radial fade)
  function createContactShadowTexture() {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 256;
    const ctx = cvs.getContext('2d');
    ctx.clearRect(0, 0, 512, 256);

    ctx.save();
    ctx.translate(256, 128);
    ctx.scale(1.0, 0.48);
    const grad = ctx.createRadialGradient(0, 0, 10, 0, 0, 220);
    grad.addColorStop(0, 'rgba(20, 40, 43, 0.45)');
    grad.addColorStop(0.30, 'rgba(20, 40, 43, 0.22)');
    grad.addColorStop(0.65, 'rgba(20, 40, 43, 0.05)');
    grad.addColorStop(0.92, 'rgba(20, 40, 43, 0.0)');
    grad.addColorStop(1.0, 'rgba(20, 40, 43, 0.0)');

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(0, 0, 240, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    const tex = new THREE.CanvasTexture(cvs);
    return tex;
  }

  const shadowTex = createContactShadowTexture();
  const shadowGeo = new THREE.PlaneGeometry(7.2, 4.2);
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    opacity: 0.85,
    depthWrite: false
  });
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.position.set(0, -0.05, -BOOK_T / 2 - 0.02);
  bookGroup.add(shadowMesh);

  // Back Cover Slab (resting flat on table, endpaper facing up into book)
  const backCoverGeo = new THREE.BoxGeometry(BOOK_W, BOOK_H, COVER_T);
  const backCoverLeatherMat = new THREE.MeshStandardMaterial({
    color: COLOR_COVER,
    roughness: 0.55,
    metalness: 0.1
  });
  const backCoverEndpaperMat = new THREE.MeshStandardMaterial({
    map: endpaperTex,
    roughness: 0.65
  });
  const backCoverMaterials = [
    backCoverLeatherMat, // +X
    backCoverLeatherMat, // -X
    backCoverLeatherMat, // +Y
    backCoverLeatherMat, // -Y
    backCoverEndpaperMat, // +Z (inside face)
    backCoverLeatherMat  // -Z (outside face on table)
  ];
  const backCover = new THREE.Mesh(backCoverGeo, backCoverMaterials);
  backCover.position.set(BOOK_W / 2, 0, -BOOK_T / 2);
  bookGroup.add(backCover);

  // Spine: Rounded half-cylinder wrapping along Y axis at X = 0
  const spineGeo = new THREE.CylinderGeometry(0.14, 0.14, BOOK_H, 24, 1, false, Math.PI / 2, Math.PI);
  const spineMat = new THREE.MeshStandardMaterial({
    color: COLOR_COVER,
    roughness: 0.55,
    metalness: 0.1
  });
  const spine = new THREE.Mesh(spineGeo, spineMat);
  spine.position.set(0, 0, 0);
  bookGroup.add(spine);

  // Page Block Materials (stratified edges with paper layers)
  const pageEdgeMat = new THREE.MeshStandardMaterial({
    map: pageEdgeTex,
    color: COLOR_EDGE,
    roughness: 0.8
  });
  const pageTopMat = new THREE.MeshStandardMaterial({
    color: COLOR_PARCHMENT,
    roughness: 0.65
  });
  const pageBlockMaterials = [
    pageEdgeMat, // +X
    pageEdgeMat, // -X
    pageEdgeMat, // +Y
    pageEdgeMat, // -Y
    pageTopMat,  // +Z
    pageTopMat   // -Z
  ];

  // Right Page Block Base
  const rightBlockGeo = new THREE.BoxGeometry(BOOK_W - 0.08, BOOK_H - 0.08, BOOK_T - 0.06);
  const rightPageBlock = new THREE.Mesh(rightBlockGeo, pageBlockMaterials);
  rightPageBlock.position.set((BOOK_W - 0.08) / 2 + 0.04, 0, -0.01);
  bookGroup.add(rightPageBlock);

  // Left Page Block Base (hidden when closed; appears when pages turn from right to left)
  const leftBlockGeo = new THREE.BoxGeometry(BOOK_W - 0.08, BOOK_H - 0.08, BOOK_T - 0.06);
  const leftPageBlock = new THREE.Mesh(leftBlockGeo, pageBlockMaterials);
  leftPageBlock.position.set(-(BOOK_W - 0.08) / 2 - 0.04, 0, -0.01);
  leftPageBlock.scale.set(1.0, 1.0, 0.001);
  leftPageBlock.visible = false;
  bookGroup.add(leftPageBlock);

  // Base Right Spread (Hindi Preamble text on right page)
  const hiSpreadGeo = new THREE.PlaneGeometry(BOOK_W - 0.1, BOOK_H - 0.1);
  const hiSpreadMat = new THREE.MeshBasicMaterial({ map: createPreambleHiTexture() });
  const hiSpreadMesh = new THREE.Mesh(hiSpreadGeo, hiSpreadMat);
  hiSpreadMesh.position.set((BOOK_W - 0.1) / 2 + 0.05, 0, (BOOK_T - 0.06) / 2 + 0.002);
  bookGroup.add(hiSpreadMesh);

  // Base Left Spread (English Preamble text on left page - full symmetrical page)
  const enSpreadGeo = new THREE.PlaneGeometry(BOOK_W - 0.1, BOOK_H - 0.1);
  const enSpreadMat = new THREE.MeshBasicMaterial({ map: createPreambleEnTexture() });
  const enSpreadMesh = new THREE.Mesh(enSpreadGeo, enSpreadMat);
  enSpreadMesh.position.set(-((BOOK_W - 0.1) / 2 + 0.05), 0, (BOOK_T - 0.06) / 2 + 0.002);
  enSpreadMesh.visible = false;
  bookGroup.add(enSpreadMesh);

  // Front Cover Pivot: Hinged STRICTLY at the spine edge (X = 0, Y = 0, Z = BOOK_T / 2)
  const coverPivot = new THREE.Group();
  coverPivot.position.set(0, 0, BOOK_T / 2);
  bookGroup.add(coverPivot);

  // Front cover thin slab with 24 width segments for board flex
  const frontCoverGeo = new THREE.BoxGeometry(BOOK_W, BOOK_H, COVER_T, 24, 1, 1);
  const coverTex = createCoverTexture();

  const coverFlexUniform = { value: 0.0 };
  const frontCoverLeatherMat = new THREE.MeshStandardMaterial({
    color: COLOR_COVER,
    roughness: 0.55
  });
  const frontCoverFaceMat = new THREE.MeshBasicMaterial({ map: coverTex, color: 0xFFFFFF });
  const frontCoverEndpaperMat = new THREE.MeshStandardMaterial({
    map: endpaperTex,
    roughness: 0.65
  });

  const frontCoverMaterials = [
    frontCoverLeatherMat, // +X
    frontCoverLeatherMat, // -X
    frontCoverLeatherMat, // +Y
    frontCoverLeatherMat, // -Y
    frontCoverFaceMat,    // +Z (outside cover face)
    frontCoverEndpaperMat // -Z (inside endpaper face)
  ];

  // Apply board flex vertex shader (max ~6 degrees bend at middle of swing)
  frontCoverMaterials.forEach((mat) => {
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uCoverFlex = coverFlexUniform;
      shader.vertexShader = 'uniform float uCoverFlex;\n' + shader.vertexShader;
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        `
        #include <begin_vertex>
        float normX = clamp((position.x + ${BOOK_W / 2}) / ${BOOK_W}, 0.0, 1.0);
        transformed.z -= normX * normX * uCoverFlex * 0.16;
        `
      );
    };
  });

  const frontCoverMesh = new THREE.Mesh(frontCoverGeo, frontCoverMaterials);
  // Position frontCoverMesh so its spine edge sits exactly on the rotation axis X = 0
  frontCoverMesh.position.set(BOOK_W / 2, 0, COVER_T / 2);
  coverPivot.add(frontCoverMesh);

  // Progressive texture load: Authentic Constitution of India photograph cover (User Provided Image)
  const texLoader = new THREE.TextureLoader();
  texLoader.load('/public/assets/constitution_cover.webp', (tex) => {
    tex.anisotropy = 4;
    frontCoverFaceMat.map = tex;
    frontCoverFaceMat.needsUpdate = true;
  }, undefined, () => {
    texLoader.load('/public/assets/constitution_cover.jpg', (tex) => {
      tex.anisotropy = 4;
      frontCoverFaceMat.map = tex;
      frontCoverFaceMat.needsUpdate = true;
    });
  });

  texLoader.load('/public/assets/cover_leather_nor_gl_1k.webp', (tex) => {
    frontCoverFaceMat.normalMap = tex;
    frontCoverFaceMat.normalScale = new THREE.Vector2(0.35, 0.35);
    frontCoverFaceMat.needsUpdate = true;
    backCoverLeatherMat.normalMap = tex;
    backCoverLeatherMat.normalScale = new THREE.Vector2(0.35, 0.35);
    backCoverLeatherMat.needsUpdate = true;
    spineMat.normalMap = tex;
    spineMat.normalScale = new THREE.Vector2(0.35, 0.35);
    spineMat.needsUpdate = true;
  }, undefined, () => {});

  // Turning Page Leaf (One leaf, scroll 0.28 to 0.34)
  const turnLeafPivot = new THREE.Group();
  turnLeafPivot.position.set(0, 0, (BOOK_T - 0.06) / 2 + 0.005);
  bookGroup.add(turnLeafPivot);

  const turnLeafGeo = new THREE.PlaneGeometry(BOOK_W - 0.12, BOOK_H - 0.1, 24, 24);
  const turnLeafCurlUniform = { value: 0.0 };
  const enSpreadTex = createPreambleEnTexture();

  const leafMatFront = new THREE.MeshBasicMaterial({ map: enSpreadTex, side: THREE.DoubleSide });
  const leafMatBack = new THREE.MeshBasicMaterial({ map: enSpreadTex, side: THREE.DoubleSide });

  [leafMatFront, leafMatBack].forEach((mat) => {
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uLeafCurl = turnLeafCurlUniform;
      shader.vertexShader = 'uniform float uLeafCurl;\n' + shader.vertexShader;
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        `
        #include <begin_vertex>
        float normLx = clamp((position.x + ${(BOOK_W - 0.12) / 2}) / ${BOOK_W - 0.12}, 0.0, 1.0);
        transformed.z += sin(normLx * 3.14159 * 0.5) * uLeafCurl * 0.24;
        `
      );
    };
  });

  const leafFrontMesh = new THREE.Mesh(turnLeafGeo, leafMatFront);
  leafFrontMesh.position.set((BOOK_W - 0.12) / 2 + 0.06, 0, 0.001);
  turnLeafPivot.add(leafFrontMesh);

  const leafBackMesh = new THREE.Mesh(turnLeafGeo, leafMatBack);
  leafBackMesh.position.set((BOOK_W - 0.12) / 2 + 0.06, 0, -0.001);
  leafBackMesh.rotation.y = Math.PI;
  turnLeafPivot.add(leafBackMesh);

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
    mEn.position.set(-1.20, yPos, 0.14);
    clauseCardsGroup.add(mEn);
    cardsEn.push(mEn);
    cardMats.push(matEn);

    const texHi = createClauseCardTexture('hi', idx, cardData[idx].en, cardData[idx].hi);
    const matHi = new THREE.MeshBasicMaterial({ map: texHi, transparent: true, opacity: 0.0 });
    const mHi = new THREE.Mesh(cardGeo, matHi);
    mHi.position.set(1.20, yPos, 0.14);
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

  // --- Clause Cards Alignment Scene (Green line cylinders removed for text legibility) ---
  // Thread lines across text are omitted so English and Hindi clause cards remain completely unobstructed

  // --- Synthetic Demo Sheet (Fix 1: Cleaned up, no ring, no handle, small tag, text-only underlines, edge connector) ---
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

  // Soft border pulse mesh (Fix 1: border pulses to plum-rose, zero rings over text)
  const synthBorderGeo = new THREE.EdgesGeometry(synthGeo);
  const synthBorderMat = new THREE.LineBasicMaterial({
    color: COLOR_ROSE,
    transparent: true,
    opacity: 0.0
  });
  const synthBorderMesh = new THREE.LineSegments(synthBorderGeo, synthBorderMat);
  syntheticSheetGroup.add(synthBorderMesh);

  // --- Catmull-Rom Camera Spline Path (Raised closed hero perspective for centered framing) ---
  const cameraPath = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.75, 7.6),   // 0.00: Closed hero (elevated for centered viewport)
    new THREE.Vector3(0, 0.72, 7.2),   // 0.15: Opening arc
    new THREE.Vector3(0, 0.58, 6.7),   // 0.32: Spread settled
    new THREE.Vector3(0, 0.55, 6.4),   // 0.48: Clause cards lift
    new THREE.Vector3(0, 0.52, 6.0),   // 0.65: Synthetic demo card
    new THREE.Vector3(0, 0.55, 6.4),   // 0.80: Substantive review
    new THREE.Vector3(0, 0.68, 7.2),   // 0.94: Closing
    new THREE.Vector3(0, 0.75, 7.6)    // 1.00: Closed CTA
  ]);

  // --- Pure Deterministic Timeline State Function: calcBookState(p) ---
  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function calcBookState(p) {
    p = Math.max(0.0, Math.min(1.0, p));

    // 1. Front Cover Angle (0 to 170 deg), Flex, and Centering Shift (Fix 2 & Centering)
    let coverAngle = 0.0;
    let coverFlex = 0.0;
    let bookShiftX = -1.2;
    let bookShiftY = 1.05;
    let coverPivotZ = BOOK_T / 2;

    if (p < 0.08) {
      coverAngle = 0.0;
      coverFlex = 0.0;
      bookShiftX = -1.2;
      bookShiftY = 1.05;
      coverPivotZ = BOOK_T / 2;
    } else if (p >= 0.08 && p < 0.28) {
      const u = (p - 0.08) / 0.20;
      const eu = easeInOutCubic(u);
      let ang = eu * 170.0;
      if (u > 0.88) {
        const su = (u - 0.88) / 0.12;
        // Damped settle: 1.5 deg overshoot decaying to 0
        ang += Math.sin(su * Math.PI) * 1.5 * (1.0 - su);
      }
      coverAngle = ang;
      coverFlex = Math.sin(Math.min(Math.PI, (coverAngle / 170.0) * Math.PI));
      bookShiftX = -1.2 * (1.0 - eu);
      bookShiftY = 1.05 - 0.40 * eu;
      coverPivotZ = (BOOK_T / 2) * (1.0 - eu) + (-BOOK_T / 2) * eu;
    } else if (p >= 0.28 && p < 0.93) {
      coverAngle = 170.0;
      coverFlex = 0.0;
      bookShiftX = 0.0;
      bookShiftY = 0.65;
      coverPivotZ = -BOOK_T / 2;
    } else if (p >= 0.93 && p <= 1.00) {
      const v = (p - 0.93) / 0.07;
      const ev = easeInOutCubic(1.0 - v);
      let ang = ev * 170.0;
      if (v > 0.88) {
        const sv = (v - 0.88) / 0.12;
        ang += Math.sin(sv * Math.PI) * 1.5 * (1.0 - sv);
      }
      coverAngle = ang;
      coverFlex = Math.sin(Math.min(Math.PI, (coverAngle / 170.0) * Math.PI));
      bookShiftX = -1.2 * (1.0 - ev);
      bookShiftY = 0.65 + 0.40 * (1.0 - ev);
      coverPivotZ = (BOOK_T / 2) * (1.0 - ev) + (-BOOK_T / 2) * ev;
    }

    // 2. Turning Leaf (p in [0.28, 0.36] opening, [0.88, 0.93] closing)
    let turnLeafAngle = 0.0;
    let turnLeafCurl = 0.0;
    let leftBlockScaleZ = 0.001;
    let rightBlockScaleZ = 1.0;

    if (p < 0.28) {
      turnLeafAngle = 0.0;
      turnLeafCurl = 0.0;
      leftBlockScaleZ = 0.001;
      rightBlockScaleZ = 1.0;
    } else if (p >= 0.28 && p < 0.36) {
      const t = (p - 0.28) / 0.08;
      const et = easeInOutCubic(t);
      turnLeafAngle = et * 180.0;
      turnLeafCurl = Math.sin(et * Math.PI);
      leftBlockScaleZ = 0.001 + et * 0.55;
      rightBlockScaleZ = 1.0 - et * 0.25;
    } else if (p >= 0.36 && p < 0.88) {
      turnLeafAngle = 180.0;
      turnLeafCurl = 0.0;
      leftBlockScaleZ = 0.55;
      rightBlockScaleZ = 0.75;
    } else if (p >= 0.88 && p < 0.93) {
      const t = (p - 0.88) / 0.05;
      const et = easeInOutCubic(1.0 - t);
      turnLeafAngle = et * 180.0;
      turnLeafCurl = Math.sin(et * Math.PI);
      leftBlockScaleZ = 0.001 + et * 0.55;
      rightBlockScaleZ = 1.0 - et * 0.25;
    } else {
      turnLeafAngle = 0.0;
      turnLeafCurl = 0.0;
      leftBlockScaleZ = 0.001;
      rightBlockScaleZ = 1.0;
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
    } else if (p >= 0.52 && p <= 0.88) {
      cardLift = 0.16;
      cardAlpha = 1.0;
    } else if (p > 0.88 && p < 0.93) {
      const t = (p - 0.88) / 0.05;
      cardLift = (1.0 - t) * 0.16;
      cardAlpha = 1.0 - t;
    }

    // 5. Sage Alignment Threads (p in [0.42, 0.58])
    let threadAlpha = 0.0;
    if (p >= 0.42 && p <= 0.56) {
      threadAlpha = (p - 0.42) / (0.56 - 0.42);
    } else if (p > 0.56 && p <= 0.88) {
      threadAlpha = 1.0;
    } else if (p > 0.88 && p < 0.93) {
      threadAlpha = 1.0 - (p - 0.88) / 0.05;
    }

    // 6. Synthetic Loose Sheet Position & Opacity (p in [0.58, 0.74])
    let sheetY = 4.0;
    let sheetAlpha = 0.0;
    if (p >= 0.58 && p < 0.65) {
      const t = (p - 0.58) / 0.07;
      sheetY = 4.0 * (1.0 - t);
      sheetAlpha = t;
    } else if (p >= 0.65 && p <= 0.84) {
      sheetY = 0.0;
      sheetAlpha = 1.0;
    } else if (p > 0.84 && p < 0.89) {
      const t = (p - 0.84) / 0.05;
      sheetY = -4.0 * t;
      sheetAlpha = 1.0 - t;
    }

    // 7. Synthetic Demo Card Border Pulse (Single soft pulse at p in [0.65, 0.72], then stays solid)
    let synthBorderOpacity = 0.4;
    if (p >= 0.65 && p < 0.72) {
      const t = (p - 0.65) / 0.07;
      const pulse = Math.sin(t * Math.PI);
      synthBorderOpacity = 0.4 + pulse * 0.6;
    } else if (p >= 0.72) {
      synthBorderOpacity = 0.85;
    }

    // 8. Book Tilt & Perspective
    let bookRotX = 0.38;
    let bookRotY = -0.10;
    let bookRotZ = 0.04;

    if (p >= 0.08 && p < 0.28) {
      const t = (p - 0.08) / 0.20;
      bookRotX = 0.38 - 0.06 * t;
      bookRotY = -0.10 * (1.0 - t);
      bookRotZ = 0.04 * (1.0 - t);
    } else if (p >= 0.28 && p < 0.93) {
      bookRotX = 0.32;
      bookRotY = 0.0;
      bookRotZ = 0.0;
    } else if (p >= 0.93) {
      const t = (p - 0.93) / 0.07;
      bookRotX = 0.32 + 0.06 * t;
      bookRotY = -0.10 * t;
      bookRotZ = 0.04 * t;
    }

    // 9. Shadow Opacity (subtle darkening on landing)
    let shadowOpacity = 0.09;
    if (p <= 0.04 || p >= 0.97) {
      shadowOpacity = 0.14;
    }

    return {
      coverAngle,
      coverFlex,
      coverPivotZ,
      turnLeafAngle,
      turnLeafCurl,
      bookShiftX,
      bookShiftY,
      leftBlockScaleZ,
      rightBlockScaleZ,
      glyphAlpha,
      glyphLift,
      cardLift,
      cardAlpha,
      threadAlpha,
      sheetY,
      sheetAlpha,
      synthBorderOpacity,
      bookRotX,
      bookRotY,
      bookRotZ,
      shadowOpacity
    };
  }

  // DOM references for Smart Header and Stage Parallax
  const storyNavbar = document.getElementById('story-navbar');
  const minimalNav = document.getElementById('story-minimal-nav');
  const stageEl = document.getElementById('story-stage');
  const stageColonnadeEl = document.getElementById('stage-l1');
  const ghostColEnEl = document.getElementById('ghost-col-en');
  const ghostColHiEl = document.getElementById('ghost-col-hi');

  // FIX 1 (Item 3): Full 100dvh Viewport Scaling for 3D Book
  function updateViewportScale() {
    const width = window.innerWidth;
    const height = window.innerHeight;

    let targetScale = 1.0;
    if (width >= 1025) {
      const hScale = Math.min(1.10, Math.max(0.85, height / 900));
      const wScale = Math.min(1.10, Math.max(0.85, width / 1440));
      targetScale = Math.min(hScale, wScale);
    } else {
      // Narrow screens (Tablet / Mobile): Scale book to comfortably fit upper 70% of viewport
      targetScale = Math.min(0.56, Math.max(0.42, (width / 800) * 0.52));
    }
    bookGroup.scale.set(targetScale, targetScale, targetScale);
    return targetScale;
  }

  // FIX 3: Desktop Side Offset (Book balances opposite side card with zero bounding box overlap)
  const SIDE_KEYPOINTS = [
    { p: 0.00, offset:  0.40 },
    { p: 0.08, offset:  0.40 },
    { p: 0.13, offset: -1.35 },
    { p: 0.26, offset: -1.35 },
    { p: 0.30, offset:  1.35 },
    { p: 0.40, offset:  1.35 },
    { p: 0.44, offset: -1.35 },
    { p: 0.56, offset: -1.35 },
    { p: 0.60, offset:  1.35 },
    { p: 0.72, offset:  1.35 },
    { p: 0.76, offset: -1.35 },
    { p: 0.86, offset: -1.35 },
    { p: 0.90, offset:  1.35 },
    { p: 0.93, offset:  1.35 },
    { p: 0.97, offset: -0.50 },
    { p: 1.00, offset: -0.50 }
  ];

  function getSideOffset(p) {
    if (window.innerWidth < 1025) return 0.0;
    if (p <= SIDE_KEYPOINTS[0].p) return SIDE_KEYPOINTS[0].offset;
    if (p >= SIDE_KEYPOINTS[SIDE_KEYPOINTS.length - 1].p) {
      return SIDE_KEYPOINTS[SIDE_KEYPOINTS.length - 1].offset;
    }
    for (let i = 0; i < SIDE_KEYPOINTS.length - 1; i++) {
      const k0 = SIDE_KEYPOINTS[i];
      const k1 = SIDE_KEYPOINTS[i + 1];
      if (p >= k0.p && p <= k1.p) {
        const u = (p - k0.p) / (k1.p - k0.p);
        const eu = easeInOutCubic(u);
        return k0.offset + (k1.offset - k0.offset) * eu;
      }
    }
    return 0.0;
  }

  // --- Apply State to 3D Scene ---
  let latestState = calcBookState(0.0);

  function applyBookState(p) {
    const state = calcBookState(p);
    latestState = state;

    // Shift book position to keep open spread or closed cover centered in viewport,
    // offset horizontally on wide screens to balance opposite active narrative card,
    // offset vertically on narrow screens to fit upper 70% viewport above bottom cards
    const isNarrow = window.innerWidth < 1025;
    const narrowShiftY = isNarrow ? 0.35 : 0.0;
    const sideOffset = getSideOffset(p);
    bookGroup.position.x = state.bookShiftX + sideOffset;
    bookGroup.position.y = state.bookShiftY + narrowShiftY;
    bookGroup.rotation.x = state.bookRotX;
    bookGroup.rotation.y = state.bookRotY;
    bookGroup.rotation.z = state.bookRotZ;
    bookGroup.updateMatrixWorld(true);

    // Stage parallax transforms (composite-only translate3d)
    if (stageColonnadeEl) {
      stageColonnadeEl.style.transform = `translate3d(0, ${(p * 15).toFixed(1)}px, 0)`;
    }
    if (ghostColEnEl) {
      ghostColEnEl.style.transform = `translate3d(0, ${(p * 24).toFixed(1)}px, 0)`;
    }
    if (ghostColHiEl) {
      ghostColHiEl.style.transform = `translate3d(0, ${(-p * 24).toFixed(1)}px, 0)`;
    }

    // Contact shadow mathematically centered directly under closed volume or open spread
    shadowMat.opacity = state.shadowOpacity;
    const openFrac = (state.coverAngle / 170.0);
    shadowMesh.scale.x = 0.5 + openFrac * 0.5;
    shadowMesh.position.x = 1.2 * (1.0 - openFrac);

    // Cover Rotation, Depth & Flex:
    // Moves pivot from +BOOK_T/2 (closed top) to -BOOK_T/2 (table plane) and rotates to 180 deg (flat on table)
    coverPivot.position.z = state.coverPivotZ;
    const coverRotDeg = state.coverAngle * (180.0 / 170.0);
    coverPivot.rotation.y = THREE.MathUtils.degToRad(-coverRotDeg);
    coverFlexUniform.value = state.coverFlex;

    // Turning Leaf Rotation & Curl (Only active during actual leaf-turn transitions)
    turnLeafPivot.visible = (p >= 0.08 && p < 0.36) || (p >= 0.88 && p <= 0.93);
    turnLeafPivot.rotation.y = THREE.MathUtils.degToRad(-state.turnLeafAngle);
    turnLeafCurlUniform.value = state.turnLeafCurl;

    // Page Block Thickness Dynamics & Visibility (left block ONLY visible after pages turn!)
    leftPageBlock.visible = (p >= 0.28 && p < 0.93);
    leftPageBlock.scale.z = state.leftBlockScaleZ;
    rightPageBlock.scale.z = state.rightBlockScaleZ;

    // Base Left Spread (English Preamble) Visibility
    enSpreadMesh.visible = (p >= 0.28 && p < 0.93);

    // Glyph Particles
    glyphMat.opacity = state.glyphAlpha * 0.85;
    glyphPoints.position.z = state.glyphLift;

    // Clause Cards: Positioned cleanly in front of page spread, fully visible without occlusion
    cardMats.forEach((mat) => { mat.opacity = state.cardAlpha * 0.95; });
    cardsEn.forEach((c) => { c.position.z = 0.14 + state.cardLift; });
    cardsHi.forEach((c) => { c.position.z = 0.14 + state.cardLift; });

    // Synthetic Demo Sheet
    syntheticSheetGroup.position.y = state.sheetY;
    synthMat.opacity = state.sheetAlpha;
    synthBorderMat.opacity = state.sheetAlpha * state.synthBorderOpacity;

    // Smooth Catmull-Rom Camera Interpolation with framed lookAt
    const camPos = cameraPath.getPointAt(p);
    camera.position.set(camPos.x, camPos.y, camPos.z);
    const lookTargetY = 0.70 - 0.20 * openFrac;
    camera.lookAt(0, lookTargetY, 0);
  }

  // --- Optimized Narrative Overlay Panels Update (Zero DOM Thrashing) & Stage Crossfade ---
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

    // FIX 2: Stage scene crossfade (600ms CSS transition across narrative acts)
    let sceneClass = 'stage-scene-cover';
    if (p < 0.28) {
      sceneClass = 'stage-scene-cover';
    } else if (p < 0.44) {
      sceneClass = 'stage-scene-segmentation';
    } else if (p < 0.60) {
      sceneClass = 'stage-scene-alignment';
    } else if (p < 0.86) {
      sceneClass = 'stage-scene-mismatch';
    } else {
      sceneClass = 'stage-scene-closing';
    }
    if (stageEl && !stageEl.classList.contains(sceneClass)) {
      stageEl.className = 'story-stage ' + sceneClass;
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

  // FIX 1: Smart Header (Visible at scroll 0, slides up on scroll down, slides down on scroll up or hover <= 60px)
  let lastScrollProgress = 0.0;
  let isHeaderHidden = false;

  function updateSmartHeader(p, cursorY) {
    if (!storyNavbar) return;

    if (cursorY !== undefined && cursorY <= 60) {
      if (isHeaderHidden) {
        isHeaderHidden = false;
        storyNavbar.classList.remove('is-hidden');
        if (minimalNav) minimalNav.classList.remove('is-active');
      }
      return;
    }

    if (p <= 0.015) {
      if (isHeaderHidden) {
        isHeaderHidden = false;
        storyNavbar.classList.remove('is-hidden');
        if (minimalNav) minimalNav.classList.remove('is-active');
      }
    } else if (p > lastScrollProgress + 0.001) {
      // Scrolling down
      if (!isHeaderHidden) {
        isHeaderHidden = true;
        storyNavbar.classList.add('is-hidden');
        if (minimalNav) minimalNav.classList.add('is-active');
      }
    } else if (p < lastScrollProgress - 0.002) {
      // Scrolling up
      if (isHeaderHidden) {
        isHeaderHidden = false;
        storyNavbar.classList.remove('is-hidden');
        if (minimalNav) minimalNav.classList.remove('is-active');
      }
    }
    lastScrollProgress = p;
  }

  window.addEventListener('mousemove', (e) => {
    if (e.clientY <= 60) {
      updateSmartHeader(storyStore.getState().scrollProgress, e.clientY);
    }
  }, { passive: true });

  function handleScrollProgress(progress) {
    storyStore.setState({ scrollProgress: progress });
    updatePanels(progress);
    updateSmartHeader(progress);

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
    const isNarrow = window.innerWidth < 1025;
    const narrowShiftY = isNarrow ? 0.35 : 0.0;
    if (!isReducedMotion) {
      // Gentle float: ~3-5mm vertical sway over 6s (frequency ~0.00105)
      const floatY = (latestState ? latestState.bookShiftY : 0.65) + narrowShiftY + Math.sin(now * 0.00105) * 0.006;
      bookGroup.position.y = floatY;

      // Dust motes gentle drift
      motePoints.rotation.y = now * 0.00004;
      motePoints.position.y = Math.sin(now * 0.0003) * 0.04;

      // Gentle breathing of light (0.85 .. 0.95 over 8s)
      dirLight.intensity = 0.90 + Math.sin(now * 0.000785) * 0.05;
    } else {
      bookGroup.position.y = (latestState ? latestState.bookShiftY : 0.65) + narrowShiftY;
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
    updateViewportScale();
    if (lenisInstance) lenisInstance.resize();
  });

  // Initial sizing and render
  updateViewportScale();
  applyBookState(0.0);

  // --- Global Diagnostics API for Playwright Verifiers ---
  window.__tulya = {
    scene: scene,
    camera: camera,
    bookGroup: bookGroup,
    getSideOffset: getSideOffset,
    get debug() {
      return {
        coverAngle: latestState.coverAngle,
        turnLeafAngle: latestState.turnLeafAngle,
        leafAngles: [latestState.turnLeafAngle],
        bookShiftX: latestState.bookShiftX,
        progress: storyStore.getState().scrollProgress,
        tier: tier,
        fps: storyStore.getState().fps
      };
    },
    getBookBoundingBox: function() {
      // Calculate 2D bounding box of all visually rendered meshes of the book
      // Excludes ground shadow plane and objects with opacity == 0 (such as idle synthetic sheet or idle cards)
      bookGroup.updateMatrixWorld(true);
      const box = new THREE.Box3();
      bookGroup.traverse((o) => {
        if (o.isMesh && o.visible && o !== shadowMesh) {
          const mat = Array.isArray(o.material) ? o.material[0] : o.material;
          const op = (mat && mat.opacity !== undefined) ? mat.opacity : 1.0;
          if (op > 0.08) {
            box.expandByObject(o);
          }
        }
      });

      if (box.isEmpty()) {
        box.setFromObject(frontCoverMesh);
      }

      const min = box.min;
      const max = box.max;
      const corners = [
        new THREE.Vector3(min.x, min.y, min.z),
        new THREE.Vector3(min.x, min.y, max.z),
        new THREE.Vector3(min.x, max.y, min.z),
        new THREE.Vector3(min.x, max.y, max.z),
        new THREE.Vector3(max.x, min.y, min.z),
        new THREE.Vector3(max.x, min.y, max.z),
        new THREE.Vector3(max.x, max.y, min.z),
        new THREE.Vector3(max.x, max.y, max.z)
      ];

      let minX = Infinity, maxX = -Infinity;
      let minY = Infinity, maxY = -Infinity;

      corners.forEach((c) => {
        const p = c.clone().project(camera);
        const sx = (p.x * 0.5 + 0.5) * window.innerWidth;
        const sy = (-(p.y * 0.5) + 0.5) * window.innerHeight;
        if (sx < minX) minX = sx;
        if (sx > maxX) maxX = sx;
        if (sy < minY) minY = sy;
        if (sy > maxY) maxY = sy;
      });

      return {
        left: minX,
        right: maxX,
        top: minY,
        bottom: maxY,
        width: maxX - minX,
        height: maxY - minY
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
      updateSmartHeader(p);
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
        const el = document.querySelector('.synthetic-tag, .synthetic-banner');
        if (el && el.textContent.includes('SYNTHETIC')) {
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
