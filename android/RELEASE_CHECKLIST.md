# Android release checklist

1. **API base URL** — Update `staging` / `prod` `API_BASE_URL` values in `app/build.gradle.kts` (product flavors) to your real backend hosts. `dev` keeps `10.0.2.2` for the emulator.
2. **Versioning** — Bump `versionCode` / `versionName` in `app/build.gradle.kts` before each Play upload.
3. **Signing** — Configure a release keystore (not committed). Use `signingConfigs.release` and `buildTypes.release` with `minifyEnabled` / `shrinkResources` once you verify R8 rules.
4. **Backend + Clerk** — Confirm `smartattendance://auth?session_token=...` deep links use a **short-lived** Clerk session JWT and HTTPS-only issuance from your web portal.
5. **Smoke test** — Run `./gradlew :app:assembleProdRelease` (or your chosen flavor) and verify student attendance + staff session start on a physical device with GPS.
6. **CI** — Ensure GitHub Actions `Android CI` workflow is green on `main` before tagging a release.
