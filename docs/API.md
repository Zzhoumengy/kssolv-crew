# Web API

0.2.0 起默认 start.cmd 打开原生桌面版，不使用 HTTP。需要下面的可选 Web API 时双击 start-web.cmd；它会在后台启动服务，检查就绪后打开实际网址。8000 被占用时可能使用相邻端口，以 .runtime/website.url 为准。

`GET /health` 还包含 `service=kssolv-crew` 和非敏感实例标识，供启动器核实服务身份。后台服务另有 `POST /service/stop`，需 .runtime/server.json 中的私有控制令牌（X-Service-Token 请求头）；正常使用请直接双击 stop.cmd，不要公开此文件。该控制令牌不出现在 health 或发布包中。

默认基址 `http://127.0.0.1:8000`。交互文档 `/docs`。

## 提交

`POST /jobs`，JSON：

```json
{
  "task": "计算硅 Si 的能带图",
  "mp_api_key": "YOUR_MP_KEY",
  "llm_api_key": "YOUR_LLM_KEY",
  "material_id": "mp-149",
  "mode": "run",
  "parameters": {
    "ecut": 20,
    "mesh": [2, 2, 2],
    "nbnd": 14,
    "points_per_segment": 20,
    "functional": "PBE",
    "smear": "gaussian"
  }
}
```

`material_id` 可省略或为 null；`mode=prepare` 不运行 MATLAB。默认参数只是用户示例，需按实际材料收敛测试。

返回 202：`{"job_id":"<uuid>","token":"<访问令牌>","status":"queued"}`。保存 token，它只返回一次。密钥只用于本次任务；不得把真实密钥提交到源码仓库。

## 状态与日志

`GET /jobs/<uuid>`，请求头 `Authorization: Bearer <访问令牌>`。

返回当前 `status`、`time`、异常类型或受控错误提示、`artifacts` 文件名列表。非法 token 或未知任务返回 404。`GET /jobs/<uuid>/artifacts/events.jsonl` 下载阶段日志；真实计算的详细输出在 `matlab.log`、`engine_console.log`。

`completed_unverified` 表示程序已获得预期输出，收敛仍需人工核实。`prepared` 表示只生成输入，无 SCF/NSCF 结果。

## 文件下载

`GET /jobs/<uuid>/artifacts/<filename>`，同样携带 Bearer token。可下载报告、配置、PNG、FIG、MAT、JSON 等。不开放任意目录路径或访问令牌哈希文件。

`GET /health` 返回服务状态及 KSSOLV 路径是否存在，不会启动 MATLAB。

本原型面向本机使用；不要直接作为无认证的公网任务提交端点。提交队列满返回 429，运行模式缺 KSSOLV 目录返回 503，输入校验错误返回 422。错误响应不回显密钥字段原值。
