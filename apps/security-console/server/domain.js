export const GRACE = 600;
export const nowSeconds = () => Math.floor(Date.now() / 1000);
export function initial() { return {pk:'GPU', version:0, phase:'unmanaged', sessions:{}, jobs:{}, stopAt:null}; }
export function sweep(s, now) {
  const next = structuredClone(s);
  next.sessions = Object.fromEntries(Object.entries(s.sessions).filter(([,v]) => v > now));
  next.jobs = Object.fromEntries(Object.entries(s.jobs).filter(([,v]) => v > now));
  const busy = Object.keys(next.sessions).length + Object.keys(next.jobs).length > 0;
  if (busy) next.stopAt = null;
  else if (next.phase === 'active' || next.phase === 'starting') {
    const deadlines = [...Object.values(s.sessions), ...Object.values(s.jobs)];
    next.stopAt ??= deadlines.length ? Math.max(...deadlines) : now + GRACE;
  }
  return next;
}
export function transition(s, action, now) {
  let n = sweep(s, now);
  if (action.type === 'begin') {
    if (n.phase === 'stopping') throw Object.assign(new Error('GPU 正在停止，请稍后重试'), {status:409});
    if (Object.keys(n.sessions).length >= 20 && !n.sessions[action.user]) throw Object.assign(new Error('演示会话已满'),{status:429});
    n.sessions[action.user] = now + GRACE;
    n.phase = n.phase === 'unmanaged' || n.phase === 'idle' ? 'starting' : n.phase;
    n.stopAt = null;
  } else if (action.type === 'heartbeat') {
    if (!n.sessions[action.user]) throw Object.assign(new Error('演示会话已过期，请重新开始'),{status:409});
    n.sessions[action.user] = now + GRACE; n.stopAt = null;
  } else if (action.type === 'end') {
    delete n.sessions[action.user];
    n = sweep(n,now);
  } else if (action.type === 'job') {
    if (!n.sessions[action.user] || n.phase !== 'active') throw Object.assign(new Error('请先启动演示并等待模型就绪'),{status:409});
    if (Object.keys(n.jobs).length >= 3) throw Object.assign(new Error('最多同时排队 3 个扫描'),{status:429});
    n.jobs[action.id] = now + 14400; n.stopAt = null;
  } else if (action.type === 'finish') {
    delete n.jobs[action.id]; n = sweep(n,now);
  } else if (action.type === 'reserveStop') {
    if (!['starting','active'].includes(n.phase) || n.stopAt === null || n.stopAt > now || Object.keys(n.jobs).length || Object.keys(n.sessions).length) return n;
    n.phase = 'stopping';
  }
  return n;
}
export function validateScan(input, allowedRepos, allowedHosts) {
  const kind = input.kind;
  if (!['code','web','api'].includes(kind)) throw new Error('请选择代码、Web 或 API 扫描');
  let url;
  try { url = new URL(input.target); } catch { throw new Error('请输入完整的 HTTPS URL'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.hash || url.search) throw new Error('目标必须是无凭据和查询参数的 HTTPS URL');
  if (kind === 'code') {
    const repo = url.pathname.replace(/\.git$/, '').replace(/\/$/, '');
    if (url.hostname !== 'github.com' || url.port || !/^\/[\w.-]+\/[\w.-]+$/.test(repo) || !allowedRepos.includes(repo.slice(1).toLowerCase())) throw new Error('代码仓库不在管理员配置的授权列表中');
    url = new URL(`https://github.com${repo}`);
  } else if (!allowedHosts.includes(url.host.toLowerCase())) throw new Error('测试域名不在管理员配置的授权列表中');
  if (!['quick','standard','deep'].includes(input.mode)) throw new Error('无效扫描深度');
  if (input.authorized !== true) throw new Error('请确认你有权测试此目标');
  const instructions = String(input.instructions || '').trim();
  if (instructions.length > 4000) throw new Error('测试说明最多 4000 字符');
  return {kind, target:url.href.replace(/\/$/,''),mode:input.mode,instructions};
}
