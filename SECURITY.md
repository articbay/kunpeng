# Security Policy

## 不得提交的内容

- `.env`、API Key、数据库密码、JWT/加密密钥、OAuth Client Secret
- 数据库文件、SQL dump、接口原始响应、日志、用户上传文件
- Excel/CSV 导出、截图或包含真实订单/客户信息的测试夹具

仓库中的 `.env.example` 只能使用明显的占位值。

## 提交前检查

```bash
git status --short
git diff --cached
git grep -n -I -E '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|API[_-]?KEY|CLIENT_SECRET|DATABASE_URL|PASSWORD|SECRET_KEY)'
```

最后一条命令会同时匹配变量名和文档说明，需要人工确认其值是占位符，而不是直接忽略结果。

## 误提交凭据后的处理

1. 立即在对应服务中撤销并轮换凭据。
2. 从当前文件和 Git 历史中清除该值。
3. 再次扫描完整历史后才能推送或解除仓库访问限制。
