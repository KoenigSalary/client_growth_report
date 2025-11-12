# ☁️ Cloud Deployment Guide - Share Your App

## Deploy to Streamlit Cloud (FREE & Recommended)

Streamlit Cloud is the easiest way to deploy and share your app. Your team can access it from any device (mobile, tablet, desktop) via a shareable link.

---

## 🚀 Quick Deployment (5 Steps)

### Step 1: Create GitHub Repository

1. **Go to GitHub:** https://github.com
2. **Sign in** (or create free account)
3. **Click:** "New Repository" button (green button, top right)
4. **Repository Settings:**
   - Name: `client-growth-report`
   - Privacy: **Private** (recommended for security)
   - ✅ Add README file
5. **Click:** "Create repository"

---

### Step 2: Upload Your Code

#### Option A: GitHub Web Interface (Easiest)

1. **In your repository**, click "Add file" → "Upload files"
2. **Drag and drop** these files from your package:
   ```
   streamlit_app.py
   process_report.py
   requirements.txt
   .streamlit/config.toml
   assets/koenig_logo.png
   ```
3. **Create folder structure:**
   - Upload `streamlit_app.py`, `process_report.py`, `requirements.txt` to root
   - Create `.streamlit` folder, upload `config.toml` inside it
   - Create `assets` folder, upload `koenig_logo.png` inside it
4. **Click:** "Commit changes"

#### Option B: Git Command Line

```bash
# In your local project folder
git init
git add streamlit_app.py process_report.py requirements.txt .streamlit/ assets/
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/client-growth-report.git
git push -u origin main
```

---

### Step 3: Deploy to Streamlit Cloud

1. **Go to:** https://share.streamlit.io/
2. **Sign in** with your GitHub account
3. **Click:** "New app" button
4. **Fill in details:**
   - **Repository:** `YOUR_USERNAME/client-growth-report`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** Choose custom URL (e.g., `koenig-growth-report`)
5. **Click:** "Deploy!"

**Deployment takes 2-3 minutes...**

---

### Step 4: Get Your Shareable Link

After deployment completes, you'll get a URL like:

```
https://koenig-growth-report.streamlit.app
```

**This link can be:**
- ✅ Shared with your team via email/Slack/Teams
- ✅ Accessed from mobile phones (iOS/Android)
- ✅ Accessed from tablets
- ✅ Accessed from any desktop browser
- ✅ Bookmarked for quick access
- ✅ Password-protected with your login page

---

### Step 5: Share with Team

**Send this message to your team:**

> 📊 **Client Growth Report System is now live!**
>
> **Access URL:** https://koenig-growth-report.streamlit.app
>
> **Login Credentials:**
> - Username: `admin`
> - Password: `koenig2024`
>
> **How to use:**
> 1. Open the link on any device (phone/tablet/computer)
> 2. Login with credentials above
> 3. Upload your RCB files
> 4. Click "Generate Report"
> 5. Download the Excel report
>
> **Note:** Works on all devices - mobile, tablet, and desktop!

---

## 📱 Mobile & Desktop Access

### Mobile Phones (iOS/Android):
- ✅ Open link in Safari/Chrome
- ✅ Login with credentials
- ✅ Upload files from phone storage
- ✅ Download reports to phone
- ✅ Responsive design adjusts to screen size

### Tablets (iPad/Android):
- ✅ Full functionality in tablet browser
- ✅ Larger screen for better visibility
- ✅ Same login and upload flow

### Desktop (Windows/Mac/Linux):
- ✅ Best experience with full screen
- ✅ Drag-and-drop file upload
- ✅ Fast report generation

---

## 🔒 Security Best Practices

### 1. Update Login Credentials

**After deployment, change default password:**

1. Edit `streamlit_app.py` on GitHub:
   ```python
   LOGIN_USERNAME = "admin"
   LOGIN_PASSWORD = "your_secure_password_here"  # Change this!
   ```
2. Commit changes
3. Streamlit Cloud will auto-redeploy (30 seconds)

### 2. Use Strong Password

- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Example: `K0en!g2024$Growth`

### 3. Keep Repository Private

- Your GitHub repo should be **Private**
- Only authorized team members get access
- Streamlit Cloud can deploy from private repos

---

## 🛠️ Advanced Configuration

### Custom Domain (Optional)

To use your own domain like `reports.koenig.com`:

1. **Streamlit Cloud Settings** → "Custom domain"
2. Add CNAME record in your DNS:
   ```
   CNAME reports → koenig-growth-report.streamlit.app
   ```
3. Wait for DNS propagation (5-30 minutes)

### Environment Variables (For Sensitive Data)

Instead of hardcoding credentials:

1. **Streamlit Cloud** → Your app → "Settings" → "Secrets"
2. Add secrets in TOML format:
   ```toml
   LOGIN_USERNAME = "admin"
   LOGIN_PASSWORD = "your_secure_password"
   ```
3. Update `streamlit_app.py`:
   ```python
   LOGIN_USERNAME = st.secrets["LOGIN_USERNAME"]
   LOGIN_PASSWORD = st.secrets["LOGIN_PASSWORD"]
   ```

---

## 📊 Monitor Usage

### App Analytics:

Streamlit Cloud provides:
- ✅ Number of visitors
- ✅ Resource usage (CPU, memory)
- ✅ Error logs
- ✅ Deployment history

**Access:** App settings → "Metrics"

---

## 🔄 Update Your App

When you want to change something:

1. **Edit files** on GitHub (or push via Git)
2. **Commit changes**
3. **Streamlit Cloud auto-detects** and redeploys
4. **Wait 30 seconds** for new version to be live

**Your team doesn't need to do anything - link stays the same!**

---

## 💰 Pricing

### Streamlit Cloud Free Tier:
- ✅ 1 private app
- ✅ Unlimited public apps
- ✅ 1 GB memory per app
- ✅ Perfect for your use case!

### Community Cloud (Free):
- Sign up at: https://share.streamlit.io/

**No credit card required!**

---

## 🌐 Alternative: Deploy to Your Own Server

If you prefer hosting on your own infrastructure:

### Requirements:
- Ubuntu/Linux server with public IP
- Nginx for reverse proxy
- SSL certificate (Let's Encrypt)
- Firewall configured

### Quick Setup:

```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip nginx

# Clone your code
git clone https://github.com/YOUR_USERNAME/client-growth-report.git
cd client-growth-report

# Install Python packages
pip3 install -r requirements.txt

# Run with systemd service
sudo nano /etc/systemd/system/streamlit.service
```

**Service file:**
```ini
[Unit]
Description=Streamlit Client Growth Report
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/client-growth-report
ExecStart=/usr/local/bin/streamlit run streamlit_app.py --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl enable streamlit
sudo systemctl start streamlit

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/streamlit
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Add SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

**Access:** `https://your-domain.com`

---

## 🐳 Alternative: Docker Deployment

### Create Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Deploy:

```bash
# Build image
docker build -t client-growth-report .

# Run container
docker run -p 8501:8501 client-growth-report
```

**Access:** `http://your-server-ip:8501`

---

## 🔧 Troubleshooting

### Issue: App won't deploy
**Solution:** Check requirements.txt has correct Python versions
- Use Python 3.11 or 3.12
- Check logs in Streamlit Cloud dashboard

### Issue: Files upload fails
**Solution:** Check file size limits
- Streamlit Cloud: 200 MB per file
- Your RCB files should be under this limit

### Issue: Slow performance
**Solution:** Upgrade Streamlit Cloud tier or optimize code
- Free tier: 1 GB RAM
- Paid tier: Up to 32 GB RAM

### Issue: Can't access from mobile
**Solution:** Check firewall/network settings
- Ensure HTTPS is enabled
- Check mobile network allows access

---

## 📞 Support

### Streamlit Cloud Support:
- Documentation: https://docs.streamlit.io/streamlit-community-cloud
- Community Forum: https://discuss.streamlit.io/
- GitHub Issues: https://github.com/streamlit/streamlit/issues

---

## ✅ Deployment Checklist

Before sharing with team:

- [ ] Code pushed to GitHub repository
- [ ] App deployed to Streamlit Cloud
- [ ] Login credentials updated (not default)
- [ ] Tested on mobile device
- [ ] Tested on desktop browser
- [ ] Logo displays correctly
- [ ] File upload works
- [ ] Report generation successful
- [ ] Download works on all devices
- [ ] Shareable link copied
- [ ] Team notified with credentials

---

## 🎉 You're Done!

Your Client Growth Report system is now:
- ✅ **Live on the internet**
- ✅ **Accessible from anywhere**
- ✅ **Mobile & desktop friendly**
- ✅ **Secure with login**
- ✅ **Ready to share with team**

**Share the link and start generating reports!** 📊

---

*Cloud Deployment Guide v1.0*  
*Last Updated: November 12, 2025*
