# 🚀 GitHub Actions Deployment Guide

## Automated Deployment with GitHub Actions

ระบบจะ deploy อัตโนมัติทุกครั้งที่ push code ไป `main` branch

---

## ตัวเลือก Deployment

### **Option 1: Heroku (Recommended)**

#### Setup:

1. **สร้าง Heroku Account**
   - https://www.heroku.com

2. **สร้าง Heroku App**
   ```bash
   heroku login
   heroku create your-app-name
   heroku stack:set container
   ```

3. **เพิ่ม Secrets ใน GitHub**
   - ไป: `Repository Settings` → `Secrets and variables` → `Actions`
   - เพิ่ม 2 secrets:
     - `HEROKU_API_KEY`: (จาก Heroku Account Settings)
     - `HEROKU_APP_NAME`: your-app-name

4. **Push to GitHub**
   ```bash
   git push origin main
   ```

5. **ดู Deploy Progress**
   - ไปที่: `Actions` tab ใน GitHub
   - รอ deploy เสร็จ (~5 นาที)
   - ได้ live URL: `https://your-app-name.herokuapp.com`

---

### **Option 2: AWS (Advanced)**

1. ตั้ง AWS CLI
2. เพิ่ม AWS credentials ใน GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
3. Modify `.github/workflows/deploy.yml` สำหรับ AWS ECS/Lambda

---

### **Option 3: Docker Hub (Manual Deploy)**

1. ตั้ง Docker Hub account
2. เพิ่ม secrets:
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`
3. Image จะ push ไป Docker Hub อัตโนมัติ

---

## Workflows ที่ Available

| Workflow | เมื่อไร | ทำอะไร |
|----------|--------|--------|
| **test.yml** | ทุกครั้ง push | ทดสอบ Python syntax |
| **build.yml** | ทุกครั้ง push | Build Docker image |
| **deploy.yml** | Push to `main` | Deploy ไป Production |

---

## Real-time Status

ดูสถานะ workflow:
- ไป: GitHub Repository
- Click: `Actions` tab
- ดู: Latest runs สถานะ

---

## Environment Variables สำหรับ Production

ตั้งใน Heroku Dashboard:

```
MONGODB_URL=your_production_mongo_db_url
JWT_SECRET=your_secret_key_production
ADMIN_EMAIL=admin@ecommerce.local
ENVIRONMENT=production
```

---

## Deploy Log & Troubleshooting

### ดู Deploy Logs:
1. GitHub → `Actions` tab
2. Click latest workflow run
3. ดู `Deploy to Production` step

### Common Issues:

**❌ Deployment failed: "Heroku credentials invalid"**
- ตรวจสอบ `HEROKU_API_KEY` ใน GitHub Secrets
- แน่ใจว่า token ยังใช้ได้ (30 days expiry)

**❌ Build timeout (>30 min)**
- ลดขนาด dependencies
- Optimize Dockerfile

**❌ App crashes after deploy**
- ดู Heroku logs: `heroku logs --tail`
- ตรวจสอบ environment variables
- เช็ค database connection

---

## ส่งให้ผู้อื่นใช้

ใช้ live URL ที่ได้จาก deployment:

```
https://your-app-name.herokuapp.com
```

---

## Manual Deploy (In Case)

ถ้า GitHub Actions fail, deploy ด้วยมือได้:

```bash
# Heroku
heroku login
git push heroku main
heroku logs --tail

# หรือ Docker
docker build -t ecommerce:latest .
docker run -p 8000:8000 ecommerce:latest
```

---

## Automatic Redeploy

ทุกครั้งที่ push ไป `main`:

```bash
git add .
git commit -m "Fix: update code"
git push origin main
# GitHub Actions จะ auto deploy!
```

Deploy จะเสร็จในประมาณ **5-10 นาที** ✅

---

## Support

หาข้อมูลเพิ่มเติม:
- 📖 [GitHub Actions Docs](https://docs.github.com/en/actions)
- 📖 [Heroku Docs](https://devcenter.heroku.com)
- 💬 ตรวจสอบ Workflow Logs สำหรับ error messages
