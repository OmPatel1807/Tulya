# Tulya - Bundled Public Assets Register

This register documents all external 3D environment maps and PBR surface textures bundled locally for offline rendering in the Tulya bilingual statutory auditor.

All assets are licensed under **Creative Commons CC0 1.0 Universal (Public Domain Dedication)** and are bundled locally in `frontend/public/assets/` to guarantee 100% offline reliability without external CDN runtime dependencies.

---

## 1. Studio Environment Map (HDRI)

| Property | Details |
| :--- | :--- |
| **Asset Name** | Studio Small 03 (`studio_small_03`) |
| **Asset Type** | High Dynamic Range Environment Map (`.hdr`) |
| **Resolution** | 1024 × 512 (1k equirectangular) |
| **Asset Page URL** | https://polyhaven.com/a/studio_small_03 |
| **Direct Source URL** | https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_03_1k.hdr |
| **Local Path** | `frontend/public/assets/studio_small_03_1k.hdr` |
| **Author / Provider** | Andreas Mischok & Poly Haven Contributors |
| **License** | Creative Commons CC0 1.0 Universal (Public Domain Dedication) |
| **Date Downloaded** | 2026-11-01 |
| **File Size** | 1,686,299 bytes (~1.61 MB) |
| **Visual Characteristics**| Soft, low-contrast diffuse indoor studio illumination with balanced neutral fill and zero harsh specular hot-spots. |

---

## 2. Book Cover Material (Leather / Cloth PBR)

| Property | Details |
| :--- | :--- |
| **Asset Name** | Brown Leather (`brown_leather`) |
| **Asset Type** | PBR Texture Set (Albedo/Diffuse, OpenGL Normal, Roughness) |
| **Resolution** | 1024 × 1024 (1k), compressed to WebP (quality 85) |
| **Asset Page URL** | https://polyhaven.com/a/brown_leather |
| **Direct Source URLs** | • Diffuse: https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_leather/brown_leather_albedo_1k.jpg<br>• Normal GL: https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_leather/brown_leather_nor_gl_1k.jpg<br>• Roughness: https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_leather/brown_leather_rough_1k.jpg |
| **Local Paths** | • `frontend/public/assets/cover_leather_diffuse_1k.webp` (196,600 bytes)<br>• `frontend/public/assets/cover_leather_nor_gl_1k.webp` (245,844 bytes)<br>• `frontend/public/assets/cover_leather_rough_1k.webp` (446,052 bytes) |
| **Author / Provider** | Rob Tuytel & Poly Haven Contributors |
| **License** | Creative Commons CC0 1.0 Universal (Public Domain Dedication) |
| **Date Downloaded** | 2026-11-01 |
| **Visual Characteristics**| Fine-grain bound leather grain texture, providing tactile hardbound surface micro-relief for the book cover board. |

---

## 3. Page Leaves Paper Material (Parchment / Paper PBR)

| Property | Details |
| :--- | :--- |
| **Asset Name** | Paper 001 (`Paper001`) |
| **Asset Type** | PBR Texture Set (Color/Diffuse, OpenGL Normal, Roughness) |
| **Resolution** | 1024 × 1024 (1k), compressed to WebP (quality 85) |
| **Asset Page URL** | https://ambientcg.com/view?id=Paper001 |
| **Direct Source URL** | https://ambientcg.com/get?file=Paper001_1K-JPG.zip |
| **Local Paths** | • `frontend/public/assets/paper_diffuse_1k.webp` (45,436 bytes)<br>• `frontend/public/assets/paper_nor_gl_1k.webp` (319,446 bytes)<br>• `frontend/public/assets/paper_rough_1k.webp` (233,688 bytes) |
| **Author / Provider** | Lennart Demes (ambientCG) |
| **License** | Creative Commons CC0 1.0 Universal (Public Domain Dedication) |
| **Date Downloaded** | 2026-11-01 |
| **Visual Characteristics**| Natural off-white rag paper grain with gentle fiber displacement, matte roughness, and non-distracting surface texture. |

---

## 4. Constitution of India Hero Volume Cover (Official Edition)

| Property | Details |
| :--- | :--- |
| **Asset Name** | Constitution of India Official Volume Cover (`constitution_cover`) |
| **Asset Type** | Photographic Cover Texture (Albedo / Diffuse) |
| **Resolution** | 776 × 1024, bundled as WebP (357 KB) and JPEG (649 KB) |
| **Source** | User-Provided Official Photograph of the Authentic Constitution of India Volume |
| **Local Paths** | • `frontend/public/assets/constitution_cover.webp` (357,252 bytes)<br>• `frontend/public/assets/constitution_cover.jpg` (649,956 bytes) |
| **Author / Provider** | Government of India Official Publication Archive (Public Domain) |
| **License** | Public Domain (Official text and facsimile of the Constitution of India) |
| **Date Added** | 2026-11-01 |
| **Visual Characteristics**| Authentic dark charcoal leather with intricate illuminated gold leaf borders, gold embossed title lettering, and official emblem. |

---

## 5. Animation & Smooth Scroll Engine Libraries

| Asset Name | Type / Format | Author / Source | License | Date Added | Modification & Usage Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lenis.min.js` (v1.1.18) | JavaScript Smooth Scroll Library | Studio Freight ([github.com/darkroomengineering/lenis](https://github.com/darkroomengineering/lenis)) | MIT License | 2026-11-01 | Vendored in `frontend/static/vendor/lenis.min.js` (13 KB) for hardware-accelerated, jitter-free scroll interpolation. |
| `gsap.min.js` (v3.12.5) | JavaScript Animation Library | GreenSock ([greensock.com/gsap](https://greensock.com/gsap)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/gsap.min.js` (72 KB) for synchronized 60fps ticker loop (`lagSmoothing(0)`). |
| `ScrollTrigger.min.js` (v3.12.5) | Scroll-Linked Timeline Plugin | GreenSock ([greensock.com/scrolltrigger](https://greensock.com/scrolltrigger)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/ScrollTrigger.min.js` (43 KB) with Lenis proxy binding for buttery timeline progression. |

---

## 5. Compliance & Verification

- **License Verification**: All upstream asset providers (Poly Haven and ambientCG) explicitly license all assets under CC0 1.0 Universal.
- **Offline Self-Containment**: Zero external CDN requests. All files are bundled directly in the local repository under `frontend/public/assets/`.
- **Prohibited Content Check**:
  - Zero national emblems or Ashoka symbols.
  - Zero flags or tricolor motifs.
  - Zero photographs of persons, officials, or judicial buildings.
- **Procedural Fallback**: If file access is interrupted, the renderer gracefully falls back to the built-in procedural CanvasTextures and normal maps.

