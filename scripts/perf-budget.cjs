#!/usr/bin/env node
const { spawn } = require('child_process');
const http = require('http');

const PORT = Number(process.env.PERF_PORT || 5050);
const STARTUP_TIMEOUT_MS = Number(process.env.PERF_STARTUP_TIMEOUT_MS || 20000);
const STARTUP_BUDGET_MS = Number(process.env.PERF_STARTUP_BUDGET_MS || 5000);

const child = spawn(process.execPath, ['server-modular.js'], {
  env: {
    ...process.env,
    PORT: String(PORT),
    ENABLE_FILE_LOGS: 'false',
    NODE_ENV: process.env.NODE_ENV || 'production'
  },
  stdio: ['ignore', 'inherit', 'inherit']
});

const start = Date.now();
const deadline = start + STARTUP_TIMEOUT_MS;

function checkReady() {
  const req = http.get({
    hostname: '127.0.0.1',
    port: PORT,
    path: '/health',
    method: 'GET',
    timeout: 1000
  }, (res) => {
    if (res.statusCode === 200) {
      const elapsed = Date.now() - start;
      const ok = elapsed <= STARTUP_BUDGET_MS;
      console.log(`[perf-budget] Startup time: ${elapsed}ms (budget ${STARTUP_BUDGET_MS}ms) -> ${ok ? 'OK' : 'FAIL'}`);
      try { child.kill('SIGINT'); } catch (_) {}
      setTimeout(() => process.exit(ok ? 0 : 1), 750);
    } else {
      retryOrTimeout();
    }
  });
  req.on('error', retryOrTimeout);
}

function retryOrTimeout() {
  if (Date.now() > deadline) {
    console.error(`[perf-budget] Startup timed out after ${STARTUP_TIMEOUT_MS}ms`);
    try { child.kill('SIGKILL'); } catch (_) {}
    process.exit(1);
  } else {
    setTimeout(checkReady, 250);
  }
}

child.on('exit', (code, signal) => {
  if (Date.now() < deadline) {
    console.error(`[perf-budget] Server exited early with code=${code} signal=${signal}`);
    process.exit(1);
  }
});

setTimeout(checkReady, 250);

