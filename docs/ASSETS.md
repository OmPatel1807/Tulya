# Tulya 3D & Frontend Assets Register

This register documents all 3D models, textures, and vendor libraries utilized in the Tulya bilingual statutory auditor frontend, in compliance with open-source and creative commons licensing.

| Asset Name | Type / Format | Author / Source | License | Date Added | Modification & Usage Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `three.min.js` (r128) | JavaScript Library (`.js`) | Mr.doob & Three.js Contributors ([threejs.org](https://threejs.org/)) | MIT License | 2026-11-01 | Vendored locally in `frontend/static/vendor/three.min.js` (589 KB) for 100% offline execution. |
| `Procedural Floating Legal Sheets` | Procedural 3D Mesh (`THREE.PlaneGeometry` + Canvas Texture) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Lightweight procedural twin sheets representing English and Hindi gazettes. Renders text lines onto 2D canvas texture with native browser Devanagari text shaping. 0 KB external file size. |
| `Procedural Clause Card Stack` | Procedural 3D Mesh (`THREE.BoxGeometry` / `THREE.PlaneGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Procedural low-poly clause card geometry created dynamically at runtime; colors mapped to pastel sage (`#A8CDB5`) and muted coral (`#E8918F`). |
| `Procedural Semantic Inspection Lens` | Procedural 3D Mesh (`THREE.TorusGeometry` + `THREE.CylinderGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Glass magnifier frame with subtle transmission material, gliding across clause cards during semantic review milestone. 0 KB external file size. |
| `Procedural Pastel Connecting Threads` | Procedural 3D Curves (`THREE.Line` / `THREE.BufferGeometry`) | Tulya Architectural Engine | Procedural / Code (MIT) | 2026-11-01 | Soft bezier spline threads connecting aligned provisions between language columns. |

---

### Prohibited Content Compliance Check
- [x] No search engine scraping.
- [x] No State Emblem of India or Ashoka Chakra.
- [x] No Indian National Flag.
- [x] No real people, government officials, or judge photographs.
- [x] No court or government building photography.
- [x] No commercial brand logos.
- [x] 100% offline support (zero CDN reliance; total external 3D asset size = 0 KB, library size < 600 KB, total well under 2 MB limit).

