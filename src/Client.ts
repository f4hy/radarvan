import { DefaultApi, Configuration, DefaultConfig } from "./api"

function getConfig(): Configuration {
  // Using a framework-agnostic check for NODE_ENV
  if (process.env.NODE_ENV === 'development') {
    return new Configuration({
  basePath: 'http://localhost:8000',
});
  }
  // This will be used in production
    return new Configuration({
  basePath: 'https://localhost',
});
	
}
const config = getConfig()
export const Client = new DefaultApi(config)

