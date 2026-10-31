import { createHmac,timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
const COOKIE="ciccio_session";
function secret(){const s=process.env.CICCIO_SESSION_SECRET;if(!s||s.length<32)throw new Error("CICCIO_SESSION_SECRET deve contenere almeno 32 caratteri.");return s;}
function signature(payload:string){return createHmac("sha256",secret()).update(payload).digest("hex");}
export function validPassword(value:string){const expected=process.env.CICCIO_APP_PASSWORD||"";if(!expected||!value)return false;const a=Buffer.from(value),b=Buffer.from(expected);return a.length===b.length&&timingSafeEqual(a,b);}
export function makeSession(){const payload=String(Date.now()+1000*60*60*24*30);return payload+"."+signature(payload);}
export function verifySession(value:string){const [payload,sig]=value.split(".");if(!payload||!sig||Number(payload)<Date.now())return false;const expected=signature(payload);const a=Buffer.from(sig),b=Buffer.from(expected);return a.length===b.length&&timingSafeEqual(a,b);}
export async function isAuthenticated(){const store=await cookies();const token=store.get(COOKIE)?.value||"";try{return verifySession(token);}catch{return false;}}
export const sessionCookieName=COOKIE;
