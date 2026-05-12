import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Downgraded from error to warn. The default rule flags
      // legitimate "external data sync" patterns: hydrating form
      // state from a fetched API response, syncing URL params into
      // local state, reading DOM state set by the no-flash theme
      // script, resetting modal state when the open prop flips.
      // React's escape hatches for these (useSyncExternalStore,
      // computing-instead-of-effects) don't fit cases where the
      // outside-React data needs to live in editable component
      // state.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
