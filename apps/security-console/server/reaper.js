import {reconcile} from './gpu.js';
import {mutate} from './store.js';
export async function handler() {
  try { await reconcile(); }
  catch(e) { console.error(e.name,e.message); await mutate(s=>({...s,lastError:`${e.name}: ${e.message}`})); throw e; }
}
