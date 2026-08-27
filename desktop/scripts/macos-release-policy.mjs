export function isFormalRelease(argumentsList, environment = process.env) {
  return argumentsList.includes("--formal-release") || environment.OPENROSALIND_FORMAL_RELEASE === "1";
}

export function tauriArguments(argumentsList) {
  return argumentsList.filter((argument) => argument !== "--formal-release");
}

export function validateFormalReleaseEnvironment(environment = process.env) {
  const hasSigningIdentity = Boolean(
    environment.APPLE_SIGNING_IDENTITY && environment.APPLE_SIGNING_IDENTITY !== "-"
  );
  if (!hasSigningIdentity) {
    throw new Error(
      "Formal macOS release requires a Developer ID signing identity installed in the build keychain."
    );
  }

  const hasApiCredentials = Boolean(
    environment.APPLE_API_ISSUER
      && environment.APPLE_API_KEY
      && environment.APPLE_API_KEY_PATH
  );
  const hasAppleIdCredentials = Boolean(
    environment.APPLE_ID && environment.APPLE_PASSWORD && environment.APPLE_TEAM_ID
  );
  if (!hasApiCredentials && !hasAppleIdCredentials) {
    throw new Error(
      "Formal macOS release requires complete App Store Connect API or Apple ID notarization credentials."
    );
  }
}
