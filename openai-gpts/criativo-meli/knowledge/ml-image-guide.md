# Mercado Livre Image Guide — Criativo Meli

*Last updated: 2026-06-17*

---

## Section 1 — Technical Specs

| Spec | Requirement |
|------|-------------|
| Cover image format | Square (1:1 ratio) — mandatory |
| Recommended resolution | 1500×1500px minimum |
| Cover background | Pure white (#FFFFFF) — mandatory |
| Supported formats | JPG, PNG |
| Max file size | 10MB per image |
| Text on cover image | Prohibited (ML policy) |
| Watermarks | Prohibited |
| Total listing images | Up to 12 images allowed |

---

## Section 2 — Prohibited Elements

NEVER include in any Mercado Livre listing image:
- Competitor logos or brand names (Amazon, Shopee, AliExpress, etc.)
- Promotional text on the cover image (prices, discounts, percentage off, "promoção")
- Decorative frames or borders that partially obscure the product
- Low-resolution or pixelated visuals
- Misleading elements that don't represent the actual product being sold
- Adult content or inappropriate material
- Contact information: phone numbers, email, WhatsApp, website URLs
- Social media handles or icons
- Certification logos the seller does not actually hold

---

## Section 3 — Style Guide (Clean & Modern)

### Color Palette

| Context | Colors |
|---------|--------|
| Light backgrounds | White (#FFFFFF), light gray (#F5F5F5, #EEEEEE), off-white (#FAFAFA) |
| Dark backgrounds (hero only) | Charcoal (#1A1A1A), deep navy (#0D1B2A), dark slate (#2C3E50) |
| Accent colors | Use the product's own dominant colors — do not force brand colors |
| Avoid | Neon colors, busy gradients, overly saturated backgrounds, clashing palettes |

### Typography (when text appears in DALL-E-generated images)

- Keep text minimal — maximum 5 words per text element
- Style: clean sans-serif (imagine Helvetica, Inter, or similar)
- Colors: high contrast (white on dark, near-black on light)
- Avoid: decorative fonts, script/calligraphy fonts, ALL CAPS in long sentences
- Note: DALL-E text accuracy is limited — use visual elements over text whenever possible

### Composition Principles

- Clean, uncluttered backgrounds — generous white space around the product
- Professional studio lighting: soft, directional, no harsh shadows
- Rule of thirds or centered composition depending on image type
- Consistent padding and breathing room across all 9 images
- The product should always be recognizable and prominent

---

## Section 4 — Category-Specific Visual Guidance

### Electronics

- **Hero shot:** dark background (charcoal or deep navy) — conveys premium and tech feel
- **Close-up:** focus on ports, buttons, display, indicator lights, or surface finish
- **Lifestyle:** person actively operating the device, not just holding it
- **Benefits:** use icons to represent specs (battery, connectivity, range, power)

### Home Decor

- **Lifestyle:** show in a real room context — living room, bedroom, dining area, kitchen
- **Hero shot:** neutral background (white, light gray, or warm beige)
- **Close-up:** texture of material — fabric weave, ceramic glaze, wood grain, metal finish
- **Benefits:** icons for material, size, use context, ease of cleaning

### Clothing & Accessories

- **Lifestyle:** model wearing the item in a natural, aspirational pose
- **Hero:** flat lay on white/neutral surface, or product on hanger/stand
- **Close-up:** fabric texture, stitching detail, zipper or button hardware
- **Benefits:** fit, material, size range, care instructions as icons

### Supplements & Food

- **Lifestyle:** person in active context — gym, kitchen, outdoor, morning routine
- **Hero:** product floating, clean dramatic background; optional ingredient splash
- **Close-up:** label detail, texture of product, packaging quality
- **Benefits:** key ingredients or nutritional highlights as icon cards

### General / Multi-category

When category is unclear or mixed: default to white or light gray background for all images except Hero (use dark) and Lifestyle (use contextually appropriate setting).

---

## Section 5 — Image Role Reference (7-image flow)

| # | Type | Primary Goal | Key Visual Element | Background |
|---|------|-------------|-------------------|------------|
| 1 | Uso Real | Social proof | Person using product in context | Natural/lifestyle setting |
| 2 | Hero Product | Premium feel | Floating product, dramatic light | Dark charcoal or navy |
| 3 | Composite / Detalhe | Quality proof | 2–3 circular close-up cutouts | White or very light gray |
| 4 | Feature em Destaque | Inform | Arrow/highlight on main feature | Soft dark background |
| 5 | Original / Garantia | Trust | Shield badge + product | Clean simple setting |
| 6 | Social Proof | Buy intent | 5-star review card overlay | Lifestyle setting |
| 7 | FAQ | Reduce friction | Q&A card layout | White or very light gray |

---

## Section 6 — DALL-E Prompt Best Practices

When constructing DALL-E prompts for each image type, always include:
1. **Product description** derived from the user's uploaded photos and description
2. **Image style:** "professional product photography, studio quality, clean and modern"
3. **Background spec** from the table above
4. **Lighting:** "soft studio lighting with subtle shadows"
5. **Format:** "square 1:1 aspect ratio"
6. **What NOT to include:** text overlays unless specifically requested (image types 2, 4, 6, 8)

Example pattern:
> "Professional product photography of [product description], [background spec], soft studio lighting with subtle shadows, clean modern aesthetic, square format, no text"