# BPB 4.0 订阅 JSON → v2ray 标准订阅转换器

将 **BPB Panel 4.0** 的订阅链接（通常返回 **Xray 配置 JSON/数组**）转换为 **v2rayN 可识别的标准分享链接订阅**：

- 输出 `vless://...`（支持 WS/TLS：host、path、sni、fp、alpn、allowInsecure 等参数）
- 输出 `trojan://...`（同样支持 WS/TLS 参数）
- 支持输出为：
  - `raw`：纯文本，一行一个分享链接
  - `base64`：Base64 订阅（v2rayN 常用）

> 适用场景：BPB `sub/normal?...app=xray` 返回的是 JSON 配置，v2rayN 无法按“节点订阅”解析，需要先转换。

---

## 功能特性

- 从 BPB/Xray JSON 中提取 `outbounds` 里的代理节点
- 生成标准 `vless://`、`trojan://` 分享链接
- 解析并映射以下常用参数：
  - `network=ws` → `type=ws` + `host` + `path`
  - `security=tls` → `security=tls` + `sni` + `fp` + `alpn` + `allowInsecure`
- 去重（保序）
- 仅使用 Python 标准库（无需安装第三方依赖）

---

## 环境要求

- Python 3.10+（3.8 也通常可用，但建议 3.10+）
- 可访问你的 BPB 订阅链接（URL）

---

## 安装与运行（Usage）

下载/保存脚本后，查看帮助：

    python bpb4_to_v2ray.py --help

---

## 使用方法

脚本支持两种输入方式：

### 1）从订阅 URL 读取（推荐）

输出 Base64 订阅（适合 v2rayN 订阅）：

    python bpb4_to_v2ray.py --url "https://你的pages.dev/sub/normal/xxxxx?app=xray" --format base64 --out sub.txt

      
      

输出原始链接列表（一行一个）：

    python bpb4_to_v2ray.py --url "https://你的pages.dev/sub/normal/xxxxx?app=xray"  --format raw --out nodes.txt
      
     
      

---

### 2）从本地 JSON 文件读取

    python bpb4_to_v2ray.py --infile config.json --format base64 --out sub.txt

---

## 在 v2rayN 中使用

### 方式 A：直接导入“分享链接”

如果你用了 `--format raw` 输出 `nodes.txt`：

1. 打开 `nodes.txt` 全选复制
2. v2rayN → 从剪贴板导入（或导入分享链接）
3. 节点会直接出现

---

### 方式 B：当作订阅（可更新）

1）生成 `sub.txt`（Base64）：

    python bpb4_to_v2ray.py --url "https://你的订阅?app=xray" --format base64 --out sub.txt

2）在 `sub.txt` 所在目录起一个简单 HTTP：

    python -m http.server 8000

3）在 v2rayN 订阅地址填：

    http://127.0.0.1:8000/sub.txt

说明：这样可以点击“更新订阅”，每次都拿到最新转换结果。

---

## 输出示例

raw 模式（nodes.txt）示例：

    vless://uuid@domain:443?encryption=none&type=ws&host=xxx&path=%2Fxxx&security=tls&sni=xxx&fp=chrome#proxy
    trojan://password@domain:443?type=ws&host=xxx&path=%2Fxxx&security=tls&sni=xxx#node

base64 模式（sub.txt）说明：
- 内容是一段 Base64（解码后即上面的 raw 文本）

---

## 常见问题（FAQ）

### 1. 为什么 v2rayN 导入 BPB 订阅会“识别不正常”？

因为 BPB `app=xray` 很多情况下返回的是 **整份 Xray 配置 JSON**（包含 `inbounds/outbounds/routing/dns`），而 v2rayN 的“订阅解析”主要支持：

- 一行一个分享链接（vless/vmess/trojan/ss…）
- 或 Base64 的链接列表
- 或 Clash/Mihomo YAML

所以需要本脚本做一层转换。

---

### 2. 脚本提示：No vless/trojan links extracted

说明你的 JSON 里 `outbounds` 可能：

- 没有 `protocol=vless` 或 `protocol=trojan`
- 或结构不一致（比如 `vmess` / `shadowsocks` / `hysteria2` 等）

解决：

- 先用 `--format raw` 看脚本是否提取到了任何链接
- 若你确实有其它协议，修改脚本里的：
  - `ALLOW_PROTOCOLS = {"vless", "trojan"}`（加入你需要的协议）
  - 并补对应的 `build_xxx_link()` 解析函数

---

### 3. path / host / sni 大小写有影响吗？

通常不影响，但：

- `sni`（serverName）建议与证书/域名匹配
- `path` 建议保持原样（脚本会 URL 编码，v2rayN 可识别）

---

### 4. UDP 被 block、规则很复杂会不会丢失？

会。因为分享链接只表达“节点连接参数”，不表达你的整份 `routing/dns` 规则。

- 本脚本的目标是把节点“提出来让 v2rayN 可用”
- 如果你想保留完整规则，请使用自定义配置方式加载 JSON（不是节点订阅）

---

## 安全提示

- 不要把订阅 URL、UUID、密码、WS path 等敏感信息公开到群/论坛
- 如果部署 Worker/在线转换器，请做好访问控制（例如加 token）

---

## License

自用脚本，按需修改即可。
