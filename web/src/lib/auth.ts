import { SignJWT, jwtVerify } from 'jose'

const secret = () => new TextEncoder().encode(process.env.JWT_SECRET!)

export async function createToken() {
  return new SignJWT({ role: 'admin' })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('30d')
    .sign(secret())
}

export async function verifyToken(token: string) {
  return jwtVerify(token, secret())
}
