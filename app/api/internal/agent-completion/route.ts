import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";

export const runtime = "nodejs";

function authorized(req: NextRequest) {
  const expected = process.env.SUPABASE_SERVICE_ROLE_KEY || "";
  const supplied = (req.headers.get("authorization") || "").replace(/^Bearer\\s+/i, "");
  if (!expected || !supplied) return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(supplied);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "Non autorizzato." }, { status: 401 });
  }

  const apiKey = process.env.OPENROUTER_API_KEY || "";
  if (!apiKey) {
    return NextResponse.json({ error: "Provider di riserva non configurato." }, { status: 503 });
  }

  try {
    const raw = await req.text();
    if (raw.length > 40000) {
      return NextResponse.json({ error: "Richiesta troppo grande." }, { status: 413 });
    }
    const body = JSON.parse(raw);
    if (!Array.isArray(body.messages) || body.messages.length < 1 || body.messages.length > 12) {
      return NextResponse.json({ error: "Formato dei messaggi non valido." }, { status: 400 });
    }
    const messages = body.messages.map((message: { role?: string; content?: unknown }) => {
      const role = String(message?.role || "");
      const content = typeof message?.content === "string" ? message.content : "";
      if (!["system", "user", "assistant"].includes(role) || content.length > 20000) {
        throw new Error("Messaggio non valido.");
      }
      return { role, content };
    });
    const maxTokens = Math.min(3000, Math.max(100, Number(body.max_completion_tokens) || 1800));
    const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + apiKey,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ciccio-ai.vercel.app",
        "X-Title": "Ciccio AI"
      },
      body: JSON.stringify({
        model: "openrouter/free",
        messages,
        temperature: Math.min(1, Math.max(0, Number(body.temperature) || 0.2)),
        max_tokens: maxTokens,
        stream: false
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(90000)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json(
        { error: "Il provider di riserva non è disponibile (HTTP " + response.status + ")." },
        { status: 502 }
      );
    }
    if (!Array.isArray(data.choices) || !data.choices[0]?.message) {
      return NextResponse.json({ error: "Il provider non ha restituito una risposta valida." }, { status: 502 });
    }
    return NextResponse.json({ choices: data.choices }, {
      headers: { "Cache-Control": "no-store" }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Errore del provider di riserva.";
    return NextResponse.json({ error: message.slice(0, 240) }, { status: 502 });
  }
}
