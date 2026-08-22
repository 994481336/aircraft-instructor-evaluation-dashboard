# 型别教员测试结果看板

这是一个基于 Streamlit 的型别教员评估数据看板。应用支持上传导出的 Excel，自动识别有效工作表、机型类别、评分字段和扣分明细，并提供总览驾驶舱、教员档案、科目分析和数据质量检查。

## 当前能力

- 支持空客、波音、国产民机三类规则版本；
- 自动跳过空工作表并识别真实表头；
- 解析训前讲评分数、模拟机各科分数、总分和扣分文本；
- 对总分不一致、未识别扣分文本和未知机型显示待复核；
- 支持按机型类别、单位和技术等级筛选；
- 支持导出标准化人员数据和扣分明细 Excel；
- 上传文件只在当前 Streamlit 会话内处理，不提交、不写入仓库。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 测试

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m py_compile app.py data_loader.py normalizer.py analysis.py
```

## 评分规则

`rules/` 中的 YAML 文件是从三份 Word 评分表整理出的规则版本。正式合格线尚未启用，应用暂时展示得分、失分、风险等级和待复核状态，不自动下结论。

## 公开部署注意事项

不要将真实 Excel、Word 评分表、人员姓名或其他敏感数据提交到 GitHub。代码仓库可以公开，但真实数据应通过上传使用，并在确认部署权限后再用于线上评估。

在 Streamlit Community Cloud 中创建应用时，入口文件选择 `app.py`，依赖文件使用根目录的 `requirements.txt`。
