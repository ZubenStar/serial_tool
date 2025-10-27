# Release Notes 使用指南

本文档说明如何使用优化后的GitHub Release Notes系统。

## 📋 文件说明

### 1. `.github/release.yml`
自动分类配置文件，GitHub会根据PR/Commit的标签自动将变更分类到对应的章节。

### 2. `.github/workflows/build-release.yml`
自动构建和发布workflow，包含优化后的release notes模板。

### 3. `.github/PULL_REQUEST_TEMPLATE.md`
PR模板，帮助贡献者正确标记变更类型。

## 🏷️ 标签系统

为了让release notes自动分类，请在PR或commit中使用以下标签：

| 标签 | 用途 | 示例 |
|------|------|------|
| `feature`, `enhancement`, `new` | 新功能 | 添加新的串口配置功能 |
| `bug`, `fix`, `bugfix` | Bug修复 | 修复串口断开重连问题 |
| `documentation`, `docs` | 文档更新 | 更新README使用说明 |
| `performance`, `optimization` | 性能优化 | 优化数据接收效率 |
| `ui`, `ux`, `style` | 界面改进 | 改进主界面布局 |
| `refactor`, `refactoring` | 代码重构 | 重构串口管理模块 |
| `test`, `testing` | 测试相关 | 添加单元测试 |
| `security` | 安全更新 | 修复安全漏洞 |

## 🚀 发布流程

### 方式1: 通过Git标签触发（推荐）

```bash
# 1. 确保所有更改已提交
git add .
git commit -m "chore: prepare for release v1.2.0"

# 2. 创建标签
git tag -a v1.2.0 -m "Release version 1.2.0"

# 3. 推送标签到GitHub
git push origin v1.2.0

# 4. GitHub Actions会自动：
#    - 构建Windows可执行文件
#    - 创建ZIP压缩包
#    - 创建GitHub Release
#    - 生成优化的Release Notes
```

### 方式2: 手动触发

1. 访问 GitHub Actions 页面
2. 选择 "Build and Release" workflow
3. 点击 "Run workflow"
4. 选择分支并运行

## 📝 Release Notes 结构

优化后的release notes包含以下部分：

1. **核心功能** - 展示项目的主要特性
2. **快速开始** - 简明的安装和使用步骤
3. **系统要求** - 运行环境说明
4. **更新日志** - 自动生成的变更记录（按类别分组）
5. **相关链接** - 文档、问题反馈等链接
6. **注意事项** - 重要提示

## 💡 最佳实践

### Commit Message 规范

使用约定式提交（Conventional Commits）格式：

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

示例：
```
feat(gui): 添加深色主题支持

- 新增主题切换按钮
- 支持保存主题偏好
- 优化深色模式下的颜色对比度

Closes #123
```

### 常用的 type 类型

- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

### 添加标签到PR

在GitHub上创建或编辑PR时，在右侧栏选择适当的标签：

1. 点击 "Labels"
2. 选择一个或多个相关标签
3. 标签会自动应用到release notes分类

## 🎯 示例

### 好的Commit示例

```
feat(serial): 添加自动重连功能

当串口意外断开时，工具现在会自动尝试重新连接。

- 添加重连间隔配置选项
- 添加最大重连次数限制
- 在状态栏显示重连状态

Closes #45
```

### 对应的Release Notes输出

在发布时，这个变更会自动出现在 "🚀 新增功能" 章节下：

```markdown
## 🚀 新增功能 / New Features
- 添加自动重连功能 by @username in #123
  当串口意外断开时，工具现在会自动尝试重新连接。
```

## 🔧 自定义配置

如需修改分类或标签，编辑 `.github/release.yml` 文件：

```yaml
changelog:
  categories:
    - title: 你的自定义分类
      labels:
        - custom-label
```

## ❓ 常见问题

### Q: Release notes没有自动生成？
A: 确保在workflow中设置了 `generate_release_notes: true`

### Q: 变更没有正确分类？
A: 检查PR或commit是否添加了正确的标签

### Q: 如何排除某些提交？
A: 使用 `ignore-for-release` 标签，或在 `release.yml` 中配置排除规则

## 📚 参考资料

- [GitHub Release Notes 官方文档](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)
- [Conventional Commits 规范](https://www.conventionalcommits.org/)
- [语义化版本](https://semver.org/lang/zh-CN/)