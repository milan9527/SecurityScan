export async function initialize(){const r=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});if(r.status===401)return false;if(!r.ok)throw new Error('登录服务暂时不可用');return true;}
export async function login(username,password){return api('/auth/login',{username,password});}
export async function logout(){return api('/auth/logout',{});}
export async function api(path,body){
 const r=await fetch(`/api${path}`,{credentials:'same-origin',cache:'no-store',method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
 if(r.status===401&&path!=='/auth/login')window.dispatchEvent(new Event('session-expired'));
 const data=await r.json();if(!r.ok)throw new Error(data.error||'请求失败');return data;
}
