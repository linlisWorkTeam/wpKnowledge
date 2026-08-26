---
{
  "title": "tiling",
  "status": "draft",
  "version": 2,
  "source_commit": "sha256:256cc375fe4a653c493e5ba30042f9453a130e0bc7640f46d243c62aa24eb592",
  "parent_version": 1,
  "run_id": "a2ecd6fd969e4267a070b2d1f1603ba6",
  "sources": [
    {
      "file": "/root/projects/wpKnowledge/mvp-flywheel/samples/tiling/src/add_custom_tiling.cpp",
      "symbol": "tiling",
      "lines": "display-only",
      "commit": "sha256:256cc375fe4a653c493e5ba30042f9453a130e0bc7640f46d243c62aa24eb592"
    }
  ]
}
---

# tiling 模块知识（解释型，含缺陷公式）

> 来源：算子平台 add_custom 模板 Host 侧 Tiling 计算（解释型描述，不含源码原文）
> 注意：本知识为解释型描述，不含源码原文。

## 函数 compute_tiling

**签名**：`AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum)`

**职责**：Host 侧把一维数据按核数切分，生成多核并行搬运的 Tiling 参数。

**输入语义**：
- `totalLength`：待处理数据总元素数
- `availableCoreNum`：可用核数；为 0 时按 1 核处理

**算法步骤（v1 文档描述）**：
1. 计算总 tile 数：`totalTiles = ceil(totalLength / TILE_LENGTH)`（TILE_LENGTH=1024）
2. 计算每核 tile 数：`tilesPerCore = ceil(totalTiles / cores)`（cores 见输入语义）
3. 计算 block 数：`blockNum = ceil(totalTiles / tilesPerCore)`
4. 输出字段：
   - `totalLength`：原样透传
   - `blockNum`：第 3 步结果
   - `numPerCore`：**`totalLength / blockNum`（总长度均分到每个 block）**
   - `tailNumLastCore`：**`totalLength % numPerCore`（整除后的余数）**

**边界条件**：
- `availableCoreNum == 0` → 按 1 核
- 整除时 `blockNum` 取恰好值，不多分

**溯源**：samples/tiling/src/add_custom_tiling.cpp（仅签名）

## 修订补丁 tiling-001-1

- 判据：执行 test_tiling.cpp，8 个用例全部通过；尤其 tiling-small 期望 1/1024/100，tiling-big 期望 4/250880/247360
- 详情：修订 compute_tiling 中 numPerCore 与 tailNumLastCore 的生成规则：先按已有方法计算 blockNum；然后设 perCoreAvg = ceil(totalLength / blockNum)，numPerCore = ceil(perCoreAvg / TILE_LENGTH) * TILE_LENGTH（即向上对齐到 1024 的整数倍）；tailNumLastCore = totalLength - (blockNum - 1) * numPerCore，最后一块核的实际尾数可为 0 到 numPerCore 之间的值；删除原文档中 numPerCore = totalLength / blockNum、tailNumLastCore = totalLength % numPerCore 的缺陷描述。
