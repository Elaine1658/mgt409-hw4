import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useMatch, useNavigate, useParams } from 'react-router-dom'
import { api, clearSession, getToken, saveSession, type AuthResult, type ChatLine, type Product, type User } from './api'

function Header({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <>
      <div className="announcement">Campus essentials for every chapter of your Yale story</div>
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Campus Customs home">
          <span className="brand-mark">CC</span>
          <span className="brand-copy"><strong>Campus Customs</strong><small>YALE-INSPIRED GOODS</small></span>
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/products">Products</NavLink>
          <NavLink to="/about">About Us</NavLink>
        </nav>
        <div className="account-nav">
          {user ? <>
            <span className="welcome-name">Hello, {user.first_name}</span>
            <button className="text-button" onClick={onLogout}>Log out</button>
          </> : <>
            <NavLink to="/login">Log in</NavLink>
            <Link className="account-cta" to="/create-account">Create account</Link>
          </>}
        </div>
      </header>
    </>
  )
}

function ProductCardView({ product, compact = false }: { product: Product; compact?: boolean }) {
  const availability = product.total_stock > 0 ? `${product.total_stock} in stock` : 'Currently sold out'
  return (
    <Link className={`product-card${compact ? ' product-card-compact' : ''}`} to={`/products/${product.product_id}`}>
      <div className="product-image-wrap">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className={`stock-pill${product.total_stock === 0 ? ' sold-out' : ''}`}>{availability}</span>
      </div>
      <div className="product-card-copy">
        <p className="eyebrow">{product.garment_type}</p>
        <h3>{product.name}</h3>
        {!compact && <p className="product-description">{product.description}</p>}
        <div className="product-card-footer"><strong>${product.price.toFixed(2)}</strong><span>View item ↗</span></div>
      </div>
    </Link>
  )
}

function HomePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    api<Product[]>('/api/products?limit=8').then(setProducts).catch((e: Error) => setError(e.message))
  }, [])
  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow hero-kicker">MADE FOR CAMPUS DAYS</p>
          <h1>Carry a little<br /><em>campus pride.</em></h1>
          <p className="hero-intro">Easy layers, familiar colors, and Yale-inspired pieces for the places that feel like home.</p>
          <div className="hero-actions"><Link className="button button-dark" to="/products">Shop the collection <span>→</span></Link><Link className="underlined-link" to="/about">Get to know us</Link></div>
          <div className="hero-note"><span className="note-dot" /> Thoughtful campus gear, all in one place</div>
        </div>
        <div className="hero-art" aria-label="Campus Customs featured apparel">
          <div className="hero-art-label"><span>THE CAMPUS EDIT</span><span>01 / 03</span></div>
          <div className="hero-art-shape shape-one" />
          <div className="hero-art-shape shape-two" />
          {products[0] && <img className="hero-product" src={products[0].image_url} alt={products[0].name} />}
          <div className="hero-art-caption"><span>CLASSIC CAMPUS LAYERS</span><span>COLLECTION Nº 01</span></div>
        </div>
      </section>

      <section className="value-strip" aria-label="Store highlights">
        <div><span className="value-icon">✳</span><span><strong>For campus life</strong><small>Everyday pieces, easy to wear</small></span></div>
        <div><span className="value-icon">◇</span><span><strong>Made to explore</strong><small>Browse by style, sport, or college</small></span></div>
        <div><span className="value-icon">↗</span><span><strong>Here to help</strong><small>Ask us about sizes and stock</small></span></div>
      </section>

      <section className="section-shell featured-section">
        <div className="section-heading"><div><p className="eyebrow">A GOOD PLACE TO START</p><h2>Campus favorites</h2></div><Link className="underlined-link" to="/products">Shop all products →</Link></div>
        {error ? <p className="notice">The catalogue is not available yet. Start the FastAPI backend and place the course data pack in <code>data/</code>.</p> : products.length ? <div className="product-grid">{products.slice(0, 4).map(item => <ProductCardView key={item.product_id} product={item} />)}</div> : <div className="loading-note">Loading the collection…</div>}
      </section>
      <section className="story-band"><p className="eyebrow">FROM THE QUAD TO THE WEEKEND</p><h2>Find your next<br /><em>favorite layer.</em></h2><Link className="button button-light" to="/products">Explore products <span>→</span></Link></section>
    </main>
  )
}

function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All pieces')
  const [sortBy, setSortBy] = useState('featured')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    const timer = window.setTimeout(() => {
      setLoading(true)
      const url = `/api/products?limit=120${query.trim() ? `&search=${encodeURIComponent(query.trim())}` : ''}`
      api<Product[]>(url).then(items => { if (live) { setProducts(items); setError('') } }).catch((e: Error) => { if (live) setError(e.message) }).finally(() => { if (live) setLoading(false) })
    }, 160)
    return () => { live = false; window.clearTimeout(timer) }
  }, [query])

  const filtered = products.filter(product => {
    if (category === 'All pieces') return true
    const value = `${product.name} ${product.garment_type}`.toLowerCase()
    if (category === 'Hoodies') return value.includes('hoodie')
    if (category === 'Sweatshirts') return value.includes('crewneck') || value.includes('sweatshirt') || value.includes('sweater')
    return value.includes('t-shirt') || value.includes('shirt') || value.includes('tee')
  }).sort((a, b) => sortBy === 'price-low' ? a.price - b.price : sortBy === 'price-high' ? b.price - a.price : a.name.localeCompare(b.name))

  return (
    <main className="section-shell catalog-page">
      <div className="page-intro"><p className="eyebrow">THE CAMPUS CUSTOMS COLLECTION</p><h1>Find your <em>favorite.</em></h1><p>Browse the pieces that make campus feel a little more like yours.</p></div>
      <div className="catalog-tools">
        <label className="search-field"><span aria-hidden="true">⌕</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search hoodies, colleges, sports…" aria-label="Search products" /><kbd>⌘ K</kbd></label>
        <label className="sort-field">Sort by <select value={sortBy} onChange={event => setSortBy(event.target.value)}><option value="featured">Featured</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></label>
      </div>
      <div className="catalog-layout">
        <aside className="category-rail"><p className="eyebrow">SHOP BY STYLE</p>{['All pieces', 'Hoodies', 'Sweatshirts', 'T-shirts'].map(item => <button key={item} className={category === item ? 'category-active' : ''} onClick={() => setCategory(item)}>{item}<span>→</span></button>)}<div className="catalog-help"><strong>Need a hand?</strong><span>Ask the shop assistant about an item or a size.</span></div></aside>
        <div className="catalog-results"><div className="results-heading"><span>{loading ? 'Updating collection…' : `${filtered.length} ${filtered.length === 1 ? 'piece' : 'pieces'}`}</span><span>Campus Customs, Yale</span></div>
          {error ? <p className="notice">{error}. Please start the backend and check that the course data is available in <code>data/</code>.</p> : loading ? <div className="loading-note">Loading the collection…</div> : filtered.length ? <div className="product-grid">{filtered.map(product => <ProductCardView key={product.product_id} product={product} />)}</div> : <div className="empty-state"><span>✳</span><h2>No pieces found</h2><p>Try another search or choose a different style.</p><button className="button button-outline" onClick={() => { setQuery(''); setCategory('All pieces') }}>Reset filters</button></div>}
        </div>
      </div>
    </main>
  )
}

function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setProduct(null)
    api<Product>(`/api/products/${encodeURIComponent(productId)}`).then(setProduct).catch((e: Error) => setError(e.message))
  }, [productId])
  if (error) return <main className="section-shell empty-state"><h1>We could not find this item.</h1><p>{error}</p><Link className="button button-dark" to="/products">Back to products</Link></main>
  if (!product) return <main className="section-shell loading-note">Loading product…</main>
  return (
    <main className="section-shell detail-page">
      <div className="breadcrumbs"><Link to="/">Home</Link><span>/</span><Link to="/products">Products</Link><span>/</span><span>{product.name}</span></div>
      <div className="product-detail-grid">
        <div className="detail-image"><img src={product.image_url} alt={product.name} /></div>
        <section className="detail-copy"><p className="eyebrow">{product.garment_type}</p><h1>{product.name}</h1><p className="detail-price">${product.price.toFixed(2)}</p><p className="detail-description">{product.description}</p><div className="detail-rule" />
          <div className="detail-meta"><strong>Colors</strong><span>{product.colors.length ? product.colors.join(', ') : 'See product image'}</span></div>
          <div className="sizes-heading"><strong>Availability by size</strong><span>{product.total_stock} total in stock</span></div>
          <div className="size-grid">{product.inventory.length ? product.inventory.map(level => <div className={`size-cell${level.quantity === 0 ? ' size-out' : ''}`} key={level.size}><span>{level.size}</span><strong>{level.quantity > 0 ? `${level.quantity} available` : 'Out of stock'}</strong></div>) : <p>Size-level stock is not listed.</p>}</div>
          <p className="detail-help">Have a question about fit or stock? The Campus Customs assistant is ready to help.</p><button className="button button-dark detail-chat-button" onClick={() => window.dispatchEvent(new Event('open-campus-chat'))}>Ask about this item <span>↗</span></button>
        </section>
      </div>
      <section className="detail-note"><span>✳</span><p>Product and inventory information on this page comes from the current Campus Customs catalogue.</p></section>
    </main>
  )
}

function AboutPage() {
  return <main className="about-page"><section className="about-hero"><p className="eyebrow">A LITTLE CAMPUS, WHEREVER YOU GO</p><h1>Goods for the<br /><em>good old days.</em></h1><p>Campus Customs brings together the colors, places, and traditions that make campus feel personal. Find an easy layer for class, a game day favorite, or a gift that feels close to home.</p><Link className="button button-dark" to="/products">Browse the collection <span>→</span></Link></section><section className="about-details"><div><p className="eyebrow">OUR APPROACH</p><h2>Familiar details.<br />Fresh everyday style.</h2></div><p>We make it simple to explore campus-inspired apparel by style, college, or sport. Every product page shows the details we have, and our shop assistant can check prices and size-level stock from the catalogue.</p></section><section className="visit-card"><div><p className="eyebrow">COME VISIT</p><h2>New Haven, Connecticut</h2><p>57 Broadway<br />New Haven, CT 06511</p></div><span className="visit-mark">CC</span></section></main>
}

function AuthPage({ mode, onAuthenticated }: { mode: 'login' | 'register'; onAuthenticated: (result: AuthResult) => void }) {
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const isRegister = mode === 'register'
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (isRegister && password !== confirm) { setError('Your passwords do not match.'); return }
    setBusy(true)
    try {
      const result = await api<AuthResult>(`/api/auth/${isRegister ? 'register' : 'login'}`, {
        method: 'POST',
        body: JSON.stringify(isRegister ? { first_name: firstName, last_name: lastName, email, password } : { email, password }),
      })
      onAuthenticated(result)
      navigate('/products')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <main className="auth-page"><div className="auth-card"><p className="eyebrow">YOUR CAMPUS CUSTOMS ACCOUNT</p><h1>{isRegister ? 'Make yourself at home.' : 'Welcome back.'}</h1><p className="auth-intro">{isRegister ? 'Create an account to keep your shop conversations in one place.' : 'Log in to continue your Campus Customs visit.'}</p><form onSubmit={submit} className="auth-form">
    {isRegister && <div className="name-fields"><label>First name<input autoComplete="given-name" required value={firstName} onChange={e => setFirstName(e.target.value)} /></label><label>Last name<input autoComplete="family-name" required value={lastName} onChange={e => setLastName(e.target.value)} /></label></div>}
    <label>Email address<input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label>Password<input type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} required minLength={isRegister ? 8 : 1} value={password} onChange={e => setPassword(e.target.value)} /></label>
    {isRegister && <label>Confirm password<input type="password" autoComplete="new-password" required minLength={8} value={confirm} onChange={e => setConfirm(e.target.value)} /></label>}
    {error && <p className="form-error" role="alert">{error}</p>}<button className="button button-dark auth-submit" disabled={busy}>{busy ? 'One moment…' : isRegister ? 'Create my account' : 'Log in'} <span>→</span></button>
  </form><p className="auth-switch">{isRegister ? 'Already have an account?' : 'New to Campus Customs?'} <Link to={isRegister ? '/login' : '/create-account'}>{isRegister ? 'Log in' : 'Create an account'}</Link></p></div></main>
}

function ChatWidget({ user }: { user: User | null }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatLine[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const loadedFor = useRef<string | null>(null)
  const productMatch = useMatch('/products/:productId')
  const currentProductId = productMatch?.params.productId
  const location = useLocation()

  useEffect(() => {
    const openChat = () => setOpen(true)
    window.addEventListener('open-campus-chat', openChat)
    return () => window.removeEventListener('open-campus-chat', openChat)
  }, [])

  useEffect(() => {
    const identity = user ? String(user.id) : 'guest'
    if (!open || loadedFor.current === identity) return
    loadedFor.current = identity
    setMessages([])
    api<ChatLine[]>('/api/chat/history').then(history => {
      setMessages(history.length ? history : [{ role: 'assistant', content: 'Hi! I can help you find a product or check its price and size-level stock. What are you looking for?' }])
    }).catch(() => setMessages([{ role: 'assistant', content: 'Hi! Ask me about a product, price, or size availability.' }]))
  }, [open, user])

  async function send(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = draft.trim()
    if (!message || busy) return
    setError('')
    setDraft('')
    setMessages(current => [...current, { role: 'user', content: message }])
    setBusy(true)
    try {
      const response = await api<{ reply: string; products: Product[] }>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message, product_id: currentProductId || null, page_route: location.pathname }),
      })
      setMessages(current => [...current, { role: 'assistant', content: response.reply, products: response.products }])
    } catch (e) {
      const messageText = (e as Error).message
      setError(messageText)
      setMessages(current => [...current, { role: 'assistant', content: 'I could not reach the shop assistant. Please try again in a moment.' }])
    } finally { setBusy(false) }
  }

  return <>
    {open && <section className="chat-panel" aria-label="Campus Customs chat">
      <header className="chat-header"><div className="chat-avatar">CC</div><div><strong>Campus Customs</strong><span><i /> Shop assistant {user ? `· chatting with ${user.first_name}` : '· guest chat'}</span></div><button aria-label="Close chat" onClick={() => setOpen(false)}>×</button></header>
      <div className="chat-privacy">{user ? 'Your conversation is saved to your account.' : 'Guest conversations are not saved.'}</div>
      <div className="chat-messages" aria-live="polite">{messages.map((message, index) => <div key={message.id ?? `message-${index}`} className={`chat-row ${message.role}`}><div className="chat-bubble">{message.content}{message.products?.length ? <div className="chat-product-list">{message.products.slice(0, 4).map(product => <ProductCardView key={product.product_id} product={product} compact />)}</div> : null}</div></div>)}{busy && <div className="chat-row assistant"><div className="chat-bubble typing-indicator">Checking the catalogue…</div></div>}</div>
      {error && <p className="chat-error" role="alert">{error}</p>}
      <form className="chat-compose" onSubmit={send}><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Ask about a product or size…" aria-label="Your message" maxLength={1500} /><button aria-label="Send message" disabled={busy || !draft.trim()}>↑</button></form>
      <p className="chat-footnote">Product facts come from the Campus Customs catalogue.</p>
    </section>}
    <button className={`chat-launcher${open ? ' chat-launcher-open' : ''}`} aria-label={open ? 'Close Campus Customs chat' : 'Open Campus Customs chat'} onClick={() => setOpen(value => !value)}>{open ? '×' : <><span className="chat-launcher-dot" /> Ask the shop</>}</button>
  </>
}

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    try { return JSON.parse(localStorage.getItem('campus-customs-user') || 'null') as User | null } catch { return null }
  })
  const location = useLocation()
  useEffect(() => {
    if (!getToken()) return
    api<User>('/api/auth/me').then(setUser).catch(() => { clearSession(); setUser(null) })
  }, [])
  function authenticated(result: AuthResult) { saveSession(result); setUser(result.user) }
  function logout() { clearSession(); setUser(null); window.location.assign('/') }
  return <div className="app-shell"><Header user={user} onLogout={logout} /><Routes location={location}>
    <Route path="/" element={<HomePage />} />
    <Route path="/products" element={<ProductsPage />} />
    <Route path="/products/:productId" element={<ProductPage />} />
    <Route path="/about" element={<AboutPage />} />
    <Route path="/login" element={<AuthPage key="login" mode="login" onAuthenticated={authenticated} />} />
    <Route path="/create-account" element={<AuthPage key="register" mode="register" onAuthenticated={authenticated} />} />
    <Route path="*" element={<main className="section-shell empty-state"><h1>Page not found</h1><Link className="button button-dark" to="/">Back home</Link></main>} />
  </Routes><footer className="site-footer"><Link className="footer-brand" to="/">Campus Customs</Link><span>Thoughtful pieces for campus life.</span><Link to="/products">Browse the collection</Link><span>© 2026 Campus Customs</span></footer><ChatWidget user={user} /></div>
}
