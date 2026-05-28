# Vendor libs (read-only, sync-managed)

Bibliotecas baixadas via `scripts/sync_vendor_libs.py`. **Não edite manualmente.**
Versões e SHA256 são pinados no script — re-sync valida automaticamente.

- **Last sync:** `2026-05-21T19:04:13Z`
- **Source:** jsdelivr.net (URLs canônicas abaixo)

## Manifest

| File | Version | SHA256 | URL |
|------|---------|--------|-----|
| `d3.min.js` | 7.9.0 | `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539` | <https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js> |
| `plot.umd.min.js` | 0.6.17 | `4358086467740777dd788d6b27a95cebdbaefdd50c730a3060117073bd7134cb` | <https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/dist/plot.umd.min.js> |
| `mermaid.min.js` | 11.4.1 | `a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e` | <https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js> |
| `lucide.min.js` | 0.469.0 | `5de4fffddc1b41ad1226d5e986fcc552adb8ad9efd1566e71dfdcdb664f9a6c2` | <https://cdn.jsdelivr.net/npm/lucide@0.469.0/dist/umd/lucide.min.js> |

## Re-sync

```
python3 scripts/sync_vendor_libs.py            # download + validate
python3 scripts/sync_vendor_libs.py --check-only  # validate sem baixar
```

## Bump de versão

Veja o docstring de `scripts/sync_vendor_libs.py`.
