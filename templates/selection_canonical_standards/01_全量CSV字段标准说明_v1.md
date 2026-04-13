# 全量 CSV 字段标准说明 v1
## 0. 说明
- 本说明对应本仓库的 canonical 标准与派生模板体系
- canonical 标准原件固定放在 `templates/selection_canonical_standards/`
- operator-facing 派生模板固定放在 `templates/selection_csv_cn_reference/`
- 字段标准以 `templates/selection_canonical_standards/99_字段数据标准总表.csv` 为机器可读总表
- `03_候选市场与候选品初筛池.csv` 与 `04_供应链询价与利润核算.csv` 属于 repo-local 工作表，不属于 external canonical field master
- 以下 4 类字段一律留给人工：合规 / 改良点 / 最终解释 / 利润核价

## 00_选品运行目标与边界.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | MANUAL | 本轮运行唯一名称 |
| 站点 | enum | REQUIRED | MANUAL | 如 US/JP/UK |
| 主目标 | enum | REQUIRED | MANUAL | 如 利润优先/周转优先 |
| 选品路径 | enum | REQUIRED | MANUAL | 如 市场优先/关键词优先 |
| 默认履约方式 | enum | REQUIRED | MANUAL | 如 FBA/FBM |
| 目标售价下限 | number | REQUIRED | MANUAL | 目标售价下限，美元 |
| 目标售价上限 | number | REQUIRED | MANUAL | 目标售价上限，美元 |
| 预算上限 | number | REQUIRED | MANUAL | 本轮预算上限 |
| 可接受最小起订量上限 | number | REQUIRED | MANUAL | MOQ 上限 |
| 是否允许审批类目 | enum | REQUIRED | MANUAL | 是/否 |
| 是否允许危险品 | enum | REQUIRED | MANUAL | 是/否 |
| 商标风险容忍度 | enum | REQUIRED | MANUAL | 低/中/高 |
| 专利风险容忍度 | enum | REQUIRED | MANUAL | 低/中/高 |
| 回本周期上限_月 | number | REQUIRED | MANUAL | 最大可接受回本周期 |
| 最大周转月数 | number | REQUIRED | MANUAL | 最大可接受库存周转月数 |
| 是否允许季节性 | enum | REQUIRED | MANUAL | 是/否 |
| 单品预期月净利下限 | number | OPTIONAL | MANUAL | 本轮单品预期最低月净利 |
| 备注 | string | OPTIONAL | MANUAL | 补充说明 |

## 01_市场入口与筛选参数.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | MANUAL | 与 00 对应 |
| 方向ID | string | REQUIRED | MANUAL | 每个方向唯一 ID |
| 方向词 | string | REQUIRED | MANUAL | 探索方向，如 claw machine |
| 类目提示 | string | OPTIONAL | MANUAL | 类目提示或路径线索 |
| 站点 | enum | REQUIRED | MANUAL | 如 US |
| 时间范围_天 | number | REQUIRED | MANUAL | 如 30 |
| 新品定义_天 | number | REQUIRED | MANUAL | 如 180 |
| 样本数前N | number | REQUIRED | MANUAL | 如 100 |
| 头部商品前N | number | REQUIRED | MANUAL | 如 10 |
| 是否启用关键词趋势研究 | enum | REQUIRED | MANUAL | 是/否 |
| 是否启用市场调研 | enum | REQUIRED | MANUAL | 是/否 |
| 是否启用竞品基准研究 | enum | REQUIRED | MANUAL | 是/否 |
| 是否启用SIF补强 | enum | REQUIRED | MANUAL | 是/否 |
| 每个方向最大下推关键词数 | number | REQUIRED | MANUAL | 本轮每个方向最大下推关键词数 |
| 每个方向最大候选样品数 | number | REQUIRED | MANUAL | 本轮每个方向最大候选样品数 |
| 备注 | string | OPTIONAL | MANUAL | 补充说明 |

## 02_账号与合规预检查.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | MANUAL | 与 00 对应 |
| 站点 | enum | REQUIRED | MANUAL | 如 US |
| 目标类目 | string | REQUIRED | MANUAL | 拟进入类目 |
| 类目访问状态 | enum | REQUIRED | MANUAL | 待检查/可访问/不可访问 |
| 是否已具备审批条件 | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做FBA | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做FBM | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做危险品 | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做带电商品 | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做液体商品 | enum | REQUIRED | MANUAL | 是/否 |
| 是否可做易碎商品 | enum | REQUIRED | MANUAL | 是/否 |
| 品牌备案要求 | string | OPTIONAL | MANUAL | 有无备案要求 |
| 发票或资质要求 | string | OPTIONAL | MANUAL | 如发票/COA/GMP等 |
| 当前已知限制 | string | OPTIONAL | MANUAL | 当前已知边界 |
| 合规 | string | OPTIONAL | MANUAL | 人工留空，最终人工填写 |
| 备注 | string | OPTIONAL | MANUAL | 补充说明 |

## 10_方向输入校验结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 方向词 | string | REQUIRED | AUTO | 来自 01 |
| 校验时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 字段完整性状态 | enum | REQUIRED | AUTO | PASS/FAIL |
| 站点状态 | enum | REQUIRED | AUTO | PASS/FAIL |
| 价格带状态 | enum | REQUIRED | AUTO | PASS/FAIL |
| 禁区状态 | enum | REQUIRED | AUTO | PASS/FAIL |
| 方向粒度状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 校验结果 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 失败原因代码 | string | OPTIONAL | AUTO | 规则失败代码 |
| 失败原因说明 | string | OPTIONAL | AUTO | 规则失败说明 |
| 是否下推到Step2 | enum | REQUIRED | AUTO | 是/否 |

## 20_关键词证据词池原始结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 方向词 | string | REQUIRED | AUTO | 来自 01 |
| 关键词来源模块 | enum | REQUIRED | AUTO | KeywordResearch/KeywordTrendResearch |
| 关键词 | string | REQUIRED | AUTO | SellerSprite 原始关键词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 主类目 | string | OPTIONAL | AUTO | SellerSprite 返回类目 |
| 月搜索量 | number | OPTIONAL | AUTO | 月搜索量 |
| 搜索频率排名 | number | OPTIONAL | AUTO | 搜索频率排名 |
| 搜索量增长率_pct | number | OPTIONAL | AUTO | 增长率百分比 |
| 点击集中度_pct | number | OPTIONAL | AUTO | 点击集中度 |
| 流量成本指数 | number | OPTIONAL | AUTO | SellerSprite traffic cost 或内部归一化指标 |
| 机会标签 | string | OPTIONAL | AUTO | 如 Opportunities/Potential |
| 趋势标签 | string | OPTIONAL | AUTO | 如 Trending/RapidGrowth |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 来源查询词 | string | REQUIRED | AUTO | 本次方向词或上游词 |
| 来源文件 | string | OPTIONAL | AUTO | 原始抓取文件路径或索引 |

## 21_关键词证据词池清洗结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 方向词 | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 原始关键词 |
| 标准化关键词 | string | REQUIRED | AUTO | 清洗后的关键词 |
| 关键词角色 | enum | REQUIRED | AUTO | 核心词/次级核心词/长尾词/噪音词 |
| 去重组ID | string | OPTIONAL | AUTO | 语义去重分组 |
| 排除标记 | enum | REQUIRED | AUTO | 是/否 |
| 排除原因代码 | string | OPTIONAL | AUTO | 噪音、太宽、无量等 |
| 月搜索量 | number | OPTIONAL | AUTO | 沿用上游 |
| 搜索量增长率_pct | number | OPTIONAL | AUTO | 沿用上游 |
| 点击集中度_pct | number | OPTIONAL | AUTO | 沿用上游 |
| 流量成本指数 | number | OPTIONAL | AUTO | 沿用上游 |
| 排序分值 | number | OPTIONAL | AUTO | 内部排序分值 |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |

## 22_关键词证据词池下推结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 标准化后关键词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 月搜索量 | number | OPTIONAL | AUTO | 来自 SellerSprite |
| 搜索量增长率_pct | number | OPTIONAL | AUTO | 来自 SellerSprite |
| 点击集中度_pct | number | OPTIONAL | AUTO | 来自 SellerSprite |
| 流量成本指数 | number | OPTIONAL | AUTO | 来自 SellerSprite |
| 机会标签 | string | OPTIONAL | AUTO | 来自 SellerSprite |
| 趋势标签 | string | OPTIONAL | AUTO | 来自 SellerSprite |
| 命中规则数 | number | REQUIRED | AUTO | 通过规则数量 |
| 失败规则数 | number | REQUIRED | AUTO | 失败规则数量 |
| 整体状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 失败原因代码 | string | OPTIONAL | AUTO | 失败原因代码集合 |
| 是否下推到Step3 | enum | REQUIRED | AUTO | 是/否 |
| 下推批次号 | string | REQUIRED | AUTO | 本轮批次号 |

## 30_市场调研原始索引.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 本次跑数关键词 |
| 市场工作簿文件名 | string | REQUIRED | AUTO | xlsx 文件名 |
| 市场工作表 | string | OPTIONAL | AUTO | 识别到的 sheet |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 文件路径 | string | REQUIRED | AUTO | 本地路径 |
| 文件大小_bytes | number | OPTIONAL | AUTO | 文件大小 |
| 解析状态 | enum | REQUIRED | AUTO | PASS/FAIL |
| 解析失败原因 | string | OPTIONAL | AUTO | 失败说明 |

## 31_市场调研清洗结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 本次跑数关键词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 市场路径 | string | OPTIONAL | AUTO | 类目路径 |
| 候选市场名称 | string | REQUIRED | AUTO | 市场名称 |
| 商品样本数 | number | OPTIONAL | AUTO | 样本商品数 |
| 品牌样本数 | number | OPTIONAL | AUTO | 样本品牌数 |
| 卖家样本数 | number | OPTIONAL | AUTO | 样本卖家数 |
| 月总销量 | number | OPTIONAL | AUTO | 月总销量 |
| 月均销量 | number | OPTIONAL | AUTO | 月均销量 |
| 月均销售额 | number | OPTIONAL | AUTO | 月均销售额 |
| 平均价格 | number | OPTIONAL | AUTO | 平均价格 |
| 平均评分数 | number | OPTIONAL | AUTO | 平均评分数 |
| 平均星级 | number | OPTIONAL | AUTO | 平均星级 |
| 新品数量 | number | OPTIONAL | AUTO | 新品数量 |
| 新品占比_pct | number | OPTIONAL | AUTO | 新品占比 |
| 商品集中度 | number | OPTIONAL | AUTO | 商品集中度 |
| 品牌集中度 | number | OPTIONAL | AUTO | 品牌集中度 |
| 卖家集中度 | number | OPTIONAL | AUTO | 卖家集中度 |
| 来源工作簿 | string | REQUIRED | AUTO | 工作簿文件名 |
| 来源工作表 | string | OPTIONAL | AUTO | 工作表名称 |
| 来源数据行 | number | OPTIONAL | AUTO | 工作表数据行 |

## 32_市场调研下推结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 本次跑数关键词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 候选市场名称 | string | REQUIRED | AUTO | 市场名称 |
| 平均价格 | number | OPTIONAL | AUTO | 平均价格 |
| 月总销量 | number | OPTIONAL | AUTO | 月总销量 |
| 新品占比_pct | number | OPTIONAL | AUTO | 新品占比 |
| 商品集中度 | number | OPTIONAL | AUTO | 商品集中度 |
| 品牌集中度 | number | OPTIONAL | AUTO | 品牌集中度 |
| 卖家集中度 | number | OPTIONAL | AUTO | 卖家集中度 |
| 命中规则数 | number | REQUIRED | AUTO | 通过规则数量 |
| 失败规则数 | number | REQUIRED | AUTO | 失败规则数量 |
| 整体状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 失败原因代码 | string | OPTIONAL | AUTO | 失败原因代码集合 |
| 是否下推到Step4 | enum | REQUIRED | AUTO | 是/否 |
| 下推批次号 | string | REQUIRED | AUTO | 本轮批次号 |

## 40_竞品基准结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 候选市场名称 | string | REQUIRED | AUTO | 候选市场 |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 样品标题 | string | REQUIRED | AUTO | 样品标题 |
| 品牌 | string | OPTIONAL | AUTO | 品牌名 |
| 价格 | number | OPTIONAL | AUTO | 当前价格 |
| 评分 | number | OPTIONAL | AUTO | 当前评分 |
| 评论数 | number | OPTIONAL | AUTO | 评论数 |
| BSR | number | OPTIONAL | AUTO | BSR |
| 父体ASIN | string | OPTIONAL | AUTO | 父体 ASIN |
| 变体数 | number | OPTIONAL | AUTO | 变体数 |
| 卖家类型 | string | OPTIONAL | AUTO | 自营/第三方等 |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 来源模块 | enum | REQUIRED | AUTO | Benchmark/Competitor |
| 来源文件 | string | OPTIONAL | AUTO | 原始抓取文件 |

## 41_候选产品种子池.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部唯一候选样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 样品标题 | string | REQUIRED | AUTO | 样品标题 |
| 品牌 | string | OPTIONAL | AUTO | 品牌名 |
| 价格 | number | OPTIONAL | AUTO | 当前价格 |
| 评分 | number | OPTIONAL | AUTO | 评分 |
| 评论数 | number | OPTIONAL | AUTO | 评论数 |
| 父体ASIN | string | OPTIONAL | AUTO | 父体 ASIN |
| 变体数 | number | OPTIONAL | AUTO | 变体数 |
| 市场路径 | string | OPTIONAL | AUTO | 来源市场路径 |
| 候选市场名称 | string | REQUIRED | AUTO | 候选市场 |
| 进入种子池状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 去重组ID | string | OPTIONAL | AUTO | 相似样品去重组 |
| 去重说明 | string | OPTIONAL | AUTO | 去重说明 |
| 是否下推到Step5 | enum | REQUIRED | AUTO | 是/否 |

## 42_竞品基准下推结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 评分 | number | OPTIONAL | AUTO | 评分 |
| 评论数 | number | OPTIONAL | AUTO | 评论数 |
| 价格 | number | OPTIONAL | AUTO | 价格 |
| 变体数 | number | OPTIONAL | AUTO | 变体数 |
| 命中规则数 | number | REQUIRED | AUTO | 通过规则数量 |
| 失败规则数 | number | REQUIRED | AUTO | 失败规则数量 |
| 整体状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 失败原因代码 | string | OPTIONAL | AUTO | 失败原因代码集合 |
| 是否下推到Step5 | enum | REQUIRED | AUTO | 是/否 |
| 下推批次号 | string | REQUIRED | AUTO | 本轮批次号 |

## 50_SIF流量结构补强.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 主流量词列表 | string | OPTIONAL | AUTO | 主要流量词，分号分隔 |
| 自然流量占比_pct | number | OPTIONAL | AUTO | 自然流量占比 |
| 广告流量占比_pct | number | OPTIONAL | AUTO | 广告流量占比 |
| 推荐流量占比_pct | number | OPTIONAL | AUTO | 推荐流量占比 |
| Deal流量占比_pct | number | OPTIONAL | AUTO | Deal 流量占比 |
| 变体主推款 | string | OPTIONAL | AUTO | 当前主推变体 |
| 变体流量分布摘要 | string | OPTIONAL | AUTO | 变体流量摘要 |
| 核心流量结构状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 来源模块 | string | REQUIRED | AUTO | SIF_查流量结构/反查流量词 |

## 51_SIF关键词价值补强.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 核心关键词 | string | OPTIONAL | AUTO | 核心关键词，分号分隔 |
| 长尾关键词 | string | OPTIONAL | AUTO | 长尾关键词，分号分隔 |
| 关键词数量 | number | OPTIONAL | AUTO | 识别到的关键词数量 |
| 高价值关键词数 | number | OPTIONAL | AUTO | 符合规则的高价值词数 |
| 建议竞价中位数 | number | OPTIONAL | AUTO | SIF/平台建议竞价中位数 |
| 高竞价关键词数 | number | OPTIONAL | AUTO | 高竞价关键词数量 |
| 关键词价值状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 来源模块 | string | REQUIRED | AUTO | SIF_选词/查竞价 |

## 52_SIF广告结构补强.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 广告词数量 | number | OPTIONAL | AUTO | 广告词数量 |
| 广告活动结构摘要 | string | OPTIONAL | AUTO | 广告活动结构摘要 |
| 广告依赖状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 自然位趋势摘要 | string | OPTIONAL | AUTO | 自然位趋势摘要 |
| 广告位趋势摘要 | string | OPTIONAL | AUTO | 广告位趋势摘要 |
| 坑位稳定性状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 抓取时间 | datetime | REQUIRED | AUTO | ISO 时间 |
| 来源模块 | string | REQUIRED | AUTO | SIF_广告透视仪/查坑位 |

## 53_SIF补强下推结果.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 关键词 | string | REQUIRED | AUTO | 来源关键词 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 核心流量结构状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 关键词价值状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 广告依赖状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 坑位稳定性状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 命中规则数 | number | REQUIRED | AUTO | 通过规则数量 |
| 失败规则数 | number | REQUIRED | AUTO | 失败规则数量 |
| 整体状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 失败原因代码 | string | OPTIONAL | AUTO | 失败原因代码集合 |
| 是否下推到Step6 | enum | REQUIRED | AUTO | 是/否 |
| 下推批次号 | string | REQUIRED | AUTO | 本轮批次号 |

## 60_候选样品池.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 方向词 | string | REQUIRED | AUTO | 方向词 |
| 站点 | enum | REQUIRED | AUTO | 如 US |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 样品标题 | string | REQUIRED | AUTO | 样品标题 |
| 品牌 | string | OPTIONAL | AUTO | 品牌 |
| 市场路径 | string | OPTIONAL | AUTO | 市场路径 |
| 候选市场名称 | string | REQUIRED | AUTO | 候选市场 |
| 核心关键词 | string | OPTIONAL | AUTO | 核心关键词 |
| 长尾关键词 | string | OPTIONAL | AUTO | 长尾关键词 |
| 平均价格 | number | OPTIONAL | AUTO | 平均价格 |
| 月总销量 | number | OPTIONAL | AUTO | 月总销量 |
| 新品占比_pct | number | OPTIONAL | AUTO | 新品占比 |
| 商品集中度 | number | OPTIONAL | AUTO | 商品集中度 |
| 品牌集中度 | number | OPTIONAL | AUTO | 品牌集中度 |
| 卖家集中度 | number | OPTIONAL | AUTO | 卖家集中度 |
| 自然流量占比_pct | number | OPTIONAL | AUTO | 自然流量占比 |
| 广告流量占比_pct | number | OPTIONAL | AUTO | 广告流量占比 |
| 推荐流量占比_pct | number | OPTIONAL | AUTO | 推荐流量占比 |
| 建议竞价中位数 | number | OPTIONAL | AUTO | 建议竞价中位数 |
| 关键词价值状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 广告依赖状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 当前下推状态 | enum | REQUIRED | AUTO | PASS/FAIL/HOLD |
| 合规 | string | OPTIONAL | MANUAL | 人工留空 |
| 改良点 | string | OPTIONAL | MANUAL | 人工留空 |
| 最终解释 | string | OPTIONAL | MANUAL | 人工留空 |
| 利润核价 | string | OPTIONAL | MANUAL | 人工留空 |
| 备注 | string | OPTIONAL | MANUAL | 人工补充 |

## 61_待供应链核利清单.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | AUTO | 与 00 对应 |
| 方向ID | string | REQUIRED | AUTO | 来自 01 |
| 样品ID | string | REQUIRED | AUTO | 内部样品 ID |
| 样品ASIN | string | REQUIRED | AUTO | 样品 ASIN |
| 样品标题 | string | REQUIRED | AUTO | 样品标题 |
| 核心关键词 | string | OPTIONAL | AUTO | 核心关键词 |
| 长尾关键词 | string | OPTIONAL | AUTO | 长尾关键词 |
| 目标售价 | number | OPTIONAL | MANUAL | 人工填写 |
| 目标MOQ | number | OPTIONAL | MANUAL | 人工填写 |
| 供应商名称 | string | OPTIONAL | MANUAL | 人工填写 |
| 供应商链接 | string | OPTIONAL | MANUAL | 人工填写 |
| 出厂价 | number | OPTIONAL | MANUAL | 人工填写 |
| 包装成本 | number | OPTIONAL | MANUAL | 人工填写 |
| 头程成本 | number | OPTIONAL | MANUAL | 人工填写 |
| 平台费预估 | number | OPTIONAL | MANUAL | 人工填写 |
| 仓储费预估 | number | OPTIONAL | MANUAL | 人工填写 |
| 利润核价 | string | OPTIONAL | MANUAL | 人工留空 |
| 合规 | string | OPTIONAL | MANUAL | 人工留空 |
| 改良点 | string | OPTIONAL | MANUAL | 人工留空 |
| 最终解释 | string | OPTIONAL | MANUAL | 人工留空 |
| 最终GoNoGo | enum | OPTIONAL | MANUAL | 人工留空 |
| 人工处理状态 | enum | REQUIRED | AUTO | PENDING/IN_PROGRESS/DONE |
| 备注 | string | OPTIONAL | MANUAL | 人工填写 |

## 62_最终决策表.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| 运行名称 | string | REQUIRED | MANUAL | 与 00 对应 |
| 方向ID | string | REQUIRED | MANUAL | 来自 01 |
| 样品ID | string | REQUIRED | MANUAL | 内部样品 ID |
| 样品ASIN | string | REQUIRED | MANUAL | 样品 ASIN |
| 样品标题 | string | REQUIRED | MANUAL | 样品标题 |
| 最终GoNoGo | enum | REQUIRED | MANUAL | GO/NO_GO/HOLD |
| 最终解释 | string | OPTIONAL | MANUAL | 人工填写 |
| 利润核价 | string | OPTIONAL | MANUAL | 人工填写 |
| 合规 | string | OPTIONAL | MANUAL | 人工填写 |
| 改良点 | string | OPTIONAL | MANUAL | 人工填写 |
| 决策日期 | date | REQUIRED | MANUAL | YYYY-MM-DD |
| 决策人 | string | REQUIRED | MANUAL | 人工填写 |
| 备注 | string | OPTIONAL | MANUAL | 补充说明 |

## 90_下推参数表.csv
| 字段名 | 类型 | 必填 | 填充方式 | 说明 |
|---|---|---|---|---|
| step_code | string | REQUIRED | MANUAL | 步骤编码 |
| step_name | string | REQUIRED | MANUAL | 步骤名称 |
| rule_id | string | REQUIRED | MANUAL | 规则唯一 ID |
| metric_name | string | REQUIRED | MANUAL | 指标名 |
| metric_scope | string | REQUIRED | MANUAL | 方向/关键词/市场/样品 |
| comparator | string | REQUIRED | MANUAL | >= / <= / == / in |
| threshold_value | string | REQUIRED | MANUAL | 阈值 |
| threshold_unit | string | OPTIONAL | MANUAL | 单位 |
| enabled | enum | REQUIRED | MANUAL | TRUE/FALSE |
| hard_fail | enum | REQUIRED | MANUAL | TRUE/FALSE |
| blank_action | enum | REQUIRED | MANUAL | FAIL/HOLD/PASS |
| tie_breaker_rank | number | OPTIONAL | MANUAL | 同层排序优先级 |
| note | string | OPTIONAL | MANUAL | 补充说明 |
