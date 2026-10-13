# CareCast — Vendored Frontend Dependencies & Versions

This document records all third-party libraries vendored into `web/vendor/` per TRD §9.1 and Phase 5 Task 2.
No third-party scripts are loaded from CDNs or external origins at runtime (enforced by Content Security Policy `script-src 'self'`).

---

## 1. Chart.js

| Attribute | Value |
|---|---|
| **Library Name** | Chart.js |
| **Pinned Version** | `4.4.7` |
| **File Path** | `web/vendor/chart.umd.js` |
| **Distribution Build** | Universal Module Definition (`dist/chart.umd.js`) |
| **Exact Source** | Official npm Registry: `https://registry.npmjs.org/chart.js/-/chart.js-4.4.7.tgz` |
| **Tarball Path** | `package/dist/chart.umd.js` |
| **File Size** | 205,615 bytes |
| **SHA-256 Checksum** | `2812cb8825fdc57469eb2f7bb055e9429244e599920511ee477e828499b632cb` |
| **License** | MIT (see `web/vendor/LICENSES.md`) |
| **Security Audit** | Clean — 0 known vulnerabilities / CVEs on GitHub Security Advisories (`github.com/chartjs/Chart.js/security/advisories`) and npm advisory database. (CVE-2020-7746 affected `< 2.9.4` only). |
