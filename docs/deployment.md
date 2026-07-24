# 自有服务器部署

## 部署方式

项目使用 Next.js 静态导出。`pnpm build` 会生成 `out/` 目录，生产服务器只需要提供其中的 HTML、CSS、JavaScript 和静态资源，不需要运行 Node.js、Vinext、Wrangler 或 Cloudflare Worker。

## 构建

构建环境要求：

- Node.js `>=20.9.0`
- pnpm `10.34.5`

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm check
```

验证通过后，部署产物位于 `out/`。

## 上传

将 `out/` 中的内容上传到服务器站点目录。例如：

```bash
rsync -avz out/ your-user@your-server:/var/www/echo-home/
```

请将示例中的用户名、服务器地址和目录替换为实际值。

## Nginx 示例

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    root /var/www/echo-home;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /_next/static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

保存配置后检查并重新加载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

正式上线时还应为域名配置 HTTPS。使用 Caddy、Apache 或对象存储/CDN 时，同样只需要发布 `out/` 中的内容。
