# Tulya 3D & Frontend Assets Register

This register documents all 3D models, textures, and vendor libraries utilized in the Tulya bilingual statutory auditor frontend, in compliance with open-source and creative commons licensing.

| Asset Name | Type / Format | Author / Source | License | Date Added | Modification & Usage Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `three.min.js` (r128) | JavaScript Library (`.js`) | Mr.doob & Three.js Contributors ([threejs.org](https://threejs.org/)) | MIT License | 2026-11-01 | Vendored locally in `frontend/static/vendor/three.min.js` (589 KB) for 100% offline execution. |
| `lenis.min.js` (v1.1.18) | JavaScript Library (`.js`) | Studio Freight ([github.com/darkroomengineering/lenis](https://github.com/darkroomengineering/lenis)) | MIT License | 2026-11-01 | Vendored in `frontend/static/vendor/lenis.min.js` (13 KB) for jitter-free scroll interpolation. |
| `gsap.min.js` (v3.12.5) | JavaScript Library (`.js`) | GreenSock ([greensock.com/gsap](https://greensock.com/gsap)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/gsap.min.js` (72 KB) for high-performance 60fps ticker. |
| `ScrollTrigger.min.js` (v3.12.5) | JavaScript Plugin (`.js`) | GreenSock ([greensock.com/scrolltrigger](https://greensock.com/scrolltrigger)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/ScrollTrigger.min.js` (43 KB) for Lenis proxy binding. |
| `Procedural Constitution Book Board` | Procedural 3D Mesh (`THREE.BoxGeometry`, `THREE.CylinderGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Procedural hardbound book cover in deep ink-teal (`#234A52`) with brass-foil typography and abstract border lines. 0 KB external file size. |
| `Procedural Brass Foil Title Texture` | Procedural Canvas Texture (`THREE.CanvasTexture`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Canvas-rendered brass foil typography: "THE CONSTITUTION OF INDIA / भारत का संविधान" with abstract gold framing. Zero copyrighted illustrations or emblems. |
| `Procedural Animated Leaves & Preamble Spreads` | Procedural 3D Planes (`THREE.PlaneGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Double-sided parchment leaves (`#F3ECDD`) pivoted at spine ($x=0$) with page curl dynamics. Displays official Preamble text in English and Hindi via 2D Canvas shaping. |
| `Procedural Synthetic Demo Sheet` | Procedural 3D Plane (`THREE.PlaneGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Loose leaf paper insert labeled "SYNTHETIC DEMO EXAMPLE" demonstrating clause divergence without altering Constitution spreads. |
| `Procedural Semantic Magnifier Lens` | Procedural 3D Mesh (`THREE.TorusGeometry` + `THREE.CircleGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Glass inspection lens with stone rim (`#4B5A6B`) and standard specular transmission gliding during semantic review. |
| `studio_small_03_1k.hdr` | Studio Environment Map (`.hdr`) | Andreas Mischok & Poly Haven ([polyhaven.com](https://polyhaven.com/a/studio_small_03)) | CC0 1.0 Universal | 2026-11-01 | Bundled in `frontend/public/assets/studio_small_03_1k.hdr` (1.61 MB) for diffuse, low-contrast studio lighting. |
| `cover_leather_*_1k.webp` | Cover PBR Material (Albedo, NormalGL, Roughness) | Rob Tuytel & Poly Haven ([polyhaven.com](https://polyhaven.com/a/brown_leather)) | CC0 1.0 Universal | 2026-11-01 | Bundled in `frontend/public/assets/` (WebP 1k) providing fine-grained leather surface micro-relief. |
| `paper_*_1k.webp` | Page Leaves PBR Material (Color, NormalGL, Roughness) | Lennart Demes & ambientCG ([ambientcg.com](https://ambientcg.com/view?id=Paper001)) | CC0 1.0 Universal | 2026-11-01 | Bundled in `frontend/public/assets/` (WebP 1k) providing natural paper grain texture. |

---

### Prohibited Content Compliance Verification
- [x] **No State Emblem of India** or Ashoka lion capital.
- [x] **No Ashoka Chakra** or national symbols.
- [x] **No Indian National Flag** or tricolor (saffron/white/green) color arrangements.
- [x] **No real people**, government officials, or judge photographs.
- [x] **No court or government building photography**.
- [x] **No commercial brand logos** or printed Constitution cover illustrations.
- [x] **100% offline support** (all geometries and textures generated procedurally in code; 0 KB network downloads).
- [x] **Constitution integrity preserved**: The mismatch demonstration is explicitly isolated on the loose sheet labeled `"SYNTHETIC DEMO EXAMPLE"`.
