# Streamlit Community Cloud 部署

## 创建应用

1. 登录 [Streamlit Community Cloud](https://share.streamlit.io/)。
2. 选择 **Create app**。
3. Repository 选择 `994481336/aircraft-instructor-evaluation-dashboard`。
4. Branch 选择 `main`。
5. Main file path 填写 `app.py`。
6. 选择一个新的 App URL，例如 `aircraft-instructor-evaluation-dashboard`。
7. 点击 Deploy。

仓库根目录已经包含 `requirements.txt` 和 `.streamlit/config.toml`，Cloud 会自动安装依赖并使用项目主题配置。

## 部署后验证

上传空客、波音和国产民机 Excel 测试文件，确认：

- 自动跳过空工作表并识别三类机型；
- 将机型字段放在表格后部、前部保留“本机型经历时间（已删除）”等字段，具体机型仍正确识别；
- 分别单独上传波音、空客、国产民机文件，简报和总览均正常显示，不出现 `StreamlitDuplicateElementId`；
- “机型简报”默认展示全部公司，也可选择自动识别的公司并手动勾选原表单位名称；可切换按机型类别或具体机型展示，显示评估人数、评分记录数、记录平均分及分布；不提供 Word 简报下载；
- 切换到“按具体机型”后，B737 和 B787 分别展示；选择单一机型后总览、扣分明细也随之筛选；切回“按机型类别”后显示波音、空客、国产民机；只填类别的记录显示“机型未明确”；
- 总览页的文件读取概况显示每个文件的记录数和扣分记录数；
- 波音文件能够显示模拟机扣分明细；
- 空客新版文件的扣分项分布在训前讲评前和模拟机总分后时，两段均完整显示；机型等人员字段不会计入扣分；
- 同一单元格同时包含“不扣分”和负分项时，负分项仍出现在高频扣分项及个人明细中；
- 页面能够正常展示总览、个人档案、科目分析和下载明细。

## 隐私要求

- 不要把真实 Excel、Word 评分表、报告或人员信息提交到 GitHub；
- 公开 App 只建议用于脱敏数据或演示；
- 如果用于真实评估数据，先确认 App 的访问权限和组织合规要求；
- 应用本身不写入数据库，也不将上传文件保存到项目目录。

## 更新应用

```bash
git add <changed-files>
git commit -m "Describe the change"
git push origin main
```

推送到 `main` 后，Streamlit Community Cloud 会自动重新构建应用。若页面仍使用旧解析结果，先清空上传控件并重新上传文件，再执行 Reboot app。
