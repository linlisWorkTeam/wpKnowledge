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
