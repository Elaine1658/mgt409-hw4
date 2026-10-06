export interface StockLevel {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  inventory: StockLevel[]
  total_stock: number
}

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface ChatLine {
  id?: number
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
  created_at?: string
}

export interface AuthResult {
  token: string
  user: User
}

const TOKEN_KEY = 'campus-customs-session'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function saveSession(result: AuthResult): void {
  localStorage.setItem(TOKEN_KEY, result.token)
  localStorage.setItem('campus-customs-user', JSON.stringify(result.user))
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem('campus-customs-user')
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json() as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // The API sometimes returns an empty error response while it is starting.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}
