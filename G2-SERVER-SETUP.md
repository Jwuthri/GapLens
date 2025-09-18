# 🖥️ G2 Scraping Server Setup Guide

This guide explains how to deploy GapLens with **G2-compatible browser automation** on headless servers using **virtual displays**.

## 🎯 Overview

G2.com has extremely aggressive anti-bot detection that blocks headless browsers. To bypass this, we use:

1. **Visible browsers** (headless=False) - G2 can't detect this
2. **Virtual displays (Xvfb)** - Allows "visible" browsers on headless servers
3. **Botasaurus stealth features** - Advanced anti-detection

## 🚀 Quick Start

### Local Development
```bash
# No configuration needed - uses real display
docker-compose up
```

### Server/Cloud Deployment
```bash
# Uses virtual display automatically
docker-compose -f docker-compose.full-prod.yml up
```

## 🐳 Docker Configuration

### Development (docker-compose.yml)
- ✅ Virtual display support included
- ✅ SERVER_MODE=true for backend & celery-worker
- ✅ Chrome/Chromium installed
- ✅ Xvfb virtual display

### Production (docker-compose.full-prod.yml)
- ✅ All development features
- ✅ Production-optimized Dockerfile.prod
- ✅ Nginx reverse proxy
- ✅ Health checks & monitoring

### Kubernetes (k8s-deployment.yaml)
- ✅ SERVER_MODE environment variables
- ✅ Resource limits for browser automation
- ✅ Multi-replica celery workers

## 🛠️ Manual Server Setup

If you need to set up a server manually:

### Ubuntu/Debian
```bash
# Install virtual display
sudo apt-get update
sudo apt-get install -y xvfb x11-utils x11-xserver-utils

# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Set environment and run
export SERVER_MODE=true
export DISPLAY=:99
python your_scraper.py
```

### CentOS/RHEL
```bash
# Install virtual display
sudo yum install -y xorg-x11-server-Xvfb x11-utils

# Install Chrome
sudo yum install -y wget
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
sudo yum localinstall -y google-chrome-stable_current_x86_64.rpm

# Set environment and run
export SERVER_MODE=true
export DISPLAY=:99
python your_scraper.py
```

## ☁️ Cloud Deployment Examples

### AWS ECS/Fargate
- ✅ Use `docker-compose.full-prod.yml`
- ✅ Set task CPU/Memory: 2vCPU, 4GB RAM minimum
- ✅ Browser automation is resource-intensive

### Google Cloud Run
- ✅ Enable CPU boost for browser startup
- ✅ Set timeout to 900s (15 minutes)
- ✅ Use at least 2GB memory

### Railway/Render
- ✅ Use Dockerfile.prod (includes all dependencies)
- ✅ Environment variables set automatically
- ✅ May need upgraded plans for CPU/memory

## 📊 Resource Requirements

### Minimum (Single Browser)
- **CPU**: 1 vCPU
- **Memory**: 2GB RAM
- **Storage**: 5GB (Chrome + dependencies)

### Recommended (Multiple Workers)
- **CPU**: 2+ vCPU
- **Memory**: 4+ GB RAM
- **Storage**: 10GB

### Production Scale
- **CPU**: 4+ vCPU per celery worker
- **Memory**: 8+ GB RAM
- **Storage**: 20GB

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_MODE` | `false` | Enable virtual display for servers |
| `DISPLAY` | `:99` | X11 display for virtual screen |
| `CHROME_EXECUTABLE` | Auto-detected | Path to Chrome/Chromium binary |
| `FORCE_HEADLESS` | `false` | Force headless mode (not recommended for G2) |

## 🚨 Troubleshooting

### Quick Diagnosis
```bash
# Run the built-in test script
docker-compose exec backend python test-browser-docker.py

# Or for production
docker-compose -f docker-compose.full-prod.yml exec backend python test-browser-docker.py
```

### Manual Browser Tests
```bash
# Check if Chrome is installed
which google-chrome || which chromium

# Check if Xvfb is running
ps aux | grep Xvfb

# Test virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
xdpyinfo -display :99
```

### Check Container Logs
```bash
# View startup logs
docker-compose logs backend
docker-compose logs celery-worker

# Look for these success messages:
# "🖥️ Server Mode: Enabled (Virtual Display + Visible Browser)"
# "✅ Virtual display :99 is ready"
```

### G2 Still Blocking
1. ✅ Verify `SERVER_MODE=true` is set
2. ✅ Check logs for "Server Mode: Enabled"
3. ✅ Ensure `headless=False` in browser config
4. ✅ Consider rotating IP addresses/proxies

### Performance Issues
1. ✅ Increase CPU/Memory resources
2. ✅ Reduce celery worker concurrency
3. ✅ Add delays between requests
4. ✅ Monitor resource usage

## 📈 Monitoring

### Docker Health Checks
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs celery-worker
```

### Kubernetes Monitoring
```bash
# Check pod status
kubectl get pods -n review-gap-analyzer

# View logs
kubectl logs -f deployment/celery-worker -n review-gap-analyzer
```

### Browser Process Monitoring
```bash
# Check Chrome processes
ps aux | grep chrome

# Monitor memory usage
top -p $(pgrep chrome)
```

## 🎯 Success Indicators

When properly configured, you should see:

```
🖥️ Server Mode: Enabled (Virtual Display + Visible Browser)
🤖 Starting FIXED G2 scraping: https://www.g2.com/products/gorgias/reviews
✅ Connected: G2: Gorgias Reviews
📦 Found 10 article elements with final selector
🎯 FINAL G2 RESULTS: 25 unique reviews from 2 pages
```

## 🛡️ Security Notes

- Virtual displays run in isolated containers
- No GUI access needed on production servers  
- Browser sessions are ephemeral and cleaned up
- All HTTP requests use stealth user agents

## 📚 Additional Resources

- [Botasaurus Documentation](https://github.com/omkarcloud/botasaurus)
- [Docker Multi-stage Builds](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Xvfb Virtual Display](https://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml)

## 🤝 Support

If G2 scraping still fails after following this guide:
1. Check the logs for specific error messages
2. Verify all environment variables are set
3. Test with a simple browser automation script
4. Consider implementing proxy rotation for additional stealth

---

**🎉 With this setup, your G2 scraper will work reliably on any server environment!**
