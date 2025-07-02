# OpenAI API Proxy Configuration Guide

This guide explains how to configure OpenAI API access through proxy servers for regions with access restrictions.

## Configuration Options

### Option 1: HTTP/HTTPS Proxy

Add to your `.env` file:

```bash
# Your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here

# HTTP proxy configuration
OPENAI_PROXY_URL=http://your-proxy-server:8080

# Or HTTPS proxy
OPENAI_PROXY_URL=https://your-proxy-server:8080

# Optional: Custom base URL if using reverse proxy
# OPENAI_BASE_URL=https://api.openai.com/v1
```

### Option 2: Reverse Proxy

If you have a reverse proxy server:

```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://your-reverse-proxy.com/v1
```

### Option 3: Both Proxy and Custom Base URL

```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://your-reverse-proxy.com/v1
OPENAI_PROXY_URL=http://your-proxy-server:8080
```

## How It Works

The AI service will automatically:

1. Use the proxy URL if `OPENAI_PROXY_URL` is set
2. Use the custom base URL if `OPENAI_BASE_URL` is set  
3. Fall back to default OpenAI endpoint if neither is set

## Testing Configuration

To test if your configuration works:

```bash
cd backend
python3 -c "
import asyncio
from app.infrastructure.external_services.ai_service import AIService

async def test():
    ai_service = AIService()
    try:
        result = await ai_service.generate_lyrics('Test song about love', 'pop')
        print('✅ OpenAI API working!')
        print(f'Generated: {result[:100]}...')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

## Common Proxy Services

Some popular proxy services that work with OpenAI:

- **Cloudflare Workers**: Create a reverse proxy
- **Nginx**: Set up as reverse proxy
- **Private VPN services**: HTTP/HTTPS proxy
- **Corporate proxies**: If available in your network

## Security Notes

- Never commit your actual API keys to version control
- Use environment variables for all sensitive configuration
- Ensure proxy servers are trusted and secure
- Consider using HTTPS proxies for additional security

## Troubleshooting

1. **Connection timeout**: Increase timeout in AI service
2. **SSL errors**: Set `verify=False` for testing (not recommended for production)
3. **Proxy authentication**: Add credentials to proxy URL: `http://user:pass@proxy:8080`
4. **Firewall issues**: Ensure outbound connections are allowed on proxy ports 

# OpenAI API Proxy Setup for Russia

This guide helps you configure OpenAI API access from Russia using various proxy methods.

## 🚀 Quick Setup (Fastest Options)

### Option 1: Fast HTTP Proxy
```bash
# Add to your .env file
OPENAI_PROXY_URL=http://user:pass@fast-proxy.example.com:8080
```

### Option 2: Private VPN/Proxy Service  
```bash
# Premium proxy services (usually faster)
OPENAI_PROXY_URL=https://username:password@premium-proxy.com:443
```

### Option 3: Reverse Proxy (Fastest)
```bash
# Use a reverse proxy service that tunnels OpenAI API
OPENAI_BASE_URL=https://your-reverse-proxy.com/v1
# Leave OPENAI_PROXY_URL empty when using reverse proxy
```

## ⚡ Performance Troubleshooting

### Current Issues
- Your proxy `196.17.170.185:8000` is taking 3+ minutes (should be 5-30 seconds)
- This indicates overloaded or poorly routed proxy

### Solutions

1. **Try Different Proxy Servers**:
```bash
# Test multiple proxies to find fastest
OPENAI_PROXY_URL=http://proxy1.example.com:8080
OPENAI_PROXY_URL=http://proxy2.example.com:3128
OPENAI_PROXY_URL=https://premium-service.com:443
```

2. **Use SOCKS5 Proxy** (often faster):
```bash
# If your proxy supports SOCKS5
OPENAI_PROXY_URL=socks5://user:pass@proxy.example.com:1080
```

3. **Reverse Proxy Services** (recommended):
   - Deploy your own OpenAI proxy on Vercel/Netlify
   - Use commercial reverse proxy services
   - Much faster than traditional proxies

## 🛠 Configuration Examples

### Method 1: HTTP/HTTPS Proxy
```bash
# .env file
OPENAI_API_KEY=your_openai_key_here
OPENAI_PROXY_URL=https://username:password@proxy-server.com:8080
```

### Method 2: Reverse Proxy Only
```bash
# .env file  
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://your-reverse-proxy.herokuapp.com/v1
# No OPENAI_PROXY_URL needed
```

### Method 3: Combined (Proxy + Custom Base URL)
```bash
# .env file
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://api.openai-proxy.com/v1
OPENAI_PROXY_URL=https://backup-proxy.com:443
```

## 🧪 Testing Configuration

Run the test script to check performance:
```bash
python3 test_openai_proxy.py
```

**Expected results:**
- ✅ Connection successful in 5-30 seconds
- ❌ Timeout after 3+ minutes = slow proxy

## 📊 Proxy Performance Comparison

| Method | Speed | Reliability | Setup Difficulty |
|--------|-------|-------------|------------------|
| Reverse Proxy | 🟢 Fast (5-15s) | 🟢 High | 🟡 Medium |
| Premium HTTP Proxy | 🟡 Medium (15-45s) | 🟢 High | 🟢 Easy |
| Free HTTP Proxy | 🔴 Slow (1-3min) | 🔴 Low | 🟢 Easy |
| SOCKS5 Proxy | 🟡 Medium (10-30s) | 🟡 Medium | 🟡 Medium |

## 🔧 Creating Your Own Reverse Proxy

### Deploy on Vercel (Free)
1. Create a Vercel account
2. Deploy this simple proxy:

```javascript
// api/openai/[...path].js
export default async function handler(req, res) {
  const { path } = req.query;
  const url = `https://api.openai.com/v1/${path.join('/')}`;
  
  const response = await fetch(url, {
    method: req.method,
    headers: {
      ...req.headers,
      host: 'api.openai.com'
    },
    body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined
  });
  
  const data = await response.json();
  res.status(response.status).json(data);
}
```

3. Use: `OPENAI_BASE_URL=https://your-app.vercel.app/api/openai`

## 🚨 Immediate Solutions

If your current proxy is too slow:

1. **Switch proxy immediately**:
```bash
# Try a different proxy service
export OPENAI_PROXY_URL="https://new-proxy.com:443"
```

2. **Use direct connection temporarily** (if possible):
```bash
# Remove proxy temporarily  
unset OPENAI_PROXY_URL
```

3. **Increase timeout for slow proxy**:
```bash
# Already configured for 3 minutes in your setup
# Consider switching proxy instead of waiting longer
```

## 📞 Support

Common issues:
- **Timeout errors**: Proxy too slow, try different one
- **Connection refused**: Wrong proxy credentials/URL
- **SSL errors**: Try `http://` instead of `https://`
- **Authentication failed**: Check username/password in proxy URL 