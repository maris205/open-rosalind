import assert from "node:assert/strict";
import test from "node:test";

import {
  isFormalRelease,
  tauriArguments,
  validateFormalReleaseEnvironment
} from "./macos-release-policy.mjs";

test("formal release flag is consumed before invoking Tauri", () => {
  assert.equal(isFormalRelease(["--formal-release", "--bundles", "app,dmg"], {}), true);
  assert.deepEqual(
    tauriArguments(["--formal-release", "--bundles", "app,dmg"]),
    ["--bundles", "app,dmg"]
  );
});

test("formal release can be enabled by the environment", () => {
  assert.equal(isFormalRelease([], { OPENROSALIND_FORMAL_RELEASE: "1" }), true);
});

test("formal release fails closed without signing credentials", () => {
  assert.throws(
    () => validateFormalReleaseEnvironment({}),
    /Developer ID signing identity/
  );
  assert.throws(
    () => validateFormalReleaseEnvironment({ APPLE_SIGNING_IDENTITY: "-" }),
    /Developer ID signing identity/
  );
});

test("formal release fails closed without complete notarization credentials", () => {
  assert.throws(
    () => validateFormalReleaseEnvironment({ APPLE_SIGNING_IDENTITY: "Developer ID Application: Example" }),
    /notarization credentials/
  );
  assert.throws(
    () => validateFormalReleaseEnvironment({
      APPLE_SIGNING_IDENTITY: "Developer ID Application: Example",
      APPLE_API_ISSUER: "issuer",
      APPLE_API_KEY: "KEYID"
    }),
    /notarization credentials/
  );
});

test("formal release accepts either supported credential family", () => {
  assert.doesNotThrow(() => validateFormalReleaseEnvironment({
    APPLE_SIGNING_IDENTITY: "Developer ID Application: Example",
    APPLE_API_ISSUER: "issuer",
    APPLE_API_KEY: "KEYID",
    APPLE_API_KEY_PATH: "/private/key.p8"
  }));
  assert.doesNotThrow(() => validateFormalReleaseEnvironment({
    APPLE_SIGNING_IDENTITY: "Developer ID Application: Example",
    APPLE_ID: "developer@example.com",
    APPLE_PASSWORD: "app-password",
    APPLE_TEAM_ID: "TEAMID"
  }));
});
