## v0.2.0

### feat
- 附件支持：登录态下载（`.luogu_cookies.json` 配置 `__client_id`/`_uid`）、导出到 `data/<exec_name>/`、题面【附件】节、纳入下发 zip、代码/数据文件提示
- 示例代码 minted 语法高亮（代码块按语言折行、下划线斜体 `_x_`）
- 样例数据命名：english 前缀 `{english}{n}.in/.ans`、样例输出扩展名 `.out` → `.ans`

### fix
- english/exec_name 含下划线导致编译失败（Missing $）
- 引用块 `>` 后直接接内容漏解析（含死循环）

### test / docs
- 新增测试（附件/示例代码/转义/引用块）
- docs/implementation.md、README、docs/TODO.md（markdown-it-py 迁移计划）更新
