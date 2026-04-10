# 部署说明

## 1. 安装依赖
```bash
pip install -r requirements.txt
```

## 2. 启动服务（服务器模式）
```bash
bash ./run_server.sh
```

或
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. 可选 Nginx 反向代理
示例配置：

```nginx
server {
    listen 80;
    server_name your.domain;

    client_max_body_size 1000m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 4. 环境变量
- `APP_HOST`
- `APP_PORT`
- `APP_RELOAD`
- `MODEL_CFG_PATH`
- `MODEL_CKPT_PATH`
- `OUTPUT_ROOT`
- `SQLITE_PATH`
- `MAX_IMAGE_MB`
- `MAX_VIDEO_MB`
- `MAX_AUDIO_MB`
- `AASIST_ROOT`
- `AASIST_CONFIG_PATH`
- `AASIST_MODEL_PATH`
- `AASIST_THRESHOLD`
