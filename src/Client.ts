import { DefaultApi, Configuration, DefaultConfig } from "./api"

const config = new Configuration({
  basePath: 'http://localhost:8000',
});
export const Client = new DefaultApi(config)

