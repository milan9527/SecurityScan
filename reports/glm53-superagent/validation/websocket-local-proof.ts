// Isolated loopback proof: original gateway, synthetic event, no production services.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { executionWebSocketGateway as gateway } from '/home/ec2-user/bedrock/agentcore-superagent-update/super-agent/backend/src/websocket/execution.gateway.ts';
const require = createRequire('/home/ec2-user/bedrock/agentcore-superagent-update/super-agent/backend/package.json');
const Fastify = require('fastify');
const { WebSocket } = require('ws');
async function main() {
  const app = Fastify();
  let socket: any;
  try {
    await gateway.register(app);
    const address = await app.listen({host: '127.0.0.1', port: 0});
    const event = {executionId: 'synthetic-execution-id', type: 'node_completed', output: {marker: 'synthetic-proof-only'}};
    const received: any[] = [];
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Timeout')), 5000);
      socket = new WebSocket(address.replace('http:', 'ws:') + '/ws/executions');
      socket.on('error', reject);
      socket.on('open', () => socket.send(JSON.stringify({type: 'subscribe', executionId: event.executionId})));
      socket.on('message', (raw: Buffer) => {
        const msg = JSON.parse(raw.toString());
        received.push(msg);
        if (msg.type === 'subscribed') gateway.broadcastEvent(event as any);
        if (msg.type === 'workflow_event') { clearTimeout(timer); resolve(); }
      });
    });
    const result = {tested_at: new Date().toISOString(), scope: 'isolated original gateway on loopback; not full application or deployed ingress', credentials_sent: false, execution_id_known: true, synthetic_event_received: received.some(x => x.event?.output?.marker === 'synthetic-proof-only'), received};
    writeFileSync('/home/ec2-user/bedrock/scan/reports/glm53-superagent/validation/websocket-local-proof.json', JSON.stringify(result, null, 2));
    if (!result.synthetic_event_received) throw new Error('Missing marker');
  } finally { if (socket) socket.terminate(); gateway.close(); await app.close(); }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
