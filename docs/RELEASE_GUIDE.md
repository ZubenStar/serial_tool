# 发布指南

本项目配置了GitHub Actions自动构建和发布流程，可以自动生成Windows exe文件并发布到GitHub Releases。

## 自动发布流程

### 方式1：通过Git标签触发（推荐）

当你推送一个以 `v` 开头的标签时，会自动触发构建和发布：

```bash
# 1. 确保所有更改已提交
git add .
git commit -m "准备发布 v1.0.0"

# 2. 创建标签（版本号格式：v主版本.次版本.修订号）
git tag v1.0.0

# 3. 推送标签到GitHub
git push origin v1.0.0

# 或者一次性推送代码和标签
git push origin main --tags
```

### 方式2：手动触发

1. 进入GitHub仓库页面
2. 点击 `Actions` 标签
3. 选择 `Build and Release` 工作流
4. 点击 `Run workflow` 按钮
5. 选择分支后点击绿色的 `Run workflow` 按钮

## 自动化流程说明

GitHub Actions会自动执行以下操作：

1. **环境准备**
   - 设置Windows构建环境
   - 安装Python 3.10
   - 安装项目依赖

2. **构建exe文件**
   - 使用PyInstaller打包应用
   - 生成单个exe文件：`串口监控工具.exe`

3. **打包发布**
   - 创建ZIP压缩包：`串口监控工具-Windows-x64.zip`
   - 包含exe文件、logs目录和README文档

4. **发布Release**
   - 自动创建GitHub Release
   - 上传ZIP文件作为发布附件
   - 生成版本说明

## 版本号规范

建议使用[语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号（Major）**：不兼容的API修改
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正

示例：
- `v1.0.0` - 首次正式发布
- `v1.1.0` - 添加新功能
- `v1.1.1` - 修复bug
- `v2.0.0` - 重大更新

## 发布检查清单

在发布新版本前，请确认：

- [ ] 所有代码已提交到main分支
- [ ] 更新了README.md中的版本信息（如需要）
- [ ] 测试过主要功能正常工作
- [ ] 更新了CHANGELOG（如有维护）
- [ ] 版本号遵循语义化版本规范

## 查看发布结果

1. **GitHub Actions进度**
   - 访问仓库的 `Actions` 标签
   - 查看工作流运行状态（大约3-5分钟）

2. **下载发布包**
   - 访问仓库的 `Releases` 页面
   - 找到对应版本的Release
   - 下载 `串口监控工具-Windows-x64.zip`

## 常见问题

### Q: 如何删除错误的标签？

```bash
# 删除本地标签
git tag -d v1.0.0

# 删除远程标签
git push origin :refs/tags/v1.0.0
```

### Q: 如何修改已发布的Release？

1. 进入GitHub仓库的Releases页面
2. 找到对应的Release
3. 点击右侧的编辑按钮
4. 修改标题、说明或重新上传文件

### Q: 构建失败怎么办？

1. 查看Actions日志，定位失败原因
2. 修复问题后重新推送
3. 如果是标签触发的，需要删除旧标签重新创建

### Q: 如何发布预发布版本（Pre-release）？

可以使用带后缀的版本号，如：
- `v1.0.0-beta.1`
- `v1.0.0-rc.1`
- `v1.0.0-alpha.1`

然后在GitHub Release页面手动标记为Pre-release。

## 本地测试打包

在推送到GitHub前，建议先在本地测试打包：

```bash
# 运行本地打包脚本
python build_exe.py

# 测试生成的exe
cd dist
.\串口监控工具.exe
```

## 工作流配置文件

工作流配置文件位于：`.github/workflows/build-release.yml`

如需修改构建流程，可以编辑此文件。