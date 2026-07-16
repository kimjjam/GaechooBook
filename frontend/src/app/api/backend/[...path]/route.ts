import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const FORWARDED_HEADERS = [
  "accept",
  "content-type",
  "cookie",
  "x-csrf-token",
  "x-visitor-token",
] as const;

async function forward(
  request: NextRequest,
  { params }: { params: { path: string[] } },
): Promise<Response> {
  const backendBaseUrl = process.env.BACKEND_URL;
  if (!backendBaseUrl) {
    return Response.json(
      { detail: "백엔드 서버 주소가 설정되지 않았습니다." },
      { status: 503 },
    );
  }

  const safePath = params.path.map(encodeURIComponent).join("/");
  const target = new URL(safePath, `${backendBaseUrl.replace(/\/$/, "")}/`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let backendResponse: Response;
  try {
    backendResponse = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });
  } catch (error) {
    console.error("[api/backend] backend request failed", {
      method: request.method,
      path: target.pathname,
      error: error instanceof Error ? error.message : String(error),
    });
    return Response.json(
      { detail: "백엔드 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers(backendResponse.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("connection");

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
export const OPTIONS = forward;
