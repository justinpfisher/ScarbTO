# Community export dependencies

- jsPDF 4.2.1, official `parallax/jsPDF` tag `v4.2.1`, browser UMD distribution, Git blob `0e600d49d2b2bf81dd97c1509e22d108c2ddd3b4`; MIT notice retained in `jspdf-LICENSE.txt`. Retrieved through the GitHub connector on November 12, 2026. Browser-only text APIs are used, not HTML, annotations, remote images or server-side file access. This release fixes the published HTML/PDF injection issues; independent review and exact rendered qualification remain required.
- DM Sans source font and SIL OFL copied unchanged from the approved brand preparation. Official google/fonts ofl/dmsans/DMSans[opsz,wght].ttf blob c672f98060af9b2c85fca704ebd5ad9a8717c1df; SHA-256 8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d. Original authors/licence retained. Final render/embedding/glyph coverage must be qualified; a missing glyph must stop PDF/image export rather than silently replace source text.

Focused isolated qualification has verified actual embedded-font PDF bytes, rendered PDF pixels, and 300-dpi PNG output. This is not a claim of complete acceptance or live deployment. No external service or runtime CDN request is introduced.
