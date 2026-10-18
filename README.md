# Loon 国内外 DNS 分流

仅保存公开的 DNS 分类插件和生成程序。**不要上传完整 Loon 配置、订阅链接、节点密码或证书。**

## 使用

在 Loon 主配置的 `[Plugin]` 中加入：

```ini
https://raw.githubusercontent.com/ccc592/loon-dns-rules/main/plugins/China-DNS.lpx, enabled=true
```

插件仅包含 `[Host]`，将完整 CN 域名集合转换成根域名及通配子域名映射，使用 `https://223.5.5.5/dns-query`。其他域名沿用主配置默认 DNS。`foreign-dns-exceptions.txt` 排除 AI 及 DNS 检测域名，避免上游分类覆盖主配置的境外解析例外；例如上游 CN 库包含的 `browserleaks.com` 会被排除。

主配置仍须将 `223.5.5.5/32` 的连接设为 `DIRECT`，将默认境外 DoH 的连接设为机场代理。插件本身不决定 DNS 请求的网络出口，也不修改业务路由、代理组、防泄露插件或系统设置。

Loon 的 DNS 页面需关闭“包含系统 DNS 地址”和“查询回落”，开启加密 DNS 遵循规则。仅使用插件不能保证设备没有 DNS 绕行。

## 自动更新与验证

GitHub Actions 每天约北京时间 06:30 从上游 `meta` 分支取得最新提交，按该提交固定地址下载完整 CN 列表，再生成并提交插件。计划任务实际时间可能延迟；新仓库已用手动工作流验证。Loon 端仍需成功更新远程插件，服务端更新不会主动推送到手机。

生成程序拒绝未知匹配格式、异常规模、超过 10% 的突然缩减，以及常用国内/AI 域名分类回归。失败时工作流保留上次插件。`manifest.json` 记录源提交、SHA-256、域名及映射数量。

```sh
python3 scripts/update_dns.py
```

远程化减少主配置中的内嵌内容，手机仍会下载并加载完整 DNS 映射，不能据此声称降低了 Loon 内存占用。电脑静态检查也不能代替 iPhone 实测。

## 数据与许可

- 上游：[MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)，`meta/geo/geosite/cn.list`，GPL-3.0。
- 上游聚合来源及维护方式以其仓库说明为准。
- 本仓库的生成代码及分发数据遵循 GPL-3.0，完整许可见 `LICENSE`。
- Loon 格式参考：[DNS 映射](https://nsloon.app/docs/DNS/hostmap/)、[插件](https://nsloon.app/docs/Plugin/)。
