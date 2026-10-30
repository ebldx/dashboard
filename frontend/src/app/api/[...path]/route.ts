import type { NextRequest } from "next/server";

const MAX_PROXY_BODY_BYTES = 12 * 1024 * 1024;
const RESPONSE_HEADERS = ["content-type", "content-disposition", "cache-control"];
const BODYLESS_METHODS = new Set(["GET", "HEAD"]);

async function proxy(
  request: NextRequest,
  context: RouteContext<"/api/[...path]">,
): Promise<Response> {
  const { path } = await context.params;
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_PROXY_BODY_BYTES) {
    return Response.json({ detail: "Request body is too large." }, { status: 413 });
  }
  const allowedRoots = new Set([
    "system",
    "profile",
    "goals",
    "principles",
    "resume",
    "projects",
    "tasks",
    "calendar",
    "ai",
    "preferences",
  ]);
  if (
    !path.length ||
    !allowedRoots.has(path[0]) ||
    path.some((segment) => !/^[A-Za-z0-9_-]+$/.test(segment))
  ) {
    return Response.json({ detail: "API route not found." }, { status: 404 });
  }

  const backendBase = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  const target = new URL(
    `api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
    `${backendBase.replace(/\/+$/, "")}/`,
  );
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  let body: ArrayBuffer | undefined;
  if (!BODYLESS_METHODS.has(request.method)) {
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_PROXY_BODY_BYTES) {
      return Response.json({ detail: "Request body is too large." }, { status: 413 });
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(
      { detail: "The application API is currently unavailable." },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
