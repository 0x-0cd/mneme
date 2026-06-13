# 约定式提交规范 v1.0.0

本仓库遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) 规范。

## 提交格式

```
<类型>[可选 范围]: <描述>

[可选 正文]

[可选 脚注]
```

## 类型

| 类型 | 说明 |
|:----|:------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/项目初始化 |
| `ci` | CI 配置变更 |

## 破坏性变更

类型后加 `!`，或在脚注中写 `BREAKING CHANGE:`。

```
feat(api)!: 删除过时的 v1 接口
```

详见官方文档：https://www.conventionalcommits.org/zh-hans/v1.0.0/
