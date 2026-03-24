# source-fetch

从 FreshRSS 读取指定时间窗内容，生成 `RawSourceItem` 主产物、抓取报告和 `step-manifest.json`。

## Inputs

- `--config`
- `--run-id`
- `--window-start`
- `--window-end`
- `--output-dir`

环境变量：

- `FRESHRSS_USERNAME`
- `FRESHRSS_API_PASSWORD`

## Outputs

- `raw-source-items.json`
- `source-fetch-report.json`
- `step-manifest.json`
