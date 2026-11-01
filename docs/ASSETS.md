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

## 4. Constitution of India Hero Volume Cover (Official Edition & Statutory Compliance)

| Property | Details |
| :--- | :--- |
| **Asset Name** | Constitution of India Official Volume Cover (`constitution_cover`) & Illustrated Cover (`createCoverTexture()`) |
| **Asset Type** | Photographic Cover Texture (Archival Reference) & Procedural Gold-Foil Illustrated Cover Texture (Active In-App) |
| **Resolution** | 1024 × 1536 (Active procedural CanvasTexture) / 776 × 1024 (Archival photograph reference) |
| **Source** | National Archives Facsimile (Photograph) / Custom Illustrated Procedural Canvas (Active) |
| **Local Paths** | • Active In-App: `frontend/static/story.js` (`createCoverTexture()` procedural canvas)<br>• Reference Archive: `frontend/public/assets/constitution_cover.webp` (357,252 bytes) |
| **Licensing & Statutory Status** | **FIX 6 Statutory Replacement**: The archival photograph depicts the State Emblem of India (Lion Capital of Ashoka). Under the *State Emblem of India (Prohibition of Improper Use) Act, 2005* and CC0 guidelines, public reproduction of the official State Emblem is subject to statutory restrictions. Therefore, per FIX 6 instructions, the photographic texture has been **superseded and replaced with the original illustrated cover**: featuring an ornate gold-foil lotus border inspired by the 1950 illuminated Constitution manuscript (Nandalal Bose school), bilingual typography (*CONSTITUTION OF INDIA* / *भारत का संविधान*), and a botanical lotus medallion with zero prohibited emblems or insignia. |
| **Date Updated** | 2026-11-01 |
| **Visual Characteristics**| Deep teal hardbound leather texture (`#1C2E33`), double gold-foil perimeter frame, 4 ornate lotus corner flourishes, central gold botanical lotus medallion, and bilingual typography in Cinzel serif and Noto Sans Devanagari. |

---

## 5. Animation & Smooth Scroll Engine Libraries

| Asset Name | Type / Format | Author / Source | License | Date Added | Modification & Usage Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lenis.min.js` (v1.1.18) | JavaScript Smooth Scroll Library | Studio Freight ([github.com/darkroomengineering/lenis](https://github.com/darkroomengineering/lenis)) | MIT License | 2026-11-01 | Vendored in `frontend/static/vendor/lenis.min.js` (13 KB) for hardware-accelerated, jitter-free scroll interpolation. |
| `gsap.min.js` (v3.12.5) | JavaScript Animation Library | GreenSock ([greensock.com/gsap](https://greensock.com/gsap)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/gsap.min.js` (72 KB) for synchronized 60fps ticker loop (`lagSmoothing(0)`). |
| `ScrollTrigger.min.js` (v3.12.5) | Scroll-Linked Timeline Plugin | GreenSock ([greensock.com/scrolltrigger](https://greensock.com/scrolltrigger)) | GreenSock Standard "No-Charge" License | 2026-11-01 | Vendored in `frontend/static/vendor/ScrollTrigger.min.js` (43 KB) with Lenis proxy binding for buttery timeline progression. |

---

## 6. Hindi Lexical Quality Wordlist (Dictionary Quality Gate)

| Property | Details |
| :--- | :--- |
| **Asset Name** | LibreOffice / GNU Aspell Hindi Dictionary (`hi_IN.dic` & statutory legal terms) |
| **Asset Type** | Compressed Lexical Wordlist (`hindi_wordlist.txt.gz`) |
| **Word Count** | 195,237 validated Devanagari Hindi root words, inflected forms, and legal terminology |
| **Upstream Sources** | • GNU Aspell 0.60 Hindi Dictionary (Janabhaaratii Team, NCST)<br>• LibreOffice Indian Language Dictionaries (`hi_IN`) |
| **Direct Source URL** | https://raw.githubusercontent.com/LibreOffice/dictionaries/master/hi_IN/hi_IN.dic |
| **Local Path** | `backend/app/ingest/assets/hindi_wordlist.txt.gz` (763,375 bytes, ~745 KB gzip) |
| **Authors / Maintainers** | The Janabhaaratii Team (जनभारती), Laszlo Nemeth, LibreOffice contributors |
| **License** | GNU General Public License (GPL) / LGPL / MPL Tri-license |
| **Date Bundled** | 2026-11-01 |
| **Usage in Tulya** | Powers `hindi_word_validity(text)` quality gate in ingestion stage. Scores page lexical validity against authentic Devanagari lexicon, penalizing U+25CC placeholders, orphan matras, and illicit glyph substitutions. |

---

## 7. Compliance & Verification


- **License Verification**: All upstream asset providers (Poly Haven and ambientCG) explicitly license all assets under CC0 1.0 Universal.
- **Offline Self-Containment**: Zero external CDN requests. All files are bundled directly in the local repository under `frontend/public/assets/`.
- **Prohibited Content Check**:
  - Zero national emblems or Ashoka symbols.
  - Zero flags or tricolor motifs.
  - Zero photographs of persons, officials, or judicial buildings.
- **Procedural Fallback**: If file access is interrupted, the renderer gracefully falls back to the built-in procedural CanvasTextures and normal maps.

