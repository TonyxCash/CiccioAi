import { NextRequest,NextResponse } from "next/server";
import { makeSession,sessionCookieName,validPassword } from "@/lib/session";
export const runtime="nodejs";
export async function POST(req:NextRequest){try{const body=await req.json();if(!validPassword(String(body.password||"")))return NextResponse.json({error:"Credenziali non valide."},{status:401});const res=NextResponse.json({ok:true});res.cookies.set(sessionCookieName,makeSession(),{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:60*60*24*30});return res;}catch(e){return NextResponse.json({error:e instanceof Error?e.message:"Errore di accesso."},{status:500});}}
export async function DELETE(){const res=NextResponse.json({ok:true});res.cookies.set(sessionCookieName,"",{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:0});return res;}
