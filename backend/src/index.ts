import app from './app.js';
import { env } from './config/env.js';

const PORT = env.PORT;

app.listen(PORT, () => {
  console.log(`\n🚀 Freelanker API running`);
  console.log(`   Local:        http://localhost:${PORT}`);
  console.log(`   Health:       http://localhost:${PORT}/api/health`);
  console.log(`   ContractFlow: ${env.CONTRACTFLOW_SERVICE_URL}`);
  console.log(`   Mode:         ${env.NODE_ENV}\n`);

  if (env.isProduction && (env.CONTRACTFLOW_SERVICE_URL.includes('127.0.0.1') || env.CONTRACTFLOW_SERVICE_URL.includes('localhost'))) {
    console.warn('[Startup Warning] CONTRACTFLOW_SERVICE_URL points to loopback in production; set CONTRACTFLOW_SERVICE_URL to the deployed ContractFlow service URL.');
  }
});
