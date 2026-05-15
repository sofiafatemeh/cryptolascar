import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { jwtVerify } from 'jose'

const PUBLIC = ['/login', '/api/auth/login', '/api/ingest']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (PUBLIC.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const token = request.cookies.get('session')?.value
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET!)
    await jwtVerify(token, secret)
    return NextResponse.next()
  } catch {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
