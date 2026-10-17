export default {
  input: "http://localhost:8000/openapi.json",
  output: { path: "src/api" },
  plugins: [
    {
      name: "@hey-api/client-fetch",
      baseUrl: false,
      throwOnError: true,
      runtimeConfigPath: "./src/lib/apiConfig.ts",
    },
    { name: "@hey-api/typescript", case: "preserve", enums: "javascript" },
    { name: "@hey-api/transformers", dates: true },
    { name: "@hey-api/sdk", transformer: true },
    "@tanstack/react-query",
  ],
}
