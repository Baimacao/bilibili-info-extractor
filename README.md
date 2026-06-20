```markdown
# 🎬 B站信息提取器

基于 **PyQt-Fluent-Widgets** 的 B 站综合信息查询工具，支持视频详情、直播间状态、用户资料、UP 主投稿列表、视频评论查询。  
所有数据来自 [UAPIS](https://uapis.cn/) 开放接口，界面采用 Fluent Design 设计语言，简洁美观。

---

## ✨ 功能
- **视频查询**：输入 AV/BV 号，获取封面、播放量、分区、UP 主信息、分P列表等。
- **直播查询**：通过 MID 或房间号查询直播状态、人气、分区、标签、简介。
- **用户查询**：输入 UID 获取昵称、等级、签名、粉丝数、投稿数等信息。
- **投稿查询**：查看指定 UP 主的所有投稿，支持关键词搜索、排序（最新/最多播放）、分页。
- **评论查询**：获取视频热门/最新评论，支持 BV 号自动转换 AID、排序、分页。
- **关于页面**：软件简介及作者、API 来源链接。
- **HTML 报告导出**：每次查询均生成美观的 WinUI 风格 HTML 页面，自动在浏览器打开。

---

## 🛠️ 技术栈
- Python 3.10+
- PyQt5 / PyQt-Fluent-Widgets（Fluent Design 界面）
- Requests（网络请求）
- urllib3（SSL 警告抑制）
- 多线程（QThread）避免界面卡死

---

## 📦 安装依赖
```bash
pip install requests pyqt5 pyqt-fluent-widgets urllib3
```

---

## 🚀 快速运行
```bash
python bilibili_info.py
```
启动后左侧导航栏切换功能模块，输入对应参数即可查询。

---

## 📁 项目结构
```
bilibili-info-extractor/
├── bilibili_info.py       # 主程序（所有功能集成）
├── README.md
└── .gitignore
```

---

## ⚠️ 注意事项
- 所有数据来自 B站公开 API（通过 UAPIS 聚合），仅用于学习交流，请勿用于商业用途。
- 代码中关闭了 SSL 证书验证（`verify=False`）以解决部分环境证书缺失问题，**本地使用无碍，但请注意网络安全**。
- 若打包为 exe，需额外处理 `qfluentwidgets` 资源路径（见 PyInstaller 文档）。
- 使用过程中若遇接口变动，可前往 [UAPIS 文档](https://uapis.cn/docs) 查看最新说明。

---

## 📄 开源协议
本项目仅供学习交流，使用 [MIT License](LICENSE)（可选，可自行添加）。

---

## 🙏 致谢
- [UAPIS](https://uapis.cn/) 提供免费、稳定的 B站数据接口
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 提供美观的 Fluent Design 组件
- [B站](https://www.bilibili.com) 开放数据支持

---

> 如果觉得不错，欢迎 ⭐ Star 本仓库！

**Author:** [Baimaco](https://space.bilibili.com/1329200878)
```